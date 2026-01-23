import socket
import threading
import json
import logging
import random
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime
from typing import Dict, List, Optional

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server_game.log'),
        logging.StreamHandler()
    ]
)

class Player:
    def __init__(self, conn, player_id: str, addr):
        self.conn = conn
        self.player_id = player_id
        self.addr = addr
        self.is_admin = False
        self.eliminated = False
        # --- [NEW] Thêm trạng thái kết nối và thời gian ngắt ---
        self.is_connected = True
        self.disconnect_time = None 
        # -------------------------------------------------------
        self.lock = threading.Lock()
        
        # Stats
        self.stage = 0
        self.points_for = 0
        self.points_against = 0
        self.draws = 0
        self.survival_time = 0.0
        self.match_start_time = None

class Match:
    def __init__(self, p1: Player, p2: Player, target_score: int, match_id: int):
        self.p1 = p1
        self.p2 = p2
        self.target_score = target_score
        self.match_id = match_id
        self.p1_score = 0
        self.p2_score = 0
        self.p1_choice = None
        self.p2_choice = None
        self.completed = False
        self.lock = threading.Lock()

class GameServerGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("🖥️ GAME SERVER - Kéo Búa Bao (Split View)")
        self.master.geometry("1100x750")
        self.master.configure(bg="#1E1E1E")
        
        self.server = None
        self.setup_ui()
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_ui(self):
        """Thiết lập giao diện Server"""
        # --- Header ---
        header = tk.Frame(self.master, bg="#0078D4", height=60)
        header.pack(fill=tk.X)
        tk.Label(header, text="🖥️ SERVER DASHBOARD", 
                font=("Segoe UI", 18, "bold"), 
                bg="#0078D4", fg="white").pack(pady=10)
        
        # --- Control Panel (Top) ---
        control_frame = tk.Frame(self.master, bg="#2D2D2D", pady=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Config inputs
        tk.Label(control_frame, text="Host:", bg="#2D2D2D", fg="white").pack(side=tk.LEFT, padx=5)
        self.host_entry = tk.Entry(control_frame, width=12, font=("Consolas", 10))
        self.host_entry.insert(0, "0.0.0.0")
        self.host_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(control_frame, text="Port:", bg="#2D2D2D", fg="white").pack(side=tk.LEFT, padx=5)
        self.port_entry = tk.Entry(control_frame, width=6, font=("Consolas", 10))
        self.port_entry.insert(0, "8888")
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        self.start_btn = tk.Button(control_frame, text="▶ START", command=self.start_server,
                                   bg="#2AC62A", fg="white", font=("Segoe UI", 10, "bold"), width=10)
        self.start_btn.pack(side=tk.LEFT, padx=15)
        
        self.stop_btn = tk.Button(control_frame, text="⏹ STOP", command=self.stop_server,
                                  state='disabled', bg="#CB151B", fg="white", font=("Segoe UI", 10, "bold"), width=10)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # --- Status & Connections (Right side) ---
        self.status_label = tk.Label(control_frame, text="● STOPPED", 
                                     font=("Segoe UI", 10, "bold"), bg="#2D2D2D", fg="#D13438")
        self.status_label.pack(side=tk.RIGHT, padx=20)
        
        self.conn_label = tk.Label(control_frame, text="Connections: 0", 
                                   font=("Segoe UI", 11, "bold"), bg="#2D2D2D", fg="#4EC9B0")
        self.conn_label.pack(side=tk.RIGHT, padx=20)
        # ------------------------------------------------

        # --- Main Content Area ---
        content_frame = tk.Frame(self.master, bg="#1E1E1E")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # ================= CỘT TRÁI: CONNECTIONS =================
        left_panel = tk.Frame(content_frame, bg="#2D2D2D", width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False) 
        
        tk.Label(left_panel, text="👥 CONNECTIONS", font=("Segoe UI", 11, "bold"), 
                 bg="#252526", fg="#0078D4", pady=5).pack(fill=tk.X)
        
        self.player_count_label = tk.Label(left_panel, text="Players: 0/8", 
                                           font=("Segoe UI", 10), bg="#2D2D2D", fg="white")
        self.player_count_label.pack(pady=5, anchor='w', padx=10)
        
        self.players_listbox = tk.Listbox(left_panel, font=("Consolas", 10), 
                                         bg="#1E1E1E", fg="#4EC9B0", borderwidth=0,
                                         selectbackground="#0078D4", height=15)
        self.players_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.admin_label = tk.Label(left_panel, text="👑 Admin: --", 
                                    font=("Segoe UI", 9), bg="#2D2D2D", fg="#CE9178")
        self.admin_label.pack(pady=5, anchor='w', padx=10)

        tk.Label(left_panel, text="🎮 STATUS", font=("Segoe UI", 10, "bold"), 
                 bg="#252526", fg="white", pady=2).pack(fill=tk.X, pady=(10,0))
        
        self.game_status_label = tk.Label(left_panel, text="Waiting...", 
                                          font=("Segoe UI", 9), bg="#2D2D2D", fg="#B0B0B0")
        self.game_status_label.pack(pady=2)
        self.round_label = tk.Label(left_panel, text="-", 
                                    font=("Segoe UI", 9), bg="#2D2D2D", fg="#B0B0B0")
        self.round_label.pack(pady=2)

        # ================= CỘT PHẢI: LOGS =================
        right_panel = tk.Frame(content_frame, bg="#1E1E1E")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 1. KHUNG CHAT
        chat_frame = tk.LabelFrame(right_panel, text="💬 GLOBAL CHAT LOGS", 
                                   font=("Segoe UI", 10, "bold"), bg="#1E1E1E", fg="#569CD6")
        chat_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.chat_display = scrolledtext.ScrolledText(chat_frame, font=("Segoe UI", 10),
                                                      bg="#252526", fg="white", height=10,
                                                      insertbackground="white", state='disabled')
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.chat_display.tag_config("timestamp", foreground="#808080")
        self.chat_display.tag_config("player", foreground="#4EC9B0", font=("Segoe UI", 10, "bold"))
        self.chat_display.tag_config("msg", foreground="white")

        # 2. KHUNG SYSTEM LOG
        sys_log_frame = tk.LabelFrame(right_panel, text="🛠️ SYSTEM LOGS", 
                                      font=("Segoe UI", 10, "bold"), bg="#1E1E1E", fg="#CE9178")
        sys_log_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        
        self.log_display = scrolledtext.ScrolledText(sys_log_frame, font=("Consolas", 9),
                                                     bg="#000000", fg="#D4D4D4", height=12,
                                                     insertbackground="white", state='disabled')
        self.log_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- Log Controls (Save & Clear) ---
        btn_log_frame = tk.Frame(sys_log_frame, bg="#1E1E1E")
        btn_log_frame.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Button(btn_log_frame, text="🗑️ Clear Logs", command=self.clear_logs, 
                  bg="#3C3C3C", fg="white", font=("Segoe UI", 9)).pack(side=tk.RIGHT, padx=5)
                  
        tk.Button(btn_log_frame, text="💾 Save Logs", command=self.save_logs_to_file, 
                  bg="#0078D4", fg="white", font=("Segoe UI", 9)).pack(side=tk.RIGHT, padx=5)
        # ------------------------------------------
        
        self.log_display.tag_config("INFO", foreground="#4EC9B0")
        self.log_display.tag_config("WARNING", foreground="#CE9178")
        self.log_display.tag_config("ERROR", foreground="#F48771")
        self.log_display.tag_config("SUCCESS", foreground="#B5CEA8")
        self.log_display.tag_config("GAME", foreground="#DCDCAA")

        self.add_log("GUI Initialized. Ready to start.", "INFO")

    # --- Methods ---
    def add_chat(self, player_id, message):
        def _add():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.chat_display.config(state='normal')
            self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.chat_display.insert(tk.END, f"{player_id}: ", "player")
            self.chat_display.insert(tk.END, f"{message}\n", "msg")
            self.chat_display.see(tk.END)
            self.chat_display.config(state='disabled')
        if threading.current_thread() != threading.main_thread():
            self.master.after(0, _add)
        else: _add()

    def add_log(self, message, level="INFO"):
        def _add():
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_text = f"[{timestamp}] [{level}] {message}\n"
            self.log_display.config(state='normal')
            self.log_display.insert(tk.END, log_text, level)
            self.log_display.see(tk.END)
            self.log_display.config(state='disabled')
        if threading.current_thread() != threading.main_thread():
            self.master.after(0, _add)
        else: _add()
            
    def clear_logs(self):
        self.log_display.config(state='normal')
        self.log_display.delete(1.0, tk.END)
        self.log_display.config(state='disabled')
        self.chat_display.config(state='normal')
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state='disabled')
    
    def save_logs_to_file(self):
        """Lưu toàn bộ log ra file text"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"server_logs_{timestamp}.txt"
            
            chat_content = self.chat_display.get("1.0", tk.END)
            sys_content = self.log_display.get("1.0", tk.END)
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=== GLOBAL CHAT LOGS ===\n")
                f.write(chat_content)
                f.write("\n\n=== SYSTEM LOGS ===\n")
                f.write(sys_content)
                
            messagebox.showinfo("Saved", f"Đã lưu logs vào file:\n{filename}")
            self.add_log(f"Logs saved to {filename}", "SUCCESS")
        except Exception as e:
            messagebox.showerror("Error", f"Lỗi lưu file: {e}")

    def start_server(self):
        host = self.host_entry.get()
        try: port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Lỗi", "Port phải là số")
            return
        self.server = GameServer(host, port, self)
        threading.Thread(target=self.server.start, daemon=True).start()
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_label.config(text="● RUNNING", fg="#107C10")
        self.add_log(f"Server started on {host}:{port}", "SUCCESS")
        
    def stop_server(self):
        if self.server:
            self.server.running = False
            self.add_log("Stopping server...", "WARNING")
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_label.config(text="● STOPPED", fg="#D13438")
        
    def update_player_list(self, players, admin):
        def _update():
            self.players_listbox.delete(0, tk.END)
            for i, (pid, player) in enumerate(players.items(), 1):
                # --- [UPDATED] Hiển thị trạng thái AFK ---
                if not player.is_connected:
                    status = "⚠️ AFK"
                elif player.eliminated:
                    status = "❌"
                else:
                    status = "✅"
                # -----------------------------------------
                self.players_listbox.insert(tk.END, f"{i}. {status} {pid}")
            
            self.player_count_label.config(text=f"Players: {len(players)}/8")
            
            if admin: self.admin_label.config(text=f"👑 Admin: Connected", fg="#4EC9B0")
            else: self.admin_label.config(text="👑 Admin: Disconnected", fg="#CE9178")
            
            # Update Total Connections Label
            total_conn = len(players) + (1 if admin else 0)
            self.conn_label.config(text=f"Connections: {total_conn}")
        
        if threading.current_thread() != threading.main_thread():
            self.master.after(0, _update)
        else: _update()
    
    def on_closing(self):
        if self.server: self.server.running = False
        self.master.destroy()

class GameServer:
    def __init__(self, host, port, gui):
        self.host = host
        self.port = port
        self.gui = gui
        self.players: Dict[str, Player] = {}
        self.admin: Optional[Player] = None
        self.game_started = False
        self.current_round = 0
        self.active_matches: List[Match] = []
        self.lobby_locked = False
        self.running = True
        self.lock = threading.Lock()
        
    def send_message(self, player: Player, msg_type: str, data: dict):
        # --- [UPDATED] Check trạng thái kết nối ---
        if not player.is_connected: return
        # ------------------------------------------
        try:
            with player.lock:
                message = json.dumps({"type": msg_type, "data": data}) + '\n'
            # Check kỹ hơn trước khi gửi
            if player.conn:
                player.conn.sendall(message.encode('utf-8'))
        except Exception as e:
            logging.error(f"Error sending to {player.player_id}: {e}")
    
    def broadcast(self, msg_type: str, data: dict, exclude=None):
        with self.lock:
            for player in list(self.players.values()):
                # --- [UPDATED] Chỉ gửi cho người đang kết nối ---
                if player != exclude and not player.eliminated and player.is_connected:
                    threading.Thread(target=self.send_message, args=(player, msg_type, data), daemon=True).start()
            if self.admin and self.admin != exclude:
                threading.Thread(target=self.send_message, args=(self.admin, msg_type, data), daemon=True).start()
    
    def handle_client(self, conn, addr):
        self.gui.add_log(f"Connection request from {addr}", "INFO")
        player = None
        buffer = ""
        try:
            while self.running:
                data = conn.recv(4096).decode('utf-8')
                if not data: break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            message = json.loads(line)
                            msg_type = message.get('type')
                            msg_data = message.get('data', {})
                            
                            if msg_type == 'JOIN': player = self.handle_join(conn, msg_data, addr)
                            elif msg_type == 'CHAT' and player: self.handle_chat(player, msg_data)
                            elif msg_type == 'ADMIN_START' and player and player.is_admin: threading.Thread(target=self.start_tournament, daemon=True).start()
                            elif msg_type == 'CHOICE' and player: self.handle_choice(player, msg_data)
                        except json.JSONDecodeError: pass
        except Exception as e: self.gui.add_log(f"Error handling client {addr}: {e}", "ERROR")
        finally:
            if player: self.handle_disconnect(player)
            try: conn.close()
            except: pass
    
    def handle_join(self, conn, data: dict, addr):
        player_id = data.get('player_id', '')
        is_admin = data.get('is_admin', False)
        if self.lobby_locked and not is_admin:
            self.send_message(Player(conn, '', addr), 'ERROR', {'message': 'Game đã bắt đầu'})
            return None
        
        with self.lock:
            if is_admin:
                if self.admin:
                    self.send_message(Player(conn, '', addr), 'ERROR', {'message': 'Admin đã tồn tại'})
                    return None
                player = Player(conn, 'ADMIN', addr)
                player.is_admin = True
                self.admin = player
                self.gui.add_log(f"Admin connected from {addr[0]}", "SUCCESS")
            else:
                if len(self.players) >= 8:
                    self.send_message(Player(conn, '', addr), 'ERROR', {'message': 'Lobby đã đầy'})
                    return None
                if player_id in self.players:
                    self.send_message(Player(conn, '', addr), 'ERROR', {'message': 'ID đã tồn tại'})
                    return None
                player = Player(conn, player_id, addr)
                self.players[player_id] = player
                self.gui.add_log(f"Player '{player_id}' joined from {addr[0]}", "SUCCESS")
        
        self.send_message(player, 'JOIN_SUCCESS', {'player_id': player.player_id, 'is_admin': player.is_admin})
        self.gui.update_player_list(self.players, self.admin)
        self.broadcast_player_list()
        self.broadcast('PLAYER_JOINED', {'player_id': player.player_id, 'player_count': len(self.players)}, exclude=player)
        return player
    
    def handle_chat(self, player: Player, data: dict):
        message = data.get('message', '')
        self.gui.add_chat(player.player_id, message)
        self.broadcast('CHAT', {'from': player.player_id, 'message': message, 'timestamp': datetime.now().isoformat()})
    
    def broadcast_player_list(self):
        with self.lock:
            player_list = [{'id': pid, 'eliminated': p.eliminated} for pid, p in self.players.items()]
            can_start = len(self.players) == 8 and not self.game_started
        self.broadcast('PLAYER_LIST', {'players': player_list, 'count': len([p for p in self.players.values() if not p.eliminated]), 'can_start': can_start})
    
    def start_tournament(self):
        with self.lock:
            if len(self.players) != 8 or self.game_started: return
            self.game_started = True
            self.lobby_locked = True
        self.gui.add_log("🎮 TOURNAMENT STARTED!", "GAME")
        self.gui.game_status_label.config(text="RUNNING", fg="#107C10")
        self.broadcast('GAME_STARTING', {'message': 'Giải đấu bắt đầu!'})
        threading.Timer(2, lambda: self.start_round(1, 3)).start()
    
    def start_round(self, round_num: int, target_score: int):
        self.current_round = round_num
        with self.lock: active_players = [p for p in self.players.values() if not p.eliminated]
        round_names = {1: "TỨ KẾT", 2: "BÁN KẾT", 3: "CHUNG KẾT"}
        self.gui.add_log(f"━━━ {round_names[round_num]} (Target: {target_score}) ━━━", "GAME")
        self.gui.round_label.config(text=f"{round_names[round_num]}")
        random.shuffle(active_players)
        self.active_matches = []
        pairs = []
        for i in range(0, len(active_players), 2):
            p1 = active_players[i]
            p2 = active_players[i + 1]
            match = Match(p1, p2, target_score, i // 2 + 1)
            self.active_matches.append(match)
            pairs.append({'p1': p1.player_id, 'p2': p2.player_id, 'match_id': match.match_id})
            p1.match_start_time = datetime.now()
            p2.match_start_time = datetime.now()
            self.gui.add_log(f"Match {match.match_id}: {p1.player_id} vs {p2.player_id}", "INFO")
        self.broadcast('ROUND_START', {'round': round_num, 'round_name': round_names[round_num], 'target_score': target_score, 'pairs': pairs})
        for match in self.active_matches:
            self.send_message(match.p1, 'MATCH_INFO', {'opponent': match.p2.player_id, 'target_score': target_score, 'match_id': match.match_id})
            self.send_message(match.p2, 'MATCH_INFO', {'opponent': match.p1.player_id, 'target_score': target_score, 'match_id': match.match_id})
    
    def handle_choice(self, player: Player, data: dict):
        choice = data.get('choice')
        match = None
        for m in self.active_matches:
            if m.p1 == player or m.p2 == player:
                match = m
                break
        if not match: return
        with match.lock:
            if match.p1 == player: match.p1_choice = choice
            else: match.p2_choice = choice
            if match.p1_choice and match.p2_choice:
                threading.Thread(target=self.resolve_game, args=(match,), daemon=True).start()
    
    def resolve_game(self, match: Match):
        with match.lock:
            p1_choice, p2_choice = match.p1_choice, match.p2_choice
            if not p1_choice or not p2_choice: return
            result = self.calculate_winner(p1_choice, p2_choice)
            if result == 1:
                match.p1_score += 1
                match.p1.points_for += 1
                match.p2.points_against += 1
            elif result == 2:
                match.p2_score += 1
                match.p2.points_for += 1
                match.p1.points_against += 1
            else:
                match.p1.draws += 1
                match.p2.draws += 1
            result_text = "HÒA" if result == 0 else f"{match.p1.player_id if result == 1 else match.p2.player_id} thắng"
            self.gui.add_log(f"[M{match.match_id}] Result: {result_text} ({match.p1_score}-{match.p2_score})", "INFO")
            self.broadcast('GAME_RESULT', {'match_id': match.match_id, 'p1': match.p1.player_id, 'p2': match.p2.player_id, 'p1_choice': p1_choice, 'p2_choice': p2_choice, 'p1_score': match.p1_score, 'p2_score': match.p2_score, 'result': result})
            match.p1_choice = None
            match.p2_choice = None
            if match.p1_score >= match.target_score: self.end_match(match, match.p1, match.p2)
            elif match.p2_score >= match.target_score: self.end_match(match, match.p2, match.p1)
    
    def calculate_winner(self, c1: str, c2: str) -> int:
        if c1 == c2: return 0
        wins = {('ROCK', 'SCISSORS'): 1, ('SCISSORS', 'PAPER'): 1, ('PAPER', 'ROCK'): 1}
        return 1 if (c1, c2) in wins else 2
    
    def end_match(self, match: Match, winner: Player, loser: Player):
        match.completed = True
        if loser.match_start_time: loser.survival_time = (datetime.now() - loser.match_start_time).total_seconds()
        loser.stage = self.current_round - 1
        loser.eliminated = True
        self.gui.add_log(f"✓ Match {match.match_id} Done: {winner.player_id} wins!", "SUCCESS")
        self.gui.update_player_list(self.players, self.admin)
        self.broadcast('MATCH_END', {'match_id': match.match_id, 'winner': winner.player_id, 'loser': loser.player_id, 'score': f"{match.p1_score}-{match.p2_score}"})
        self.send_message(loser, 'ELIMINATED', {'message': 'Bạn đã bị loại!', 'countdown': 10})
        if all(m.completed for m in self.active_matches): threading.Timer(3, self.check_next_round).start()

    def check_next_round(self):
        with self.lock: active_players = [p for p in self.players.values() if not p.eliminated]
        if len(active_players) == 4 and self.current_round == 1: threading.Timer(2, lambda: self.start_round(2, 5)).start()
        elif len(active_players) == 2 and self.current_round == 2: threading.Timer(2, lambda: self.start_round(3, 5)).start()
        elif len(active_players) == 1 and self.current_round == 3: self.end_tournament(active_players[0])
    
    def end_tournament(self, champion: Player):
        self.gui.add_log(f"🏆 CHAMPION: {champion.player_id} 🏆", "GAME")
        self.gui.game_status_label.config(text="FINISHED", fg="#107C10")
        champion.stage = 3
        ranking = self.calculate_ranking()
        self.broadcast('TOURNAMENT_END', {'champion': champion.player_id, 'ranking': ranking})
        self.gui.add_log("Final Ranking sent.", "INFO")
    
    def calculate_ranking(self) -> List[dict]:
        with self.lock: players_list = list(self.players.values())
        
        # --- [UPDATED] Logic xếp hạng: Ưu tiên người Connected, sau đó đến người AFK ---
        # Key sorting (Descending):
        # 1. Connected Status (1 = Connect, 0 = AFK) -> Người connect xếp trên.
        # 2. (Nếu AFK) Time: Thời gian càng lớn (mới disconnect) thì càng "tốt" hơn người disconnect sớm.
        # 3. Stage, Points, Draws, Survival Time (Logic cũ)
        def ranking_key(p: Player):
            conn_status = 1 if p.is_connected else 0
            # Nếu connected, time coi như max. Nếu AFK, dùng timestamp.
            # Sắp xếp giảm dần -> Time lớn (mới) xếp trên Time nhỏ (cũ).
            d_time = p.disconnect_time.timestamp() if p.disconnect_time else float('inf')
            
            return (
                conn_status,                # Ưu tiên 1: Kết nối
                d_time,                     # Ưu tiên 2: Thời gian disconnect (Càng muộn càng cao)
                p.stage,                    # Ưu tiên 3: Vòng đấu
                p.points_for - p.points_against, 
                p.draws, 
                p.survival_time
            )
            
        players_list.sort(key=ranking_key, reverse=True)
        # -------------------------------------------------------------------------------
        
        ranking = []
        for rank, p in enumerate(players_list, 1):
            ranking.append({'rank': rank, 'player_id': p.player_id, 'stage': p.stage, 'points_for': p.points_for, 'points_against': p.points_against, 'goal_diff': p.points_for - p.points_against, 'draws': p.draws, 'survival_time': round(p.survival_time, 2)})
        return ranking
    
    def handle_disconnect(self, player: Player):
        with self.lock:
            if player.is_admin:
                self.gui.add_log("Admin disconnected", "WARNING")
                self.admin = None
            else:
                # Handle match forfeit on disconnect (Logic cũ giữ nguyên)
                if self.game_started:
                    for match in self.active_matches:
                        if not match.completed and (match.p1 == player or match.p2 == player):
                            winner = match.p2 if match.p1 == player else match.p1
                            loser = player
                            if winner == match.p1: match.p1_score = match.target_score
                            else: match.p2_score = match.target_score
                            self.gui.add_log(f"⚠️ Player {player.player_id} disconnected during Match {match.match_id}. Forfeit triggered.", "WARNING")
                            threading.Thread(target=self.end_match, args=(match, winner, loser), daemon=True).start()
                            break
                
                # --- [UPDATED] KHÔNG XÓA PLAYER, CHỈ ĐÁNH DẤU AFK ---
                if player.is_connected: # Chỉ xử lý nếu chưa xử lý
                    player.is_connected = False
                    player.eliminated = True # Loại khỏi giải đấu để không bắt cặp nữa
                    player.disconnect_time = datetime.now() # Ghi lại thời gian để xếp hạng
                    player.conn = None # Giải phóng socket connection
                    self.gui.add_log(f"Player '{player.player_id}' marked as AFK/Disconnected", "WARNING")
                # --------------------------------------------------
        
        self.gui.update_player_list(self.players, self.admin)
        self.broadcast_player_list()
    
    def start(self):
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(10)
            self.gui.add_log(f"Server listening on {self.host}:{self.port}", "SUCCESS")
            while self.running:
                try:
                    server_socket.settimeout(1.0)
                    conn, addr = server_socket.accept()
                    threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
                except socket.timeout: continue
                except Exception as e:
                    if self.running: self.gui.add_log(f"Accept error: {e}", "ERROR")
            server_socket.close()
            self.gui.add_log("Server stopped", "WARNING")
        except Exception as e: self.gui.add_log(f"Server error: {e}", "ERROR")

def main():
    root = tk.Tk()
    gui = GameServerGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()