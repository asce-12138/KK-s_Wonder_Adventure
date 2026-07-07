# ============================================================
# C1-1: 游戏启动入口 - main.py
# 功能: 初始化Pygame、创建窗口、管理场景切换、控制主循环
# 对应文档: https://github.com/.../CODE_DOCUMENTATION.md#c1---游戏启动入口
# ============================================================
import pygame
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.game import Game
from modules.menus.lobby import NetworkLobby
from modules.network_client import get_network_client, reset_network_client
from server import stop_server


def main():
    # ============================================================
    # C1-2: 初始化阶段 - Pygame、窗口、时钟
    # ============================================================
    pygame.init()
    
    screen_width = 1280
    screen_height = 720
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("KK's Wonder Adventure - kk的奇妙冒险")
    
    clock = pygame.time.Clock()
    
    # ============================================================
    # C1-3: 场景状态变量
    # 状态机: lobby → standalone_menu → game
    # ============================================================
    current_scene = "lobby"
    lobby = None
    game = None
    network_mode = False
    is_host = False
    local_player_id = 1
    return_to_lobby_flag = False
    disconnect_msg = None
    
    # ============================================================
    # C1-4: 场景切换回调函数
    # ============================================================
    def start_network_game(host, player_id):
        """启动网络联机游戏"""
        nonlocal current_scene, network_mode, is_host, local_player_id, game
        network_mode = True
        is_host = host
        local_player_id = player_id
        game = None
        current_scene = "game"
    
    def back_to_standalone():
        """返回单机模式"""
        nonlocal current_scene, network_mode, game
        network_mode = False
        game = None
        current_scene = "standalone_menu"
    
    def return_to_lobby(disconnect_message=None):
        """标记返回网络大厅"""
        nonlocal return_to_lobby_flag, disconnect_msg
        return_to_lobby_flag = True
        disconnect_msg = disconnect_message
    
    def do_return_to_lobby():
        """执行返回网络大厅操作"""
        nonlocal current_scene, network_mode, lobby, game, return_to_lobby_flag, disconnect_msg
        network_mode = False
        
        stop_server()
        reset_network_client()
        
        current_scene = "lobby"
        game = None
        lobby = NetworkLobby(screen, on_start_game=start_network_game, on_back_to_standalone=back_to_standalone)
        
        if disconnect_msg:
            lobby._set_status(disconnect_msg, (255, 80, 80))
        
        return_to_lobby_flag = False
        disconnect_msg = None
    
    # ============================================================
    # C1-5: 创建初始场景（网络大厅）
    # ============================================================
    lobby = NetworkLobby(screen, on_start_game=start_network_game, on_back_to_standalone=back_to_standalone)
    
    # ============================================================
    # C1-6: 游戏主循环（30FPS）
    # 流程: 事件处理 → 更新 → 渲染
    # ============================================================
    running = True
    while running:
        dt = clock.tick(30) / 1000.0
        
        # 处理返回大厅请求
        if return_to_lobby_flag:
            do_return_to_lobby()
        
        # ============================================================
        # C1-7: 事件分发 - 根据当前场景路由事件
        # ============================================================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            
            if current_scene == "lobby":
                lobby.handle_event(event)
            elif current_scene == "standalone_menu":
                if game is None:
                    game = Game(screen, network_mode=False, on_return_to_lobby=return_to_lobby)
                game.handle_event(event)
            elif current_scene == "game":
                if game is None:
                    game = Game(
                        screen, 
                        network_mode=True, 
                        is_host=is_host, 
                        local_player_id=local_player_id,
                        on_return_to_lobby=return_to_lobby
                    )
                game.handle_event(event)
        
        if not running:
            break
        
        if return_to_lobby_flag:
            do_return_to_lobby()
            continue
        
        # ============================================================
        # C1-8: 更新和渲染 - 根据当前场景执行
        # ============================================================
        if current_scene == "lobby":
            lobby.update(dt)
            lobby.render()
            pygame.display.flip()
        elif current_scene == "standalone_menu" or current_scene == "game":
            if game:
                game.update(dt)
                game.render()
                if not game.running:
                    if current_scene == "standalone_menu":
                        running = False
                    else:
                        return_to_lobby_flag = True
    
    # ============================================================
    # C1-9: 资源清理
    # ============================================================
    if lobby:
        lobby.cleanup()
    
    stop_server()
    reset_network_client()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
