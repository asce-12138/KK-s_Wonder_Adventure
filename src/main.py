import pygame
import sys
from modules.game import Game

def main():
    pygame.init()
    # 尝试初始化音频,失败也不影响游戏运行(只是没声音)
    try:
        pygame.mixer.init()
    except pygame.error as e:
        print(f"⚠ 音频初始化失败,游戏将以无声模式运行: {e}")
    screen_width = 1280
    screen_height = 720
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("像素生存")

    clock = pygame.time.Clock()
    game = Game(screen)
    
    while game.running:
        dt = clock.tick(30) / 1000.0  # 转换为秒
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            game.handle_event(event)
        
        game.update(dt)
        game.render()
        pygame.display.flip()
    
    # 如果游戏结束，退出
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main() 