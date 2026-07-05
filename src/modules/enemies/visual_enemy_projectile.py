import pygame
import math
from ..resource_manager import resource_manager


class VisualEnemyProjectile(pygame.sprite.Sprite):
    """敌人投射物的视觉副本（仅渲染，不造成伤害）
    
    用于联机同步时，在客户端显示主机端敌人发射的子弹。
    """
    
    def __init__(self, x, y, direction_x, direction_y, enemy_type, speed=200, lifetime=5.0, bullet_type=1):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.direction_x = float(direction_x)
        self.direction_y = float(direction_y)
        self.enemy_type = enemy_type
        self.speed = float(speed)
        self.lifetime = float(lifetime)
        self.bullet_type = bullet_type
        self.visual_only = True
        
        # 根据敌人类型加载/生成图像
        self.image = self._create_image()
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
    
    def _create_image(self):
        """根据敌人类型创建投射物图像"""
        if self.enemy_type == 'plant':
            if self.bullet_type == 1:
                image_path = 'images/enemy/plant_Bullet1.png'
                cache_key = 'plant_bullet_1'
            else:
                image_path = 'images/enemy/plant_Bullet 2.png'
                cache_key = 'plant_bullet_2'
            try:
                return resource_manager.load_image(cache_key, image_path)
            except Exception:
                pass
        
        # 对于 fly/skt/slime 等使用绘制圆形
        surface = pygame.Surface((16, 16), pygame.SRCALPHA)
        
        if self.enemy_type == 'fly':
            color = (50, 150, 255)
            tail_color = (150, 220, 255)
            radius = 8
        elif self.enemy_type == 'skt':
            color = (128, 0, 128)
            tail_color = (200, 100, 200)
            radius = 8
        elif self.enemy_type == 'slime':
            color = (255, 0, 0)
            tail_color = (255, 200, 200)
            radius = 8
        else:
            color = (200, 200, 200)
            tail_color = (255, 255, 255)
            radius = 8
        
        pygame.draw.circle(surface, color, (8, 8), radius)
        pygame.draw.circle(surface, tail_color, (8, 8), radius // 2)
        
        end_x = 8 - int(self.direction_x * 6)
        end_y = 8 - int(self.direction_y * 6)
        pygame.draw.line(surface, tail_color, (8, 8), (end_x, end_y), 2)
        
        return surface
    
    def update(self, dt):
        """更新位置"""
        self.x += self.direction_x * self.speed * dt
        self.y += self.direction_y * self.speed * dt
        self.rect.center = (int(self.x), int(self.y))
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
    
    def render(self, screen, camera_x, camera_y):
        """渲染投射物"""
        screen_x = self.x - camera_x + screen.get_width() // 2
        screen_y = self.y - camera_y + screen.get_height() // 2
        screen.blit(self.image, (screen_x - self.image.get_width() // 2,
                                 screen_y - self.image.get_height() // 2))
