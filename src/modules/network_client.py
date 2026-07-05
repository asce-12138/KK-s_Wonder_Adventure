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
        
        # 怪物/掉落物/武器特效/敌人子弹/玩家受伤同步队列
        self.enemy_sync_queue = queue.Queue()
        self.enemy_event_queue = queue.Queue()
        self.item_event_queue = queue.Queue()
        self.weapon_attack_queue = queue.Queue()
        self.enemy_projectile_queue = queue.Queue()
        self.player_damage_queue = queue.Queue()
        
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
            
        elif msg_type == "enemy_sync":
            self.enemy_sync_queue.put(message)
            
        elif msg_type in ("enemy_spawn", "enemy_death", "enemy_damage"):
            self.enemy_event_queue.put(message)
            
        elif msg_type in ("item_spawn", "item_pickup", "item_remove"):
            self.item_event_queue.put(message)
            
        elif msg_type == "weapon_attack":
            self.weapon_attack_queue.put(message)
            
        elif msg_type == "enemy_projectile":
            self.enemy_projectile_queue.put(message)
            
        elif msg_type == "player_damage":
            self.player_damage_queue.put(message)
            
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
    
    def send_enemy_sync(self, enemy_states):
        """发送怪物全量同步状态（主机使用）"""
        if not self.connected or not enemy_states:
            return
        self.send_queue.put({
            "type": "enemy_sync",
            "enemies": enemy_states,
            "timestamp": time.time()
        })
    
    def send_enemy_spawn(self, state):
        """发送怪物生成事件（主机使用）"""
        if not self.connected or not state:
            return
        data = {"type": "enemy_spawn", "timestamp": time.time()}
        data.update(state)
        self.send_queue.put(data)
    
    def send_enemy_death(self, enemy_id, x, y, enemy_type):
        """发送怪物死亡事件（主机使用）"""
        if not self.connected:
            return
        self.send_queue.put({
            "type": "enemy_death",
            "enemy_id": enemy_id,
            "x": x,
            "y": y,
            "enemy_type": enemy_type,
            "timestamp": time.time()
        })
    
    def send_enemy_damage(self, enemy_id, damage):
        """发送怪物伤害事件（加入方使用）"""
        if not self.connected:
            return
        self.send_queue.put({
            "type": "enemy_damage",
            "enemy_id": enemy_id,
            "damage": damage,
            "timestamp": time.time()
        })
    
    def send_item_spawn(self, item_id, item_type, x, y):
        """发送掉落物生成事件（主机使用）"""
        if not self.connected:
            return
        self.send_queue.put({
            "type": "item_spawn",
            "item_id": item_id,
            "item_type": item_type,
            "x": x,
            "y": y,
            "timestamp": time.time()
        })
    
    def send_item_pickup(self, item_id):
        """发送掉落物拾取事件（双方都可能使用）"""
        if not self.connected:
            return
        self.send_queue.put({
            "type": "item_pickup",
            "item_id": item_id,
            "timestamp": time.time()
        })
    
    def send_item_remove(self, item_id):
        """发送掉落物移除事件（主机使用）"""
        if not self.connected:
            return
        self.send_queue.put({
            "type": "item_remove",
            "item_id": item_id,
            "timestamp": time.time()
        })
    
    def send_weapon_attack(self, weapon_type, x, y, direction, level=1, is_mega=False):
        """发送武器攻击特效事件"""
        if not self.connected:
            return
        self.send_queue.put({
            "type": "weapon_attack",
            "weapon_type": weapon_type,
            "x": x,
            "y": y,
            "direction_x": direction.x if hasattr(direction, 'x') else direction[0],
            "direction_y": direction.y if hasattr(direction, 'y') else direction[1],
            "level": level,
            "is_mega": is_mega,
            "timestamp": time.time()
        })
    
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
    
    def get_enemy_sync_data(self):
        """获取最新的怪物同步数据，消费队列中所有旧数据只保留最新"""
        latest_data = None
        while not self.enemy_sync_queue.empty():
            try:
                latest_data = self.enemy_sync_queue.get_nowait()
            except queue.Empty:
                break
        return latest_data
    
    def get_enemy_events(self):
        """获取所有待处理的怪物事件"""
        events = []
        while not self.enemy_event_queue.empty():
            try:
                events.append(self.enemy_event_queue.get_nowait())
            except queue.Empty:
                break
        return events
    
    def get_item_events(self):
        """获取所有待处理的掉落物事件"""
        events = []
        while not self.item_event_queue.empty():
            try:
                events.append(self.item_event_queue.get_nowait())
            except queue.Empty:
                break
        return events
    
    def get_weapon_attack_events(self):
        """获取所有待处理的武器攻击特效事件"""
        events = []
        while not self.weapon_attack_queue.empty():
            try:
                events.append(self.weapon_attack_queue.get_nowait())
            except queue.Empty:
                break
        return events
    
    def send_enemy_projectile(self, event):
        """发送敌人投射物创建事件（主机使用）"""
        if not self.connected or not event:
            return
        data = {"type": "enemy_projectile", "timestamp": time.time()}
        data.update(event)
        self.send_queue.put(data)
    
    def get_enemy_projectile_events(self):
        """获取所有待处理的敌人投射物事件"""
        events = []
        while not self.enemy_projectile_queue.empty():
            try:
                events.append(self.enemy_projectile_queue.get_nowait())
            except queue.Empty:
                break
        return events
    
    def send_player_damage(self, amount, damage_type="enemy", knockback_dx=0.0, knockback_dy=0.0, knockback_distance=0.0):
        """发送玩家受伤事件（主机通知加入方）"""
        if not self.connected:
            return
        self.send_queue.put({
            "type": "player_damage",
            "amount": amount,
            "damage_type": damage_type,
            "knockback_dx": knockback_dx,
            "knockback_dy": knockback_dy,
            "knockback_distance": knockback_distance,
            "timestamp": time.time()
        })
    
    def get_player_damage_events(self):
        """获取所有待处理的玩家受伤事件"""
        events = []
        while not self.player_damage_queue.empty():
            try:
                events.append(self.player_damage_queue.get_nowait())
            except queue.Empty:
                break
        return events
    
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
