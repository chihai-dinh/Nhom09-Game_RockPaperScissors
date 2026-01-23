import socket
import threading
import json
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime

class GameClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Game Kéo Búa Bao - Client (Network Programming)")
        self.master.geometry("900x700") # Tăng kích thước mặc định
        
        # Cấu hình style cơ bản
        self.font_reg = ("Segoe UI", 10)
        self.font_bold = ("Segoe UI", 10, "bold")
        self.font_large = ("Segoe UI", 12, "bold")
        self.master.configure(bg="#f0f0f0")

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
        
        # Cấu hình lưới cho cửa sổ chính để co giãn
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(1, weight=1) # Phần Lobby sẽ giãn
        self.master.rowconfigure(2, weight=1) # Phần Match cũng giãn
        
        self.setup_ui()
        
        # Xử lý khi đóng cửa sổ
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_ui(self):
        """Thiết lập giao diện (Đã cải tiến Layout)"""
        
        # --- 1. Frame kết nối (Luôn hiện ở trên cùng) ---
        self.connect_frame = tk.LabelFrame(self.master, text="Connection configuration", font=self.font_bold, bg="#f0f0f0")
        self.connect_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        # Gom nhóm input cho gọn
        input_container = tk.Frame(self.connect_frame, bg="#f0f0f0")
        input_container.pack(pady=5)

        tk.Label(input_container, text="Server IP:", font=self.font_reg, bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.server_entry = tk.Entry(input_container, width=15, font=self.font_reg)
        self.server_entry.insert(0, "localhost")
        self.server_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(input_container, text="Port:", font=self.font_reg, bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.port_entry = tk.Entry(input_container, width=8, font=self.font_reg)
        self.port_entry.insert(0, "8888")
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(input_container, text="Player ID:", font=self.font_reg, bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.id_entry = tk.Entry(input_container, width=15, font=self.font_reg)
        self.id_entry.pack(side=tk.LEFT, padx=5)
        
        self.connect_btn = tk.Button(input_container, text="CONNECT SERVER", 
                                   command=self.connect_to_server, bg="#2196F3", fg="white", 
                                   font=self.font_bold, relief="flat", padx=10)
        self.connect_btn.pack(side=tk.LEFT, padx=15)
        
        # --- 2. Frame Lobby (Hiện danh sách & Chat) ---
        self.lobby_frame = tk.LabelFrame(self.master, text="Lobby", font=self.font_bold, bg="#f0f0f0")
        self.lobby_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.lobby_frame.columnconfigure(1, weight=3) # Cột Chat chiếm 3 phần
        self.lobby_frame.columnconfigure(0, weight=1) # Cột Player chiếm 1 phần
        self.lobby_frame.rowconfigure(0, weight=1)

        # Cột Trái: Danh sách người chơi
        left_panel = tk.Frame(self.lobby_frame, bg="#e0e0e0")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        tk.Label(left_panel, text="List Online", font=self.font_bold, bg="#e0e0e0").pack(pady=5)
        self.player_listbox = tk.Listbox(left_panel, font=self.font_reg, height=10, bg="white", bd=0)
        self.player_listbox.pack(fill=tk.BOTH, expand=True, padx=2)
        
        self.status_label = tk.Label(left_panel, text="Status: Not connected", fg="red", bg="#e0e0e0", font=("Segoe UI", 9, "italic"))
        self.status_label.pack(pady=5)
        
        # Cột Phải: Chat
        right_panel = tk.Frame(self.lobby_frame, bg="#f0f0f0")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        self.chat_display = scrolledtext.ScrolledText(right_panel, font=self.font_reg, state='disabled', bg="white", bd=0)
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        chat_input_frame = tk.Frame(right_panel, bg="#f0f0f0")
        chat_input_frame.pack(fill=tk.X, pady=5)
        
        self.chat_entry = tk.Entry(chat_input_frame, font=self.font_reg)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_entry.bind('<Return>', lambda e: self.send_chat())
        
        tk.Button(chat_input_frame, text="Chat", command=self.send_chat, bg="#4CAF50", fg="white", relief="flat").pack(side=tk.RIGHT)
        
        # --- 3. Frame Trận đấu (Mặc định ẩn, khi hiện sẽ đè lên Lobby hoặc hiện bên dưới) ---
        # Để đẹp hơn, mình sẽ cho nó hiện thay thế Lobby hoặc nằm dưới. Ở đây mình để nằm dưới Lobby nhưng ẩn đi.
        self.match_frame = tk.LabelFrame(self.master, text="KHU VỰC THI ĐẤU", font=self.font_large, fg="#D32F2F", bg="#FFF3E0")
        # Không pack/grid ngay. Khi nào start match mới grid.
        
        # Thông tin trận
        info_frame = tk.Frame(self.match_frame, bg="#FFF3E0")
        info_frame.pack(fill=tk.X, pady=5)
        
        self.match_info_label = tk.Label(info_frame, text="", font=("Segoe UI", 12), bg="#FFF3E0")
        self.match_info_label.pack()
        
        self.score_label = tk.Label(info_frame, text="0 - 0", font=("Segoe UI", 20, "bold"), fg="#D32F2F", bg="#FFF3E0")
        self.score_label.pack(pady=5)
        
        # Các nút bấm (SỬA LẠI TÊN NÚT CHO ĐÚNG LOGIC)
        choice_frame = tk.Frame(self.match_frame, bg="#FFF3E0")
        choice_frame.pack(pady=15)
        
        # Nút Búa (ROCK)
        self.rock_btn = tk.Button(choice_frame, text="✊ BÚA", width=15, height=2,
                                  command=lambda: self.make_choice('ROCK'), 
                                  bg="#FF5252", fg="white", font=self.font_large, relief="flat", cursor="hand2")
        self.rock_btn.grid(row=0, column=0, padx=10)
        
        # Nút Bao (PAPER)
        self.paper_btn = tk.Button(choice_frame, text="✋ BAO", width=15, height=2,
                                   command=lambda: self.make_choice('PAPER'),
                                   bg="#2196F3", fg="white", font=self.font_large, relief="flat", cursor="hand2")
        self.paper_btn.grid(row=0, column=1, padx=10)
        
        # Nút Kéo (SCISSORS)
        self.scissors_btn = tk.Button(choice_frame, text="✌ KÉO", width=15, height=2,
                                      command=lambda: self.make_choice('SCISSORS'),
                                      bg="#4CAF50", fg="white", font=self.font_large, relief="flat", cursor="hand2")
        self.scissors_btn.grid(row=0, column=2, padx=10)
        
        # Log trận đấu
        tk.Label(self.match_frame, text="Nhật ký trận đấu:", bg="#FFF3E0", font=self.font_bold).pack(anchor="w", padx=10)
        self.match_log = scrolledtext.ScrolledText(self.match_frame, width=60, height=8, state='disabled', font=("Consolas", 10))
        self.match_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
    # --- LOGIC CODE GIỮ NGUYÊN (Chỉ sửa mapping emoji) ---

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
        threading.Thread(target=self.perform_connection, args=(host, port), daemon=True).start()

    def perform_connection(self, host, port):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.is_connected = True
            
            self.send_message_sync('JOIN', {'player_id': self.player_id, 'is_admin': False})
            
            self.master.after(0, lambda: self.connect_btn.config(state='disabled', text="ĐÃ KẾT NỐI", bg="gray"))
            self.master.after(0, lambda: self.add_chat("✓ Đã kết nối server!", "green"))
            self.master.after(0, lambda: self.status_label.config(text="Status: Online", fg="green"))
            
            threading.Thread(target=self.receive_loop, daemon=True).start()
            
        except Exception as e:
            self.master.after(0, lambda: messagebox.showerror("Lỗi kết nối", str(e)))

    def send_message_sync(self, msg_type, data):
        if self.sock and self.is_connected:
            try:
                message = json.dumps({"type": msg_type, "data": data}) + '\n'
                self.sock.sendall(message.encode('utf-8'))
            except Exception as e:
                print(f"Send error: {e}")
                self.is_connected = False

    def send_chat(self):
        message = self.chat_entry.get().strip()
        if message:
            threading.Thread(target=self.send_message_sync, args=('CHAT', {'message': message}), daemon=True).start()
            self.chat_entry.delete(0, tk.END)

    def make_choice(self, choice):
        threading.Thread(target=self.send_message_sync, args=('CHOICE', {'choice': choice}), daemon=True).start()
        self.disable_choices()
        self.add_match_log(f"Bạn chọn: {self.get_emoji(choice)}", "blue")

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
                        except json.JSONDecodeError:
                            print("JSON Error")
            except Exception as e:
                print(f"Receive error: {e}")
                break
        
        self.is_connected = False
        self.master.after(0, lambda: self.add_chat("✗ Mất kết nối server", "red"))
        self.master.after(0, lambda: self.connect_btn.config(state='normal', text="KẾT NỐI LẠI", bg="#2196F3"))
        self.master.after(0, lambda: self.status_label.config(text="Status: Disconnected", fg="red"))

    def handle_message(self, message):
        msg_type = message.get('type')
        data = message.get('data')
        
        if msg_type == 'JOIN_SUCCESS':
            self.add_chat(f"Chào mừng {data['player_id']}!", "blue")
            
        elif msg_type == 'PLAYER_LIST':
            self.update_player_list(data['players'])
            if data.get('can_start'):
                self.status_label.config(text="✓ Đủ 8 người - Chờ Admin bắt đầu", fg="green")
            else:
                self.status_label.config(text=f"Waiting ({data.get('count', 0)}/8)", fg="orange")
                
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
            # Ẩn lobby, hiện match frame
            self.lobby_frame.grid_remove()
            self.match_frame.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=10, pady=5)
            
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

    def update_player_list(self, players):
        self.player_listbox.delete(0, tk.END)
        for p in players:
            status = " (Loại)" if p['eliminated'] else ""
            self.player_listbox.insert(tk.END, "👤 " + p['id'] + status)

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
        
        # Đảm bảo Match Frame hiện lên
        self.lobby_frame.grid_remove()
        self.match_frame.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=10, pady=5)
        
        self.match_info_label.config(text=f"ĐỐI THỦ CỦA BẠN: {self.opponent}")
        self.update_score()
        
        self.add_match_log(f"═══ TRẬN ĐẤU BẮT ĐẦU VS {self.opponent} ═══", "purple")
        self.add_match_log(f"Mục tiêu: {self.target_score} điểm thắng\n", "blue")
        self.enable_choices()

    def update_score(self):
        self.score_label.config(
            text=f"{self.player_id} [{self.my_score}] - [{self.opponent_score}] {self.opponent}"
        )

    def enable_choices(self):
        self.rock_btn.config(state='normal', bg="#FF5252")
        self.paper_btn.config(state='normal', bg="#2196F3")
        self.scissors_btn.config(state='normal', bg="#4CAF50")

    def disable_choices(self):
        self.rock_btn.config(state='disabled', bg="#FFCDD2")
        self.paper_btn.config(state='disabled', bg="#BBDEFB")
        self.scissors_btn.config(state='disabled', bg="#C8E6C9")

    def get_emoji(self, choice):
        # [SỬA LOGIC] Map đúng: ROCK=Búa, SCISSORS=Kéo
        emojis = {'ROCK': '✊ Búa', 'PAPER': '✋ Bao', 'SCISSORS': '✌ Kéo'}
        return emojis.get(choice, choice)

    def show_game_result(self, data):
        if self.player_id != data['p1'] and self.player_id != data['p2']:
            return
        
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
            color = "#F57C00" # Orange darken
        elif (data['result'] == 1 and data['p1'] == self.player_id) or \
             (data['result'] == 2 and data['p2'] == self.player_id):
            result_text = "✓ THẮNG"
            color = "#388E3C" # Green darken
        else:
            result_text = "✗ THUA"
            color = "#D32F2F" # Red darken
        
        self.add_match_log(f"Đối thủ ra: {self.get_emoji(opp_choice)}", "black")
        self.add_match_log(f"→ KẾT QUẢ: {result_text}", color)
        self.add_match_log("-" * 30, "gray")
        
        self.update_score()
        self.enable_choices()

    def show_match_end(self, data):
        winner = data['winner']
        loser = data['loser']
        
        if winner == self.player_id:
            self.add_match_log(f"\n★ CHÚC MỪNG! BẠN ĐÃ CHIẾN THẮNG!", "green")
            self.add_match_log(f"Tỉ số chung cuộc: {data['score']}", "green")
            self.disable_choices()
            self.in_match = False
            # Có thể quay về lobby sau vài giây nếu muốn, ở đây giữ nguyên logic cũ
        elif loser == self.player_id:
            self.add_match_log(f"\n✗ RẤT TIẾC! BẠN ĐÃ THUA TRẬN NÀY.", "red")
            self.add_match_log(f"Tỉ số chung cuộc: {data['score']}", "red")
            self.disable_choices()
            self.in_match = False
        else:
            self.add_chat(f"Kết thúc trận: {winner} thắng {loser} ({data['score']})", "blue")

    def show_eliminated(self, data):
        # Format bảng xếp hạng dạng text cho popup
        ranking_text = "🏆 KẾT QUẢ CHUNG CUỘC 🏆\n"
        ranking_text += "═" * 35 + "\n"
        ranking_text += f"{'#':<4}{'TÊN':<15}{'ĐIỂM (HS)'}\n"
        ranking_text += "─" * 35 + "\n"
        
        # Mapping tên vòng đấu
        stage_name = {3: "VÔ ĐỊCH", 2: "Á QUÂN", 1: "Top 4", 0: "Top 8"}
        
        for p in data['ranking']:
            # Format: 1   PlayerID       5-2 (+3)
            score_info = f"{p['points_for']}-{p['points_against']} ({p['goal_diff']:+d})"
            
            # Thêm icon cúp cho Top 3
            rank_icon = ""
            if p['rank'] == 1: rank_icon = "🥇"
            elif p['rank'] == 2: rank_icon = "🥈"
            elif p['rank'] == 3: rank_icon = "🥉"
            
            # Dòng hiển thị
            line = f"{p['rank']:<3} {p['player_id']:<12} {score_info}\n"
            if p['rank'] <= 2: # Nhấn mạnh Top 2
                line = line.upper()
                
            ranking_text += line
            
        ranking_text += "═" * 35 + "\n"
        ranking_text += f"Nhà vô địch: {data['champion']}! 🎉"
        
        messagebox.showinfo("KẾT THÚC GIẢI ĐẤU", ranking_text)

    def on_closing(self):
        if self.sock:
            self.is_connected = False
            try:
                self.sock.close()
            except:
                pass
        self.master.destroy()

def main():
    root = tk.Tk()
    # Thử set theme nếu có (Windows only)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = GameClient(root)
    root.mainloop()

if __name__ == '__main__':
    main()