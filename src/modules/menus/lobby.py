import pygame
import sys
import os
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from ..utils import FontManager
from ..network_client import get_network_client, reset_network_client
from server import start_server, stop_server, get_server


class TextInputBox:
    """文本输入框组件，仅允许输入数字和小数点"""
    
    def __init__(self, x, y, width, height, placeholder="", default_text="", max_length=15):
        self.rect = pygame.Rect(x, y, width, height)
        self.width = width
        self.height = height
        self.text = default_text
        self.placeholder = placeholder
        self.max_length = max_length
        self.active = False
        self.font = FontManager.get_font(24)
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_blink_interval = 0.5
        
        self.bg_color = (30, 30, 30)
        self.active_bg_color = (50, 50, 50)
        self.border_color = (100, 100, 100)
        self.active_border_color = (100, 200, 255)
        self.text_color = (255, 255, 255)
        self.placeholder_color = (120, 120, 120)
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active
        
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_DELETE:
                self.text = ""
            elif event.unicode in '0123456789.' and len(self.text) < self.max_length:
                if event.unicode == '.' and '.' in self.text:
                    pass
                else:
                    self.text += event.unicode
            return True
        return False
    
    def update(self, dt):
        self.cursor_timer += dt
        if self.cursor_timer >= self.cursor_blink_interval:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible
    
    def render(self, screen):
        bg_color = self.active_bg_color if self.active else self.bg_color
        border_color = self.active_border_color if self.active else self.border_color
        
        pygame.draw.rect(screen, bg_color, self.rect)
        pygame.draw.rect(screen, border_color, self.rect, 2)
        
        if self.text:
            text_surface = self.font.render(self.text, True, self.text_color)
        else:
            text_surface = self.font.render(self.placeholder, True, self.placeholder_color)
        
        text_rect = text_surface.get_rect()
        text_rect.left = self.rect.left + 10
        text_rect.centery = self.rect.centery
        screen.blit(text_surface, text_rect)
        
        if self.active and self.cursor_visible:
            cursor_x = text_rect.right + 2
            if self.text:
                cursor_x = text_rect.right + 2
            else:
                cursor_x = self.rect.left + 10
            cursor_y_start = self.rect.top + 8
            cursor_y_end = self.rect.bottom - 8
            pygame.draw.line(screen, self.text_color, (cursor_x, cursor_y_start), (cursor_x, cursor_y_end), 2)
    
    def get_text(self):
        return self.text
    
    def set_text(self, text):
        self.text = text
    
    def clear(self):
        self.text = ""


class Button:
    """按钮组件，支持鼠标悬浮变色"""
    
    def __init__(self, x, y, width, height, text, callback=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.hovered = False
        self.font = FontManager.get_font(28)
        
        self.bg_color = (50, 50, 70)
        self.hover_bg_color = (70, 100, 150)
        self.disabled_bg_color = (40, 40, 40)
        self.border_color = (150, 150, 150)
        self.hover_border_color = (100, 200, 255)
        self.text_color = (220, 220, 220)
        self.hover_text_color = (255, 255, 255)
        self.disabled_text_color = (100, 100, 100)
        
        self.enabled = True
        self.clicked = False
    
    def handle_event(self, event):
        if not self.enabled:
            return False
        
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.clicked = True
                if self.callback:
                    self.callback()
                return True
        return False
    
    def render(self, screen):
        if not self.enabled:
            bg_color = self.disabled_bg_color
            border_color = self.border_color
            text_color = self.disabled_text_color
        elif self.hovered:
            bg_color = self.hover_bg_color
            border_color = self.hover_border_color
            text_color = self.hover_text_color
        else:
            bg_color = self.bg_color
            border_color = self.border_color
            text_color = self.text_color
        
        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)
        
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
    
    def set_enabled(self, enabled):
        self.enabled = enabled


class NetworkLobby:
    """
    联机大厅UI - 游戏启动首界面
    提供创建房间、加入房间、输入IP/端口、状态显示等功能
    """
    
    def __init__(self, screen, on_start_game=None, on_back_to_standalone=None):
        self.screen = screen
        self.on_start_game = on_start_game
        self.on_back_to_standalone = on_back_to_standalone
        
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        
        self.title_font = FontManager.get_font(56)
        self.subtitle_font = FontManager.get_font(28)
        self.label_font = FontManager.get_font(22)
        self.status_font = FontManager.get_font(24)
        self.small_font = FontManager.get_font(18)
        
        self.state = "idle"
        self.status_message = "请选择创建房间或加入房间"
        self.status_color = (200, 200, 200)
        
        self.is_host = False
        self.server_running = False
        self.waiting_for_player = False
        self.connecting = False
        
        self._init_ui()
        
        self.network_client = get_network_client()
        self.network_client.on_connected = self._on_connected
        self.network_client.on_disconnected = self._on_disconnected
        self.network_client.on_game_start = self._on_game_start
        
        self.check_thread = None
        self.check_running = False
    
    def _init_ui(self):
        center_x = self.screen_width // 2
        
        input_width = 250
        input_height = 45
        label_width = 100
        button_width = 200
        button_height = 55
        small_button_width = 120
        small_button_height = 40
        
        self.ip_input = TextInputBox(
            center_x - input_width // 2 + 30, 280,
            input_width, input_height,
            placeholder="输入IP地址",
            default_text=self._get_local_ip(),
            max_length=15
        )
        
        self.port_input = TextInputBox(
            center_x - input_width // 2 + 30, 350,
            input_width, input_height,
            placeholder="输入端口",
            default_text="5555",
            max_length=5
        )
        
        self.create_button = Button(
            center_x - button_width - 20, 420,
            button_width, button_height,
            "创建房间",
            callback=self._on_create_room
        )
        
        self.join_button = Button(
            center_x + 20, 420,
            button_width, button_height,
            "加入房间",
            callback=self._on_join_room
        )
        
        self.back_button = Button(
            20, self.screen_height - small_button_height - 20,
            small_button_width, small_button_height,
            "返回单机",
            callback=self._on_back
        )
        
        self.cancel_button = Button(
            center_x - small_button_width // 2, 510,
            small_button_width, small_button_height,
            "取消",
            callback=self._on_cancel
        )
        self.cancel_button.set_enabled(False)
    
    def _get_local_ip(self):
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def _on_create_room(self):
        if self.connecting or self.server_running:
            return
        
        try:
            port_text = self.port_input.get_text().strip()
            port = int(port_text) if port_text else 5555
            if port < 1 or port > 65535:
                port = 5555
        except ValueError:
            port = 5555
        
        self.state = "creating"
        self.is_host = True
        self.connecting = True
        
        self.create_button.set_enabled(False)
        self.join_button.set_enabled(False)
        self.ip_input.active = False
        self.port_input.active = False
        self.cancel_button.set_enabled(True)
        
        self._set_status("正在启动服务端...", (255, 255, 0))
        
        def start_server_and_connect():
            try:
                success = start_server(port=port)
                if not success:
                    self._set_status("服务端启动失败！端口可能被占用", (255, 50, 50))
                    self._reset_to_idle()
                    return
                
                self.server_running = True
                time.sleep(0.3)
                
                local_ip = get_server().get_local_ip() if get_server() else self._get_local_ip()
                self._set_status(f"服务端已启动，正在进入房间...", (255, 255, 0))
                
                host_connect_success = self.network_client.connect("127.0.0.1", port, timeout=5.0)
                if not host_connect_success:
                    self._set_status("本地连接失败！", (255, 50, 50))
                    self._reset_to_idle()
                    return
                
                self.waiting_for_player = True
                self._set_status(f"房间已创建！IP: {local_ip}  端口: {port}，等待玩家2加入...", (0, 255, 255))
                
                self.check_running = True
                self.check_thread = threading.Thread(target=self._wait_for_player2, daemon=True)
                self.check_thread.start()
                
            except Exception as e:
                self._set_status(f"创建房间出错: {str(e)}", (255, 50, 50))
                self._reset_to_idle()
        
        threading.Thread(target=start_server_and_connect, daemon=True).start()
    
    def _wait_for_player2(self):
        while self.check_running and self.waiting_for_player:
            server = get_server()
            if server and server.get_client_count() >= 2:
                self._set_status("玩家2已加入！准备开始游戏...", (0, 255, 0))
                time.sleep(0.5)
                break
            time.sleep(0.5)
    
    def _on_join_room(self):
        if self.connecting or self.server_running:
            return
        
        ip = self.ip_input.get_text().strip()
        port_text = self.port_input.get_text().strip()
        
        if not ip:
            self._set_status("请输入主机IP地址！", (255, 100, 100))
            return
        
        try:
            port = int(port_text) if port_text else 5555
            if port < 1 or port > 65535:
                port = 5555
        except ValueError:
            self._set_status("端口格式不正确！", (255, 100, 100))
            return
        
        self.state = "joining"
        self.is_host = False
        self.connecting = True
        
        self.create_button.set_enabled(False)
        self.join_button.set_enabled(False)
        self.ip_input.active = False
        self.port_input.active = False
        self.cancel_button.set_enabled(True)
        
        self._set_status(f"正在连接到 {ip}:{port} ...", (255, 255, 0))
        
        def connect_thread():
            success = self.network_client.connect(ip, port, timeout=10.0)
            if not success:
                self._set_status(f"连接失败！请检查IP和端口是否正确", (255, 50, 50))
                self._reset_to_idle()
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def _on_connected(self, player_id):
        if self.is_host:
            self._set_status(f"你是玩家{player_id}(主机)，等待玩家2加入...", (0, 255, 255))
        else:
            self.waiting_for_player = False
            self.check_running = False
            self._set_status(f"连接成功！你是玩家{player_id}，等待主机开始游戏...", (0, 255, 0))
    
    def _on_game_start(self):
        self._set_status("游戏开始！", (0, 255, 0))
        
        def start_game_delayed():
            time.sleep(0.3)
            if self.on_start_game:
                self.on_start_game(self.is_host, self.network_client.get_player_id())
        
        threading.Thread(target=start_game_delayed, daemon=True).start()
    
    def _on_disconnected(self):
        self._set_status("连接已断开！", (255, 50, 50))
        self.waiting_for_player = False
        self.check_running = False
        self._reset_to_idle()
    
    def _on_cancel(self):
        self.check_running = False
        self.waiting_for_player = False
        
        if self.network_client and self.network_client.is_connected():
            self.network_client.disconnect()
        
        reset_network_client()
        self.network_client = get_network_client()
        self.network_client.on_connected = self._on_connected
        self.network_client.on_disconnected = self._on_disconnected
        self.network_client.on_game_start = self._on_game_start
        
        if self.server_running:
            stop_server()
            self.server_running = False
        
        self._set_status("已取消，返回大厅", (200, 200, 200))
        self._reset_to_idle()
    
    def _on_back(self):
        self._on_cancel()
        if self.on_back_to_standalone:
            self.on_back_to_standalone()
    
    def _reset_to_idle(self):
        self.connecting = False
        self.state = "idle"
        self.create_button.set_enabled(True)
        self.join_button.set_enabled(True)
        self.cancel_button.set_enabled(False)
    
    def _set_status(self, message, color=(200, 200, 200)):
        self.status_message = message
        self.status_color = color
    
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.connecting or self.server_running:
                    self._on_cancel()
                else:
                    self._on_back()
                return
        
        self.ip_input.handle_event(event)
        self.port_input.handle_event(event)
        self.create_button.handle_event(event)
        self.join_button.handle_event(event)
        self.back_button.handle_event(event)
        self.cancel_button.handle_event(event)
    
    def update(self, dt):
        self.ip_input.update(dt)
        self.port_input.update(dt)
        
        if self.server_running and self.waiting_for_player:
            server = get_server()
            if server and server.get_client_count() >= 1:
                pass
    
    def render(self):
        self.screen.fill((20, 20, 30))
        
        title_text = self.title_font.render("KK's Wonder Adventure", True, (255, 215, 0))
        title_rect = title_text.get_rect(center=(self.screen_width // 2, 100))
        self.screen.blit(title_text, title_rect)
        
        subtitle_text = self.subtitle_font.render("局域网双人联机", True, (180, 180, 220))
        subtitle_rect = subtitle_text.get_rect(center=(self.screen_width // 2, 160))
        self.screen.blit(subtitle_text, subtitle_rect)
        
        ip_label = self.label_font.render("IP地址:", True, (200, 200, 200))
        self.screen.blit(ip_label, (self.ip_input.rect.left - 110, self.ip_input.rect.centery - 10))
        
        port_label = self.label_font.render("端口:", True, (200, 200, 200))
        self.screen.blit(port_label, (self.port_input.rect.left - 110, self.port_input.rect.centery - 10))
        
        self.ip_input.render(self.screen)
        self.port_input.render(self.screen)
        
        self.create_button.render(self.screen)
        self.join_button.render(self.screen)
        self.back_button.render(self.screen)
        
        if self.connecting or self.server_running:
            self.cancel_button.render(self.screen)
        
        status_text = self.status_font.render(self.status_message, True, self.status_color)
        status_rect = status_text.get_rect(center=(self.screen_width // 2, 210))
        
        shadow_text = self.status_font.render(self.status_message, True, (0, 0, 0))
        shadow_rect = shadow_text.get_rect(center=(self.screen_width // 2 + 2, 212))
        self.screen.blit(shadow_text, shadow_rect)
        self.screen.blit(status_text, status_rect)
        
        if self.is_host and self.server_running and self.waiting_for_player:
            hint_text = self.small_font.render("请将上述IP和端口告诉好友，让他们点击【加入房间】连接", True, (150, 200, 255))
            hint_rect = hint_text.get_rect(center=(self.screen_width // 2, 240))
            self.screen.blit(hint_text, hint_rect)
        
        tip_text = self.small_font.render("提示: 创建房间者自动作为主机，另一台设备输入主机IP即可加入", True, (100, 100, 120))
        tip_rect = tip_text.get_rect(center=(self.screen_width // 2, self.screen_height - 80))
        self.screen.blit(tip_text, tip_rect)
    
    def cleanup(self):
        self.check_running = False
        self.waiting_for_player = False
        if self.network_client and self.network_client.is_connected():
            self.network_client.disconnect()
        if self.server_running:
            stop_server()
            self.server_running = False
        reset_network_client()
    
    def is_in_lobby(self):
        return True
