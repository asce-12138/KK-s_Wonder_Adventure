from ..enemy import Enemy
from ...resource_manager import resource_manager
import pygame

class Skeleton(Enemy):
    def __init__(self, x, y, enemy_type='skeleton', difficulty="normal", level=1, scale=None):
        super().__init__(x, y, enemy_type, difficulty, level, scale)
        
        self.load_animations()
        
        self.current_animation = 'idle'
        self.image = self.animations[self.current_animation].get_current_frame()
        original_size = self.image.get_size()
        new_size = (int(original_size[0] * self.scale), int(original_size[1] * self.scale))
        self.image = pygame.transform.scale(self.image, new_size)
        
        self.original_image = self.image.copy()
        
    def load_animations(self):
        idle_spritesheet = resource_manager.load_spritesheet(
            'skeleton_idle_spritesheet', 'images/enemy/skeleton_idle_32x40.png')
        
        self.animations = {
            'idle': resource_manager.create_animation(
                'skeleton_idle', idle_spritesheet,
                frame_width=32, frame_height=40,
                frame_count=1, row=0,
                frame_duration=1.0
            ),
            'walk': resource_manager.create_animation(
                'skeleton_walk', idle_spritesheet,
                frame_width=32, frame_height=40,
                frame_count=1, row=0,
                frame_duration=1.0
            ),
            'hurt': resource_manager.create_animation(
                'skeleton_hurt', idle_spritesheet,
                frame_width=32, frame_height=40,
                frame_count=1, row=0,
                frame_duration=1.0
            )
        }
    
    def update(self, dt, player):
        self.update_status_effects(dt)
        
        if self.invincible:
            self.invincible_timer -= dt
            if self.invincible_timer <= 0:
                self.invincible = False
                self.invincible_timer = 0
        
        dx = player.world_x - self.rect.x
        dy = player.world_y - self.rect.y
        distance = pygame.math.Vector2(dx, dy).length()
        
        self.facing_right = dx > 0
        
        if distance != 0:
            dx = dx / distance
            dy = dy / distance
            
            self.rect.x += dx * self.speed * dt
            self.rect.y += dy * self.speed * dt
        
        self.update_image()
    
    def update_image(self):
        modified_frame = self.original_image.copy()
        
        mask = pygame.mask.from_surface(self.original_image)
        mask_outline = mask.outline()
        
        if 'slow' in self.status_effects:
            slow_effect = pygame.Surface(modified_frame.get_size(), pygame.SRCALPHA)
            if mask_outline:
                for point in mask_outline:
                    pygame.draw.circle(slow_effect, (0, 0, 200, 100), point, 3)
            mask_surface = mask.to_surface(setcolor=(0, 0, 100, 70), unsetcolor=(0, 0, 0, 0))
            slow_effect.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            modified_frame.blit(slow_effect, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        
        if self.burn_flash_timer > 0:
            fire_effect = pygame.Surface(modified_frame.get_size(), pygame.SRCALPHA)
            if mask_outline:
                for point in mask_outline:
                    pygame.draw.circle(fire_effect, (255, 100, 0, 150), point, 3)
            mask_surface = mask.to_surface(setcolor=(50, 0, 0, 50), unsetcolor=(0, 0, 0, 0))
            fire_effect.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            modified_frame.blit(fire_effect, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        
        if not self.facing_right:
            modified_frame = pygame.transform.flip(modified_frame, True, False)
        
        self.image = modified_frame
        self.mask = pygame.mask.from_surface(self.image)