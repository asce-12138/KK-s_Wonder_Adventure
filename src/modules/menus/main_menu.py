import pygame
from ..resource_manager import resource_manager
from ..utils import FontManager

class MainMenu:
    def __init__(self, screen, extra_options=None):
        self.screen = screen
        self.is_active = True
        
        self.options = ["开始新游戏", "读取存档", "设置", "退出游戏"]
        self.actions = ["start", "load", "settings", "quit"]
        
        if extra_options:
            for opt in extra_options:
                self.options.append(opt['text'])
                self.actions.append(opt['action'])
        
        self.selected_index = 0
        
        self.title_font = FontManager.get_font(74)
        self.option_font = FontManager.get_font(50)
        
        self.title_color = (255, 255, 255)
        self.text_color = (200, 200, 200)
        self.hover_color = (255, 255, 0)
        
        self.screen_center_x = self.screen.get_width() // 2
        self.title_y = 100
        self.first_option_y = 300
        self.option_padding = 60
        
        self.option_rects = []
        
        try:
            self.background = resource_manager.load_image('menu_background', 'images/menu/background.png')
            self.background = pygame.transform.scale(self.background, (screen.get_width(), screen.get_height()))
        except:
            self.background = None
            
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_UP, pygame.K_w]:
                self.selected_index = (self.selected_index - 1) % len(self.options)
                resource_manager.play_sound("menu_move")
            elif event.key in [pygame.K_DOWN, pygame.K_s]:
                self.selected_index = (self.selected_index + 1) % len(self.options)
                resource_manager.play_sound("menu_move")
            elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                resource_manager.play_sound("menu_select")
                return self.actions[self.selected_index]
                
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            for i, rect in enumerate(self.option_rects):
                if rect.collidepoint(mouse_pos):
                    resource_manager.play_sound("menu_select")
                    return self.actions[i]
                    
        elif event.type == pygame.MOUSEMOTION:
            mouse_pos = pygame.mouse.get_pos()
            for i, rect in enumerate(self.option_rects):
                if rect.collidepoint(mouse_pos):
                    if self.selected_index != i:
                        self.selected_index = i
                        resource_manager.play_sound("menu_move")
                    break
                    
        return None
        
    def render(self):
        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill((0, 0, 0))
            
        title_text = self.title_font.render("kk的奇妙冒险", True, self.title_color)
        title_rect = title_text.get_rect(center=(self.screen_center_x, self.title_y))
        self.screen.blit(title_text, title_rect)
        
        self.option_rects.clear()
        
        total_options = len(self.options)
        start_y = self.first_option_y - (total_options - 4) * 30 if total_options > 4 else self.first_option_y
        
        for i, option in enumerate(self.options):
            color = self.hover_color if i == self.selected_index else self.text_color
            text = self.option_font.render(option, True, color)
            rect = text.get_rect(center=(self.screen_center_x, start_y + i * self.option_padding))
            self.screen.blit(text, rect)
            self.option_rects.append(rect)
            
        pygame.display.flip() 
