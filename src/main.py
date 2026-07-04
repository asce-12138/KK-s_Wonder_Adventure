import pygame
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.game import Game
from modules.menus.lobby import NetworkLobby
from modules.network_client import get_network_client, reset_network_client
from server import stop_server


def main():
    pygame.init()
    screen_width = 1280
    screen_height = 720
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("KK's Wonder Adventure - kk的奇妙冒险")

    clock = pygame.time.Clock()
    
    current_scene = "lobby"
    lobby = None
    game = None
    network_mode = False
    is_host = False
    local_player_id = 1
    return_to_lobby_flag = False
    disconnect_msg = None
    
    def start_network_game(host, player_id):
        nonlocal current_scene, network_mode, is_host, local_player_id, game
        network_mode = True
        is_host = host
        local_player_id = player_id
        game = None
        current_scene = "game"
    
    def back_to_standalone():
        nonlocal current_scene, network_mode, game
        network_mode = False
        game = None
        current_scene = "standalone_menu"
    
    def return_to_lobby(disconnect_message=None):
        nonlocal current_scene, network_mode, lobby, game, return_to_lobby_flag, disconnect_msg
        return_to_lobby_flag = True
        disconnect_msg = disconnect_message
    
    def do_return_to_lobby():
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
    
    lobby = NetworkLobby(screen, on_start_game=start_network_game, on_back_to_standalone=back_to_standalone)
    
    running = True
    while running:
        dt = clock.tick(30) / 1000.0
        
        if return_to_lobby_flag:
            do_return_to_lobby()
        
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
    
    if lobby:
        lobby.cleanup()
    
    stop_server()
    reset_network_client()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
