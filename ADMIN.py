import socket
import threading
import json
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from datetime import datetime

class AdminClient:
    def __init__(self, master):
        self.master = master
        self.master.title("👑 ADMIN CONTROL PANEL - KÉO BÚA BAO")
        self.master.geometry("1200x700") # Mở rộng chiều ngang cho 3 cột
        self.master.configure(bg="#2C3E50")
        
        self.sock = None
        self.is_connected = False
        self.game_started = False
        self.player_states = {} # [NEW] Lưu trạng thái kết nối của player để dùng cho Ranking
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()
        
        self.setup_ui()
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def configure_styles(self):
        self.style.configure("TFrame", background="#2C3E50")
        self.style.configure("TLabel", background="#2C3E50", foreground="white", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#ECF0F1")
        
        self.style.configure("Connect.TButton", font=("Segoe UI", 10, "bold"), background="#27AE60", foreground="white")
        self.style.map("Connect.TButton", background=[('active', '#2ECC71')])
        
        self.style.configure("Start.TButton", font=("Segoe UI", 14, "bold"), background="#E67E22", foreground="white")
        self.style.map("Start.TButton", background=[('active', '#D35400')])
        
        self.style.configure("Treeview", background="white", foreground="black", fieldbackground="white", font=("Segoe UI", 9), rowheight=25)
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def setup_ui(self):
        """Thiết lập giao diện admin 3 cột"""
        # --- Header ---
        top_bar = tk.Frame(self.master, bg="#34495E", height=60, padx=10, pady=10)
        top_bar.pack(fill=tk.X)
        
        tk.Label(top_bar, text="🎮 GAME ADMIN MANAGER", font=("Segoe UI", 14, "bold"), bg="#34495E", fg="#ECF0F1").pack(side=tk.LEFT)
        
        conn_frame = tk.Frame(top_bar, bg="#34495E")
        conn_frame.pack(side=tk.RIGHT)
        
        tk.Label(conn_frame, text="Server:", bg="#34495E", fg="#BDC3C7").pack(side=tk.LEFT, padx=5)
        self.server_entry = tk.Entry(conn_frame, width=12, bg="#2C3E50", fg="white", insertbackground="white")
        self.server_entry.insert(0, "localhost")
        self.server_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(conn_frame, text="Port:", bg="#34495E", fg="#BDC3C7").pack(side=tk.LEFT, padx=5)
        self.port_entry = tk.Entry(conn_frame, width=6, bg="#2C3E50", fg="white", insertbackground="white")
        self.port_entry.insert(0, "8888")
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="🔌 KẾT NỐI", style="Connect.TButton", command=self.connect_to_server)
        self.connect_btn.pack(side=tk.LEFT, padx=10)
        
        self.status_label = tk.Label(top_bar, text="● Offline", bg="#34495E", fg="#E74C3C", font=("Segoe UI", 10, "bold"))
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # --- Main Layout (3 Columns) ---
        main_container = tk.Frame(self.master, bg="#2C3E50")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 1. LEFT COLUMN: Controls & Players (Width fixed ~280)
        left_col = tk.Frame(main_container, bg="#2C3E50", width=280)
        left_col.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_col.pack_propagate(False)
        
        # Player List
        player_frame = tk.LabelFrame(left_col, text=" Danh sách người chơi ", font=("Segoe UI", 10, "bold"), bg="#2C3E50", fg="#ECF0F1")
        player_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.player_tree = ttk.Treeview(player_frame, columns=("player", "status"), show="headings", height=8)
        self.player_tree.heading("player", text="Player ID")
        self.player_tree.heading("status", text="Trạng thái")
        self.player_tree.column("player", width=120)
        self.player_tree.column("status", width=80, anchor="center")
        self.player_tree.pack(fill=tk.X, padx=5, pady=5)
        
        self.player_count_label = tk.Label(player_frame, text="Wait: 0/8", bg="#2C3E50", fg="#F1C40F", font=("Segoe UI", 10, "bold"))
        self.player_count_label.pack(pady=2)

        # Start Button
        self.start_btn = ttk.Button(left_col, text="🚀 BẮT ĐẦU GIẢI ĐẤU", style="Start.TButton", command=self.start_game, state='disabled')
        self.start_btn.pack(fill=tk.X, pady=5, ipady=10)
        
        # Chat
        chat_frame = tk.LabelFrame(left_col, text=" Chat Lobby ", font=("Segoe UI", 10, "bold"), bg="#2C3E50", fg="#ECF0F1")
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.chat_display = scrolledtext.ScrolledText(chat_frame, width=30, height=10, font=("Segoe UI", 9), bg="#34495E", fg="white", state='disabled', borderwidth=0)
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        chat_input_box = tk.Frame(chat_frame, bg="#2C3E50")
        chat_input_box.pack(fill=tk.X, padx=5, pady=5)
        self.chat_entry = tk.Entry(chat_input_box, font=("Segoe UI", 10), bg="#ECF0F1")
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.chat_entry.bind('<Return>', lambda e: self.send_chat())
        tk.Button(chat_input_box, text="➤", command=self.send_chat, bg="#3498DB", fg="white", relief="flat").pack(side=tk.RIGHT, padx=(5,0))

        # 2. RIGHT COLUMN: Ranking & Stats (Width fixed ~320)
        # (Pack Right first so Center fills the remaining space)
        right_col = tk.Frame(main_container, bg="#2C3E50", width=320)
        right_col.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_col.pack_propagate(False)
        
        self.round_label = tk.Label(right_col, text="TRẠNG THÁI: CHỜ...", font=("Segoe UI", 12, "bold"), bg="#2C3E50", fg="#3498DB", wraplength=300)
        self.round_label.pack(pady=(0, 10))
        
        # Ranking Table
        rank_frame = tk.LabelFrame(right_col, text=" Bảng Xếp Hạng ", font=("Segoe UI", 10, "bold"), bg="#2C3E50", fg="#ECF0F1")
        rank_frame.pack(fill=tk.BOTH, expand=True)
        
        self.ranking_tree = ttk.Treeview(rank_frame, columns=("Rank", "Player", "Score"), show="headings", height=20)
        self.ranking_tree.heading("Rank", text="#")
        self.ranking_tree.heading("Player", text="Player")
        self.ranking_tree.heading("Score", text="Điểm (Thắng-Thua)")
        
        self.ranking_tree.column("Rank", width=40, anchor="center")
        self.ranking_tree.column("Player", width=130, anchor="center") # Mở rộng cột Player một chút để hiện chữ AFK
        self.ranking_tree.column("Score", width=120, anchor="center")
        self.ranking_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 3. CENTER COLUMN: Match Logs (Fills remaining space)
        center_col = tk.Frame(main_container, bg="#2C3E50")
        center_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        log_frame = tk.LabelFrame(center_col, text=" Diễn biến trận đấu ", font=("Segoe UI", 10, "bold"), bg="#2C3E50", fg="#ECF0F1")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.match_display = scrolledtext.ScrolledText(log_frame, width=50, height=20, font=("Consolas", 10), bg="#000000", fg="#00FF00", state='disabled', borderwidth=0)
        self.match_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def connect_to_server(self):
        host = self.server_entry.get()
        try: port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Lỗi", "Port phải là số")
            return
        threading.Thread(target=self.perform_connection, args=(host, port), daemon=True).start()

    def perform_connection(self, host, port):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.is_connected = True
            self.send_message_sync('JOIN', {'player_id': 'ADMIN', 'is_admin': True})
            self.master.after(0, self.on_connect_success)
            self.receive_loop()
        except Exception as e: self.master.after(0, lambda: messagebox.showerror("Lỗi kết nối", str(e)))

    def on_connect_success(self):
        self.status_label.config(text="● ONLINE", fg="#2ECC71")
        self.connect_btn.state(['disabled'])
        self.add_log("✓ Đã kết nối server thành công!", "green")

    def send_message_sync(self, msg_type, data):
        if self.sock and self.is_connected:
            try:
                message = json.dumps({"type": msg_type, "data": data}) + '\n'
                self.sock.sendall(message.encode('utf-8'))
            except Exception as e: self.is_connected = False

    def receive_loop(self):
        buffer = ""
        while self.is_connected:
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data: break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            msg = json.loads(line)
                            self.master.after(0, self.handle_message, msg)
                        except json.JSONDecodeError: pass
            except: break
        self.is_connected = False
        self.master.after(0, self.on_disconnect)

    def on_disconnect(self):
        self.status_label.config(text="● OFFLINE", fg="#E74C3C")
        self.connect_btn.state(['!disabled'])
        self.add_log("✗ Mất kết nối server", "red")

    def handle_message(self, message):
        msg_type = message.get('type')
        data = message.get('data')
        
        if msg_type == 'JOIN_SUCCESS': self.add_chat("SYSTEM: Admin đã vào phòng", "yellow")
        elif msg_type == 'PLAYER_LIST':
            self.update_player_list(data['players'])
            count = data.get('count', 0)
            self.player_count_label.config(text=f"Players: {count}/8")
            if data.get('can_start'):
                self.start_btn.state(['!disabled'])
                self.player_count_label.config(fg="#2ECC71", text="SẴN SÀNG KHỞI TRANH!")
            else:
                self.start_btn.state(['disabled'])
                self.player_count_label.config(fg="#F1C40F")
        elif msg_type == 'PLAYER_JOINED': self.add_chat(f"→ {data.get('player_id')} tham gia", "cyan")
        elif msg_type == 'CHAT':
            try:
                sender = data.get('from', 'Unknown')
                if sender != 'ADMIN':
                    timestamp = datetime.fromisoformat(data['timestamp']).strftime('%H:%M')
                    self.add_chat(f"[{timestamp}] {sender}: {data['message']}")
            except: pass
        elif msg_type == 'GAME_STARTING':
            self.game_started = True
            self.start_btn.state(['disabled'])
            self.add_log("\n" + "█"*60, "purple")
            self.add_log("    🔥 GIẢI ĐẤU CHÍNH THỨC BẮT ĐẦU! 🔥", "purple")
            self.add_log("█"*60 + "\n", "purple")
        elif msg_type == 'ROUND_START': self.show_round_start(data)
        elif msg_type == 'GAME_RESULT': self.show_game_result(data)
        elif msg_type == 'MATCH_END': self.show_match_end(data)
        elif msg_type == 'TOURNAMENT_END': self.show_tournament_end(data)

    def send_chat(self):
        message = self.chat_entry.get().strip()
        if message and self.is_connected:
            threading.Thread(target=self.send_message_sync, args=('CHAT', {'message': message})).start()
            self.add_chat(f"ADMIN: {message}", "green")
            self.chat_entry.delete(0, tk.END)

    def start_game(self):
        if messagebox.askyesno("Xác nhận", "Bắt đầu giải đấu với 8 người chơi?"):
            threading.Thread(target=self.send_message_sync, args=('ADMIN_START', {})).start()

    def update_player_list(self, players):
        # [NEW] Cập nhật logic để nhận diện AFK từ danh sách người chơi
        for item in self.player_tree.get_children(): self.player_tree.delete(item)
        self.player_states.clear() # Làm mới trạng thái
        
        for p in players:
            # Lấy thông tin connected (nếu server V5 gửi), mặc định True để tương thích ngược
            is_connected = p.get('connected', True)
            self.player_states[p['id']] = is_connected # Lưu lại trạng thái để dùng ở Ranking
            
            if not is_connected:
                status = "⚠️ AFK"
            elif p['eliminated']:
                status = "❌ Bị loại"
            else:
                status = "✅ Sẵn sàng"
                
            self.player_tree.insert("", "end", values=(p['id'], status))

    def add_chat(self, text, color="white"):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, text + '\n')
        colors = {"green": "#2ECC71", "blue": "#3498DB", "red": "#E74C3C", "yellow": "#F1C40F", "cyan": "#1ABC9C", "purple": "#9B59B6"}
        self.chat_display.tag_add(color, "end-2l", "end-1l")
        self.chat_display.tag_config(color, foreground=colors.get(color, "white"))
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')

    def add_log(self, text, color="white"):
        self.match_display.config(state='normal')
        self.match_display.insert(tk.END, text + '\n')
        colors = {"green": "#2ECC71", "blue": "#3498DB", "red": "#E74C3C", "purple": "#D2B4DE", "cyan": "#1ABC9C"}
        self.match_display.tag_add(color, "end-2l", "end-1l")
        self.match_display.tag_config(color, foreground=colors.get(color, "#ECF0F1"), font=("Consolas", 10, "bold"))
        self.match_display.see(tk.END)
        self.match_display.config(state='disabled')

    def show_round_start(self, data):
        self.round_label.config(text=f"🏆 {data['round_name']} | Mục tiêu: {data['target_score']} điểm")
        self.add_log(f"\n⚡ {data['round_name']} - BẮT ĐẦU", "purple")
        for pair in data['pairs']: self.add_log(f"  ➤ Match {pair['match_id']}: {pair['p1']} vs {pair['p2']}")

    def show_game_result(self, data):
        emojis = {'ROCK': '✊', 'PAPER': '✋', 'SCISSORS': '✌'}
        result = "HÒA" if data['result'] == 0 else f"{data['p1'] if data['result'] == 1 else data['p2']} THẮNG"
        self.add_log(f"[Trận {data['match_id']}] {data['p1']} {emojis.get(data['p1_choice'])} vs {emojis.get(data['p2_choice'])} {data['p2']} ➜ {result} ({data['p1_score']}-{data['p2_score']})")

    def show_match_end(self, data):
        self.add_log(f"\n🏁 Trận {data['match_id']} KẾT THÚC: {data['winner']} Thắng", "green")

    def show_tournament_end(self, data):
        # 1. Log ra màn hình console của Admin
        self.add_log("\n" + "★"*60, "purple")
        self.add_log(f"         🏆 NHÀ VÔ ĐỊCH: {data['champion']}", "purple")
        self.add_log("★"*60 + "\n", "purple")
        
        # 2. Cập nhật Bảng Xếp Hạng (Treeview) bên phải
        # Xóa dữ liệu cũ
        for item in self.ranking_tree.get_children(): 
            self.ranking_tree.delete(item)
            
        # Thêm dữ liệu mới (Đủ 8 người)
        for p in data['ranking']:
            score_text = f"{p['points_for']}-{p['points_against']} ({p['goal_diff']:+d})"
            
            # [NEW] Kiểm tra trạng thái AFK đã lưu ở player_states
            is_connected = self.player_states.get(p['player_id'], True)
            display_name = p['player_id']
            if not is_connected:
                display_name += " (⚠️ AFK)"
            
            # Insert vào bảng
            self.ranking_tree.insert("", "end", values=(p['rank'], display_name, score_text))
            
        # 3. Popup thông báo ngắn gọn
        messagebox.showinfo("HOÀN THÀNH", f"Giải đấu kết thúc thành công!\n🏆 Vô địch: {data['champion']}")

    def on_closing(self):
        if self.sock:
            self.is_connected = False
            try: self.sock.close()
            except: pass
        self.master.destroy()

def main():
    root = tk.Tk()
    app = AdminClient(root)
    root.mainloop()

if __name__ == '__main__':
    main()