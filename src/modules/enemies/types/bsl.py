from ..enemy import Enemy
from ...resource_manager import resource_manager
from ...utils import create_outlined_sprite
import pygame
import math


class Bsl(Enemy):
    """隐身敌人：远离玩家时透明，靠近才出现，只有碰撞伤害"""

    def __init__(self, x, y, enemy_type='bsl', difficulty="normal", level=1, scale=None):
        super().__init__(x, y, enemy_type, difficulty, level, scale)

        self.visibility_range = self.config.get("visibility_range", 300)
        self.visibility_fade_range = self.config.get("visibility_fade_range", 100)
        self.current_alpha = 255

        self.load_animations()

        self.current_animation = 'idle'
        self.image = self.animations[self.current_animation].get_current_frame()
        original_size = self.image.get_size()
        new_size = (int(original_size[0] * self.scale), int(original_size[1] * self.scale))
        self.image = pygame.transform.scale(self.image, new_size)

    def load_animations(self):
        animation_speed = self.config.get("animation_speed", 0.0333)

        idle_spritesheet = resource_manager.load_spritesheet(
            'bsl_idle_spritesheet', 'images/enemy/bsl_Idle (84x38).png')
        attack_spritesheet = resource_manager.load_spritesheet(
            'bsl_attack_spritesheet', 'images/enemy/bsl_Attack (84x38).png')
        hit_spritesheet = resource_manager.load_spritesheet(
            'bsl_hit_spritesheet', 'images/enemy/bsl_Hit (84x38).png')

        self.animations = {
            'idle': resource_manager.create_animation(
                'bsl_idle', idle_spritesheet,
                frame_width=84, frame_height=38,
                frame_count=13, row=0,
                frame_duration=animation_speed
            ),
            'attack': resource_manager.create_animation(
                'bsl_attack', attack_spritesheet,
                frame_width=84, frame_height=38,
                frame_count=10, row=0,
                frame_duration=animation_speed
            ),
            'hurt': resource_manager.create_animation(
                'bsl_hurt', hit_spritesheet,
                frame_width=84, frame_height=38,
                frame_count=5, row=0,
                frame_duration=animation_speed
            )
        }

    def update(self, dt, player):
        self.update_status_effects(dt)

        if self.invincible:
            self.invincible_timer -= dt
            if self.invincible_timer <= 0:
                self.invincible = False
                self.invincible_timer = 0

        if self.current_animation in self.animations:
            self.animations[self.current_animation].update(dt)

        if self.hurt_timer > 0:
            self.hurt_timer -= dt
            if self.hurt_timer <= 0:
                self.current_animation = 'idle'
                if self.current_animation in self.animations:
                    self.animations[self.current_animation].reset()

        dx = player.world_x - self.rect.x
        dy = player.world_y - self.rect.y
        distance = math.sqrt(dx * dx + dy * dy)

        self.facing_right = dx > 0

        if distance != 0:
            dx = dx / distance
            dy = dy / distance

            self.rect.x += dx * self.speed * dt
            self.rect.y += dy * self.speed * dt

            if self.hurt_timer <= 0:
                if distance < self.visibility_range * 0.5:
                    if self.current_animation != 'attack':
                        self.current_animation = 'attack'
                        if self.current_animation in self.animations:
                            self.animations[self.current_animation].reset()
                else:
                    if self.current_animation != 'idle':
                        self.current_animation = 'idle'
                        if self.current_animation in self.animations:
                            self.animations[self.current_animation].reset()

        elif self.hurt_timer <= 0:
            if self.current_animation != 'idle':
                self.current_animation = 'idle'
                if self.current_animation in self.animations:
                    self.animations[self.current_animation].reset()

        self.update_image(player)

    def update_image(self, player=None):
        if self.current_animation in self.animations:
            current_frame = self.animations[self.current_animation].get_current_frame()

            original_size = current_frame.get_size()
            new_size = (int(original_size[0] * self.scale), int(original_size[1] * self.scale))
            current_frame = pygame.transform.scale(current_frame, new_size)

            current_frame = pygame.transform.flip(current_frame, True, False)

            if not self.facing_right:
                current_frame = pygame.transform.flip(current_frame, True, False)

            modified_frame = current_frame.copy()

            if player:
                dx = player.world_x - self.rect.centerx
                dy = player.world_y - self.rect.centery
                distance = math.sqrt(dx * dx + dy * dy)

                if distance > self.visibility_range + self.visibility_fade_range:
                    alpha = 0
                elif distance < self.visibility_range:
                    alpha = 255
                else:
                    fade_distance = distance - self.visibility_range
                    fade_ratio = fade_distance / self.visibility_fade_range
                    alpha = int(255 * (1 - fade_ratio))

                self.current_alpha = alpha
                modified_frame.set_alpha(alpha)

            mask = pygame.mask.from_surface(current_frame)
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

            self.image = modified_frame

    def attack(self, player, dt):
        return False

    def render(self, screen, screen_x, screen_y):
        draw_rect = self.rect.copy()
        draw_rect.x = screen_x
        draw_rect.y = screen_y

        if hasattr(self, 'image'):
            if self.show_outline:
                outlined_image = create_outlined_sprite(
                    self,
                    outline_color=self.outline_color,
                    outline_thickness=self.outline_thickness
                )
                screen.blit(outlined_image, draw_rect)
            else:
                screen.blit(self.image, draw_rect)

        if self.current_alpha > 0:
            health_bar_width = 32 * self.scale
            health_bar_height = 5 * self.scale
            health_ratio = self.health / self.max_health

            bar_x = screen_x + (self.rect.width - health_bar_width) / 2
            bar_y = screen_y - 10 * self.scale

            pygame.draw.rect(screen, (255, 0, 0),
                            (bar_x, bar_y,
                             health_bar_width, health_bar_height))
            pygame.draw.rect(screen, (0, 255, 0),
                            (bar_x, bar_y,
                             health_bar_width * health_ratio, health_bar_height))
