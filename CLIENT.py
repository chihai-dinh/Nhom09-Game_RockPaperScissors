import socket
import threading
import json
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime

class GameClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Game Kéo Búa Bao - Client")
        self.master.geometry("700x600")
        
        # Socket variables
        self.sock = None
        self.is_connected = False
        
        # Game variables
        self.player_id = None
        self.in_match = False
        self.opponent = None
        self.my_score = 0
        self.opponent_score = 0
        self.target_score = 0
        
        self.setup_ui()
        
        # Xử lý khi đóng cửa sổ
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_ui(self):
        """Thiết lập giao diện"""
        # --- Frame kết nối ---
        self.connect_frame = tk.Frame(self.master)
        self.connect_frame.pack(pady=10)
        
        tk.Label(self.connect_frame, text="Server:").grid(row=0, column=0)
        self.server_entry = tk.Entry(self.connect_frame, width=15)
        self.server_entry.insert(0, "localhost")
        self.server_entry.grid(row=0, column=1, padx=5)
        
        tk.Label(self.connect_frame, text="Port:").grid(row=0, column=2)
        self.port_entry = tk.Entry(self.connect_frame, width=8)
        self.port_entry.insert(0, "8888")
        self.port_entry.grid(row=0, column=3, padx=5)
        
        tk.Label(self.connect_frame, text="Player ID:").grid(row=0, column=4)
        self.id_entry = tk.Entry(self.connect_frame, width=12)
        self.id_entry.grid(row=0, column=5, padx=5)
        
        self.connect_btn = tk.Button(self.connect_frame, text="Kết nối", 
                                   command=self.connect_to_server, bg="green", fg="white")
        self.connect_btn.grid(row=0, column=6, padx=5)
        
        # --- Frame lobby ---
        self.lobby_frame = tk.LabelFrame(self.master, text="LOBBY", font=("Arial", 12, "bold"))
        self.lobby_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Danh sách người chơi (Trái)
        left_frame = tk.Frame(self.lobby_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
        
        tk.Label(left_frame, text="Người chơi:", font=("Arial", 10, "bold")).pack()
        self.player_listbox = tk.Listbox(left_frame, width=20, height=15)
        self.player_listbox.pack()
        
        self.status_label = tk.Label(left_frame, text="Chờ kết nối...", fg="blue")
        self.status_label.pack(pady=5)
        
        # Chat (Phải)
        right_frame = tk.Frame(self.lobby_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(right_frame, text="Chat:", font=("Arial", 10, "bold")).pack()
        self.chat_display = scrolledtext.ScrolledText(right_frame, width=50, height=12, state='disabled')
        self.chat_display.pack()
        
        chat_input_frame = tk.Frame(right_frame)
        chat_input_frame.pack(fill=tk.X, pady=5)
        
        self.chat_entry = tk.Entry(chat_input_frame)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.chat_entry.bind('<Return>', lambda e: self.send_chat())
        
        tk.Button(chat_input_frame, text="Gửi", command=self.send_chat).pack(side=tk.RIGHT)
        
        # --- Frame trận đấu (Ẩn mặc định) ---
        self.match_frame = tk.LabelFrame(self.master, text="TRẬN ĐẤU", font=("Arial", 12, "bold"))
        
        self.match_info_label = tk.Label(self.match_frame, text="", font=("Arial", 11))
        self.match_info_label.pack(pady=5)
        
        self.score_label = tk.Label(self.match_frame, text="", font=("Arial", 14, "bold"), fg="red")
        self.score_label.pack(pady=5)
        
        # Buttons chọn
        choice_frame = tk.Frame(self.match_frame)
        choice_frame.pack(pady=10)
        
        self.rock_btn = tk.Button(choice_frame, text="✊ BÚA", width=12, height=3,
                                  command=lambda: self.make_choice('ROCK'), 
                                  bg="#FF6B6B", fg="white", font=("Arial", 12, "bold"))
        self.rock_btn.grid(row=0, column=0, padx=10)
        
        self.paper_btn = tk.Button(choice_frame, text="✋ BAO", width=12, height=3,
                                   command=lambda: self.make_choice('PAPER'),
                                   bg="#4ECDC4", fg="white", font=("Arial", 12, "bold"))
        self.paper_btn.grid(row=0, column=1, padx=10)
        
        self.scissors_btn = tk.Button(choice_frame, text="✌ KÉO", width=12, height=3,
                                      command=lambda: self.make_choice('SCISSORS'),
                                      bg="#95E1D3", fg="white", font=("Arial", 12, "bold"))
        self.scissors_btn.grid(row=0, column=2, padx=10)
        
        self.match_log = scrolledtext.ScrolledText(self.match_frame, width=60, height=8, state='disabled')
        self.match_log.pack(pady=5)
        
    def connect_to_server(self):
        """Kết nối đến server (Chạy luồng riêng để không đơ UI)"""
        host = self.server_entry.get()
        try:
            port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Lỗi", "Port phải là số")
            return

        player_id = self.id_entry.get().strip()
        
        if not player_id:
            messagebox.showerror("Lỗi", "Vui lòng nhập Player ID")
            return
        
        self.player_id = player_id
        
        # Start connection in a separate thread to keep UI responsive
        threading.Thread(target=self.perform_connection, args=(host, port), daemon=True).start()

    def perform_connection(self, host, port):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.is_connected = True
            
            # Gửi tin nhắn JOIN ngay lập tức
            self.send_message_sync('JOIN', {'player_id': self.player_id, 'is_admin': False})
            
            # Cập nhật UI từ luồng chính
            self.master.after(0, lambda: self.connect_btn.config(state='disabled'))
            self.master.after(0, lambda: self.add_chat("✓ Đã kết nối server!", "green"))
            
            # Bắt đầu luồng nhận tin nhắn
            threading.Thread(target=self.receive_loop, daemon=True).start()
            
        except Exception as e:
            self.master.after(0, lambda: messagebox.showerror("Lỗi kết nối", str(e)))

    def send_message_sync(self, msg_type, data):
        """Gửi message (Synchronous)"""
        if self.sock and self.is_connected:
            try:
                message = json.dumps({"type": msg_type, "data": data}) + '\n'
                self.sock.sendall(message.encode('utf-8'))
            except Exception as e:
                print(f"Send error: {e}")
                self.is_connected = False

    def send_chat(self):
        """Gửi chat"""
        message = self.chat_entry.get().strip()
        if message:
            # Gửi trong luồng phụ để tránh lag nếu mạng chậm
            threading.Thread(target=self.send_message_sync, args=('CHAT', {'message': message}), daemon=True).start()
            self.chat_entry.delete(0, tk.END)

    def make_choice(self, choice):
        """Gửi lựa chọn"""
        threading.Thread(target=self.send_message_sync, args=('CHOICE', {'choice': choice}), daemon=True).start()
        self.disable_choices()
        self.add_match_log(f"Bạn chọn: {self.get_emoji(choice)}", "blue")

    def receive_loop(self):
        """Vòng lặp nhận tin nhắn từ server"""
        buffer = ""
        while self.is_connected:
            try:
                # Đọc dữ liệu từ socket
                data = self.sock.recv(4096).decode('utf-8')
                if not data:
                    break
                
                buffer += data
                
                # Xử lý các gói tin bị dính liền (newline delimited)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            msg = json.loads(line)
                            # Đẩy việc xử lý về luồng chính (Main Thread)
                            self.master.after(0, self.handle_message, msg)
                        except json.JSONDecodeError:
                            print("JSON Error")
                            
            except Exception as e:
                print(f"Receive error: {e}")
                break
        
        # Nếu thoát vòng lặp -> mất kết nối
        self.is_connected = False
        self.master.after(0, lambda: self.add_chat("✗ Mất kết nối server", "red"))
        self.master.after(0, lambda: self.connect_btn.config(state='normal'))

    def handle_message(self, message):
        """Xử lý logic message (Chạy trên Main Thread)"""
        msg_type = message.get('type')
        data = message.get('data')
        
        if msg_type == 'JOIN_SUCCESS':
            self.add_chat(f"Chào mừng {data['player_id']}!", "blue")
            
        elif msg_type == 'PLAYER_LIST':
            self.update_player_list(data['players'])
            if data.get('can_start'):
                self.status_label.config(text="✓ Đủ 8 người - Chờ Admin bắt đầu", fg="green")
            else:
                self.status_label.config(text=f"Đang chờ ({data.get('count', 0)}/8)", fg="orange")
                
        elif msg_type == 'PLAYER_JOINED':
            self.add_chat(f"→ {data.get('player_id')} đã tham gia ({data.get('player_count')}/8)", "blue")
            
        elif msg_type == 'CHAT':
            try:
                timestamp = datetime.fromisoformat(data['timestamp']).strftime('%H:%M:%S')
                self.add_chat(f"[{timestamp}] {data['from']}: {data['message']}")
            except:
                self.add_chat(f"{data['from']}: {data['message']}")
            
        elif msg_type == 'GAME_STARTING':
            self.add_chat(data['message'], "green")
            self.lobby_frame.pack_forget() # Ẩn lobby
            
        elif msg_type == 'ROUND_START':
            self.add_chat(f"\n{'='*50}", "purple")
            self.add_chat(f"  {data['round_name']} - Thắng {data['target_score']} điểm", "purple")
            self.add_chat(f"{'='*50}", "purple")
            
        elif msg_type == 'MATCH_INFO':
            self.start_match(data)
            
        elif msg_type == 'GAME_RESULT':
            self.show_game_result(data)
            
        elif msg_type == 'MATCH_END':
            self.show_match_end(data)
            
        elif msg_type == 'ELIMINATED':
            self.show_eliminated(data)
            
        elif msg_type == 'TOURNAMENT_END':
            self.show_tournament_end(data)
            
        elif msg_type == 'ERROR':
            messagebox.showerror("Lỗi Server", data['message'])

    # --- Các hàm cập nhật UI (Helper) ---
    def update_player_list(self, players):
        self.player_listbox.delete(0, tk.END)
        for p in players:
            status = " (Loại)" if p['eliminated'] else ""
            self.player_listbox.insert(tk.END, p['id'] + status)

    def add_chat(self, text, color="black"):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, text + '\n')
        self.chat_display.tag_add(color, "end-2l", "end-1l")
        self.chat_display.tag_config(color, foreground=color)
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')

    def add_match_log(self, text, color="black"):
        self.match_log.config(state='normal')
        self.match_log.insert(tk.END, text + '\n')
        self.match_log.tag_add(color, "end-2l", "end-1l")
        self.match_log.tag_config(color, foreground=color)
        self.match_log.see(tk.END)
        self.match_log.config(state='disabled')

    def start_match(self, data):
        self.in_match = True
        self.opponent = data['opponent']
        self.target_score = data['target_score']
        self.my_score = 0
        self.opponent_score = 0
        
        self.match_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.match_info_label.config(text=f"Đối thủ: {self.opponent}")
        self.update_score()
        
        self.add_match_log(f"═══ Trận đấu vs {self.opponent} ═══", "purple")
        self.add_match_log(f"Mục tiêu: {self.target_score} điểm\n", "blue")
        self.enable_choices()

    def update_score(self):
        self.score_label.config(
            text=f"{self.player_id} {self.my_score} - {self.opponent_score} {self.opponent}"
        )

    def enable_choices(self):
        self.rock_btn.config(state='normal')
        self.paper_btn.config(state='normal')
        self.scissors_btn.config(state='normal')

    def disable_choices(self):
        self.rock_btn.config(state='disabled')
        self.paper_btn.config(state='disabled')
        self.scissors_btn.config(state='disabled')

    def get_emoji(self, choice):
        emojis = {'ROCK': '✊ Búa', 'PAPER': '✋ Bao', 'SCISSORS': '✌ Kéo'}
        return emojis.get(choice, choice)

    def show_game_result(self, data):
        # --- [FIX QUAN TRỌNG] ---
        # Kiểm tra xem tin nhắn này có phải của trận mình đang đấu không
        # Nếu ID của mình không phải P1, cũng không phải P2 -> Bỏ qua ngay
        if self.player_id != data['p1'] and self.player_id != data['p2']:
            return
        # ------------------------

        # Xác định ai là p1, p2
        if data['p1'] == self.player_id:
            my_choice = data['p1_choice']
            opp_choice = data['p2_choice']
            self.my_score = data['p1_score']
            self.opponent_score = data['p2_score']
        else:
            my_choice = data['p2_choice']
            opp_choice = data['p1_choice']
            self.my_score = data['p2_score']
            self.opponent_score = data['p1_score']
        
        result_text = ""
        color = "black"
        
        if data['result'] == 0:
            result_text = "⚖ HÒA"
            color = "orange"
        elif (data['result'] == 1 and data['p1'] == self.player_id) or \
             (data['result'] == 2 and data['p2'] == self.player_id):
            result_text = "✓ THẮNG"
            color = "green"
        else:
            result_text = "✗ THUA"
            color = "red"
        
        self.add_match_log(f"{self.opponent} chọn: {self.get_emoji(opp_choice)}", "gray")
        self.add_match_log(f"→ {result_text}", color)
        
        self.update_score()
        self.enable_choices()

    def show_match_end(self, data):
        """Hiển thị kết thúc trận - CHỈ xử lý nếu mình trong trận"""
        winner = data['winner']
        loser = data['loser']
        
        # CHỈ xử lý nếu mình là người trong trận này
        if winner == self.player_id:
            self.add_match_log(f"\n★ BẠN THẮNG! Tỉ số: {data['score']}", "green")
            self.disable_choices()
            self.in_match = False
        elif loser == self.player_id:
            self.add_match_log(f"\n✗ BẠN THUA! Tỉ số: {data['score']}", "red")
            self.disable_choices()
            self.in_match = False
        else:
            # Không phải trận của mình, chỉ log thông tin vào chat
            self.add_chat(f"Match kết thúc: {winner} thắng {loser} ({data['score']})", "blue")

    def show_eliminated(self, data):
        messagebox.showwarning("BỊ LOẠI", f"{data['message']}\n\nỨng dụng sẽ đóng sau 10 giây")
        self.master.after(10000, self.master.quit)

    def show_tournament_end(self, data):
        ranking_text = "\n═══ BẢNG XẾP HẠNG CUỐI CÙNG ═══\n\n"
        stage_name = {3: "🏆 VÔ ĐỊCH", 2: "🥈 Á QUÂN", 1: "🥉 Hạng 3-4", 0: "Hạng 5-8"}
        
        for p in data['ranking']:
            ranking_text += f"{p['rank']}. {p['player_id']} - {stage_name.get(p['stage'], 'Unknown')}\n"
            ranking_text += f"   Điểm: {p['points_for']}-{p['points_against']} "
            ranking_text += f"(Hiệu số: {p['goal_diff']:+d}, Hòa: {p['draws']})\n\n"
        
        messagebox.showinfo("KẾT THÚC GIẢI ĐẤU", ranking_text)

    def on_closing(self):
        """Xử lý khi đóng cửa sổ"""
        if self.sock:
            self.is_connected = False
            try:
                self.sock.close()
            except:
                pass
        self.master.destroy()

def main():
    root = tk.Tk()
    app = GameClient(root)
    root.mainloop()

if __name__ == '__main__':
    main()