import socket
import threading
import json
import time
import queue


class NetworkClient:
    """
    KK's Wonder Adventure 局域网联机TCP客户端
    负责连接服务端、收发游戏同步数据
    使用独立守护线程，不会卡顿游戏画面
    """
    
    def __init__(self):
        self.client_socket = None
        self.connected = False
        self.running = False
        self.player_id = None
        self.send_queue = queue.Queue()
        self.receive_queue = queue.Queue()
        self.recv_thread = None
        self.send_thread = None
        self.lock = threading.Lock()
        self.on_disconnected = None
        self.on_connected = None
        self.on_game_start = None
        self.last_heartbeat = 0
        self.heartbeat_interval = 3.0
        
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
    
    def connect(self, host, port=5555, timeout=5.0):
        """
        连接到服务端
        
        Args:
            host: 服务端IP地址
            port: 服务端端口
            timeout: 连接超时时间（秒）
            
        Returns:
            bool: 连接是否成功
        """
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(timeout)
            self.client_socket.connect((host, port))
            self.client_socket.setblocking(False)
            self.connected = True
            self.running = True
            self.last_heartbeat = time.time()
            
            self.recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
            self.recv_thread.start()
            self.send_thread.start()
            
            print(f"[客户端] 已连接到服务端 {host}:{port}")
            return True
            
        except socket.timeout:
            print(f"[客户端] 连接超时")
            self._cleanup()
            return False
        except ConnectionRefusedError:
            print(f"[客户端] 连接被拒绝，请确认服务端已启动")
            self._cleanup()
            return False
        except Exception as e:
            print(f"[客户端] 连接失败: {e}")
            self._cleanup()
            return False
    
    def _receive_loop(self):
        """接收数据的线程函数"""
        buffer = ""
        while self.running:
            try:
                if not self.connected or not self.client_socket:
                    break
                
                import select
                readable, _, exceptional = select.select([self.client_socket], [], [self.client_socket], 0.1)
                
                if exceptional:
                    break
                
                if not readable:
                    if time.time() - self.last_heartbeat > 30.0:
                        print("[客户端] 心跳超时，连接可能已断开")
                        break
                    continue
                
                data = self.client_socket.recv(4096)
                if not data:
                    print("[客户端] 服务端关闭了连接")
                    break
                
                self.last_heartbeat = time.time()
                try:
                    buffer += data.decode('utf-8')
                except UnicodeDecodeError:
                    print("[客户端] 收到非法数据，清空缓冲区")
                    buffer = ""
                    continue
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            message = json.loads(line)
                            self._process_message(message)
                        except json.JSONDecodeError:
                            pass
                            
            except ConnectionResetError:
                print("[客户端] 连接被重置")
                break
            except Exception as e:
                if self.running:
                    print(f"[客户端] 接收数据出错: {e}")
                break
        
        self._handle_disconnect()
    
    def _send_loop(self):
        """发送数据的线程函数"""
        while self.running:
            try:
                if not self.connected:
                    time.sleep(0.1)
                    continue
                
                try:
                    message = self.send_queue.get(timeout=0.5)
                    if message:
                        data = json.dumps(message) + '\n'
                        encoded = data.encode('utf-8')
                        with self.lock:
                            if self.client_socket and self.connected:
                                remaining = encoded
                                for _ in range(20):
                                    try:
                                        sent = self.client_socket.send(remaining)
                                        remaining = remaining[sent:]
                                        if not remaining:
                                            break
                                    except BlockingIOError:
                                        time.sleep(0.01)
                                else:
                                    print("[客户端] 发送缓冲区已满，连接不稳定")
                except queue.Empty:
                    if time.time() - self.last_heartbeat > self.heartbeat_interval:
                        self.send_queue.put({"type": "heartbeat", "timestamp": time.time()})
                    continue
                    
            except Exception as e:
                if self.running:
                    print(f"[客户端] 发送数据出错: {e}")
                break
    
    def _process_message(self, message):
        """处理接收到的消息"""
        msg_type = message.get("type", "")
        
        if msg_type == "welcome":
            self.player_id = message.get("player_id", 1)
            print(f"[客户端] {message.get('message', '欢迎')}")
            if self.on_connected:
                self.on_connected(self.player_id)
                
        elif msg_type == "game_start":
            print(f"[客户端] {message.get('message', '游戏开始')}")
            if self.on_game_start:
                self.on_game_start()
                
        elif msg_type == "player_disconnect":
            print(f"[客户端] {message.get('message', '对方断开连接')}")
            self._handle_disconnect()
            
        elif msg_type == "player_data":
            self.receive_queue.put(message)
            
        elif msg_type == "heartbeat":
            self.last_heartbeat = time.time()
    
    def send_player_data(self, world_x, world_y, health, max_health, hero_type, is_moving, facing_right, is_hurt):
        """
        发送本地玩家数据给服务端
        
        Args:
            world_x: 玩家世界X坐标
            world_y: 玩家世界Y坐标
            health: 当前血量
            max_health: 最大血量
            hero_type: 英雄类型
            is_moving: 是否在移动
            facing_right: 是否面朝右
            is_hurt: 是否受伤
        """
        if not self.connected:
            return
            
        data = {
            "type": "player_data",
            "world_x": world_x,
            "world_y": world_y,
            "health": health,
            "max_health": max_health,
            "hero_type": hero_type,
            "is_moving": is_moving,
            "facing_right": facing_right,
            "is_hurt": is_hurt,
            "timestamp": time.time()
        }
        self.send_queue.put(data)
    
    def get_remote_player_data(self):
        """
        获取远程玩家的最新数据
        
        Returns:
            dict or None: 远程玩家数据，如果没有则返回None
        """
        latest_data = None
        while not self.receive_queue.empty():
            try:
                latest_data = self.receive_queue.get_nowait()
            except queue.Empty:
                break
        return latest_data
    
    def _handle_disconnect(self):
        """处理断开连接"""
        was_connected = self.connected
        self.connected = False
        self.running = False
        self._cleanup()
        
        if was_connected and self.on_disconnected:
            self.on_disconnected()
    
    def disconnect(self):
        """主动断开连接"""
        self.running = False
        self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        self.connected = False
        
        with self.lock:
            if self.client_socket:
                try:
                    self.client_socket.close()
                except Exception:
                    pass
                self.client_socket = None
        
        while not self.send_queue.empty():
            try:
                self.send_queue.get_nowait()
            except queue.Empty:
                break
                
        while not self.receive_queue.empty():
            try:
                self.receive_queue.get_nowait()
            except queue.Empty:
                break
    
    def is_connected(self):
        """检查是否已连接"""
        return self.connected and self.running
    
    def get_player_id(self):
        """获取本地玩家ID"""
        return self.player_id


_network_instance = None

def get_network_client():
    """获取全局网络客户端实例"""
    global _network_instance
    if _network_instance is None:
        _network_instance = NetworkClient()
    return _network_instance

def reset_network_client():
    """重置全局网络客户端实例（断线重连时使用）"""
    global _network_instance
    if _network_instance:
        _network_instance.disconnect()
    _network_instance = None
