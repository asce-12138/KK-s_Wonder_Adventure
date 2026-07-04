import socket
import threading
import json
import sys
import select

class GameServer:
    """
    KK's Wonder Adventure 局域网双人联机TCP服务端
    负责在两个客户端之间转发游戏同步数据
    """
    
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.client_addresses = []
        self.running = False
        self.lock = threading.Lock()
        self.server_thread = None
        
    def get_local_ip(self):
        """获取本机内网IPv4地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                return ip
            except Exception:
                return "127.0.0.1"
    
    def start(self):
        """启动服务端"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(2)
            self.server_socket.settimeout(1.0)
            self.running = True
            
            self.server_thread = threading.Thread(target=self._accept_clients, daemon=True)
            self.server_thread.start()
            
            print(f"[服务端] 已启动，监听端口 {self.port}")
            print(f"[服务端] 本机IP: {self.get_local_ip()}")
            return True
        except Exception as e:
            print(f"[服务端] 启动失败: {e}")
            return False
    
    def _accept_clients(self):
        """接受客户端连接的线程函数"""
        print("[服务端] 等待玩家连接...")
        while self.running and len(self.clients) < 2:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_socket.setblocking(False)
                
                with self.lock:
                    self.clients.append(client_socket)
                    self.client_addresses.append(client_address)
                
                player_id = len(self.clients)
                print(f"[服务端] 玩家{player_id}已连接: {client_address}")
                
                welcome_msg = json.dumps({
                    "type": "welcome",
                    "player_id": player_id,
                    "message": f"你是玩家{player_id}"
                }) + "\n"
                try:
                    client_socket.send(welcome_msg.encode('utf-8'))
                except Exception:
                    pass
                
                recv_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, player_id),
                    daemon=True
                )
                recv_thread.start()
                
                if len(self.clients) == 2:
                    self._broadcast(json.dumps({
                        "type": "game_start",
                        "message": "两名玩家均已连接，游戏开始！"
                    }))
                    print("[服务端] 两名玩家已就绪，游戏开始！")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[服务端] 接受连接出错: {e}")
                break
    
    def _handle_client(self, client_socket, player_id):
        """处理单个客户端的数据接收"""
        buffer = ""
        while self.running:
            try:
                readable, _, _ = select.select([client_socket], [], [], 1.0)
                if not readable:
                    continue
                
                data = client_socket.recv(4096)
                if not data:
                    print(f"[服务端] 玩家{player_id}断开连接")
                    break
                
                buffer += data.decode('utf-8')
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self._process_message(client_socket, player_id, line)
                        
            except ConnectionResetError:
                print(f"[服务端] 玩家{player_id}连接被重置")
                break
            except Exception as e:
                if self.running:
                    print(f"[服务端] 处理玩家{player_id}数据出错: {e}")
                break
        
        self._remove_client(client_socket, player_id)
    
    def _process_message(self, sender_socket, sender_id, message_str):
        """处理来自客户端的消息并转发"""
        try:
            message = json.loads(message_str)
            message['sender_id'] = sender_id
            self._broadcast(json.dumps(message), exclude_socket=sender_socket)
        except json.JSONDecodeError:
            pass
    
    def _broadcast(self, message, exclude_socket=None):
        """向所有连接的客户端广播消息"""
        if not message.endswith('\n'):
            message += '\n'
        
        with self.lock:
            for client in self.clients:
                if client != exclude_socket:
                    encoded = message.encode('utf-8')
                    for _ in range(20):
                        try:
                            sent = client.send(encoded)
                            encoded = encoded[sent:]
                            if not encoded:
                                break
                        except BlockingIOError:
                            import time
                            time.sleep(0.01)
                    else:
                        print(f"[服务端] 转发消息失败")
    
    def _remove_client(self, client_socket, player_id):
        """移除断开连接的客户端"""
        with self.lock:
            if client_socket in self.clients:
                idx = self.clients.index(client_socket)
                self.clients.remove(client_socket)
                if idx < len(self.client_addresses):
                    self.client_addresses.pop(idx)
                try:
                    client_socket.close()
                except Exception:
                    pass
                
                if self.running:
                    self._broadcast(json.dumps({
                        "type": "player_disconnect",
                        "player_id": player_id,
                        "message": f"玩家{player_id}已断开连接"
                    }))
        
        if len(self.clients) == 0 and self.running:
            print("[服务端] 所有玩家已断开")
    
    def stop(self):
        """停止服务端"""
        self.running = False
        
        with self.lock:
            for client in self.clients:
                try:
                    client.close()
                except Exception:
                    pass
            self.clients.clear()
            self.client_addresses.clear()
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        
        print("[服务端] 已停止")
    
    def get_client_count(self):
        """获取当前连接的客户端数量"""
        with self.lock:
            return len(self.clients)

_server_instance = None

def start_server(port=5555):
    """启动全局服务端实例（用于内嵌服务端）"""
    global _server_instance
    if _server_instance:
        stop_server()
    _server_instance = GameServer(port=port)
    return _server_instance.start()

def stop_server():
    """停止全局服务端实例"""
    global _server_instance
    if _server_instance:
        _server_instance.stop()
        _server_instance = None

def get_server():
    """获取全局服务端实例"""
    return _server_instance

if __name__ == "__main__":
    port = 5555
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    
    server = GameServer(port=port)
    if server.start():
        print(f"服务端运行中，按 Ctrl+C 停止...")
        try:
            while server.running:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在停止服务端...")
            server.stop()
