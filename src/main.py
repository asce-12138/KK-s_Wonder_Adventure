import pygame
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.game import Game
from modules.menus.lobby import NetworkLobby
from modules.network_client import get_network_client, reset_network_client
from server import stop_server


def main():
    # 初始化Pygame库
    pygame.init()
    # 设置游戏窗口尺寸
    screen_width = 1280
    screen_height = 720
    # 创建游戏窗口
    screen = pygame.display.set_mode((screen_width, screen_height))
    # 设置窗口标题
    pygame.display.set_caption("KK's Wonder Adventure - kk的奇妙冒险")

    # 创建时钟对象，用于控制帧率
    clock = pygame.time.Clock()
    
    # 当前场景状态
    current_scene = "lobby"  # lobby: 网络大厅, standalone_menu: 单机菜单, game: 游戏中
    lobby = None  # 网络大厅对象
    game = None  # 游戏对象
    network_mode = False  # 是否为网络模式
    is_host = False  # 是否为主机
    local_player_id = 1  # 本地玩家ID
    return_to_lobby_flag = False  # 返回大厅标志
    disconnect_msg = None  # 断开连接消息
    
    def start_network_game(host, player_id):
        """启动网络联机游戏
        
        Args:
            host: 是否为主机
            player_id: 玩家ID
        """
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
        """标记返回网络大厅
        
        Args:
            disconnect_message: 断开连接时的提示消息
        """
        nonlocal current_scene, network_mode, lobby, game, return_to_lobby_flag, disconnect_msg
        return_to_lobby_flag = True
        disconnect_msg = disconnect_message
    
    def do_return_to_lobby():
        """执行返回网络大厅操作"""
        nonlocal current_scene, network_mode, lobby, game, return_to_lobby_flag, disconnect_msg
        network_mode = False
        
        # 停止服务器和重置网络客户端
        stop_server()
        reset_network_client()
        
        # 切换到大厅场景
        current_scene = "lobby"
        game = None
        lobby = NetworkLobby(screen, on_start_game=start_network_game, on_back_to_standalone=back_to_standalone)
        
        # 如果有断开连接消息，显示提示
        if disconnect_msg:
            lobby._set_status(disconnect_msg, (255, 80, 80))
        
        return_to_lobby_flag = False
        disconnect_msg = None
    
    # 创建网络大厅对象
    lobby = NetworkLobby(screen, on_start_game=start_network_game, on_back_to_standalone=back_to_standalone)
    
    # 游戏主循环
    running = True
    while running:
        # 计算时间增量(秒)，限制帧率为30FPS
        dt = clock.tick(30) / 1000.0
        
        # 处理返回大厅请求
        if return_to_lobby_flag:
            do_return_to_lobby()
        
        # 处理事件队列
        for event in pygame.event.get():
            # 关闭窗口事件
            if event.type == pygame.QUIT:
                running = False
                break
            
            # 根据当前场景分发事件
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
        
        # 如果游戏已结束，退出循环
        if not running:
            break
        
        # 再次检查返回大厅请求
        if return_to_lobby_flag:
            do_return_to_lobby()
            continue
        
        # 根据当前场景执行更新和渲染
        if current_scene == "lobby":
            lobby.update(dt)
            lobby.render()
            pygame.display.flip()
        elif current_scene == "standalone_menu" or current_scene == "game":
            if game:
                game.update(dt)
                game.render()
                # 如果游戏不再运行，处理退出逻辑
                if not game.running:
                    if current_scene == "standalone_menu":
                        running = False
                    else:
                        return_to_lobby_flag = True
    
    # 清理资源
    if lobby:
        lobby.cleanup()
    
    stop_server()
    reset_network_client()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
