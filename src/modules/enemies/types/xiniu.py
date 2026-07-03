from ..enemy import Enemy
from ...resource_manager import resource_manager
import pygame
import math


class Xiniu(Enemy):
    """疾跑敌人：靠近玩家时加速并切换到奔跑动画"""

    def __init__(self, x, y, enemy_type='xiniu', difficulty="normal", level=1, scale=None):
        super().__init__(x, y, enemy_type, difficulty, level, scale)

        self.charge_range = self.config.get("charge_range", 200)
        self.charge_speed_multiplier = self.config.get("charge_speed_multiplier", 1.8)

        self.load_animations()

        self.current_animation = 'idle'
        self.image = self.animations[self.current_animation].get_current_frame()
        original_size = self.image.get_size()
        new_size = (int(original_size[0] * self.scale), int(original_size[1] * self.scale))
        self.image = pygame.transform.scale(self.image, new_size)

    def load_animations(self):
        animation_speed = self.config.get("animation_speed", 0.0333)

        idle_spritesheet = resource_manager.load_spritesheet(
            'xiniu_idle_spritesheet', 'images/enemy/xiniu_idle(52x34).png')
        run_spritesheet = resource_manager.load_spritesheet(
            'xiniu_run_spritesheet', 'images/enemy/xiniu_run (52x34).png')
        hit_spritesheet = resource_manager.load_spritesheet(
            'xiniu_hit_spritesheet', 'images/enemy/xiniu_hit (52x34).png')

        self.animations = {
            'idle': resource_manager.create_animation(
                'xiniu_idle', idle_spritesheet,
                frame_width=52, frame_height=34,
                frame_count=11, row=0,
                frame_duration=animation_speed
            ),
            'run': resource_manager.create_animation(
                'xiniu_run', run_spritesheet,
                frame_width=52, frame_height=34,
                frame_count=6, row=0,
                frame_duration=animation_speed * 0.7
            ),
            'hurt': resource_manager.create_animation(
                'xiniu_hurt', hit_spritesheet,
                frame_width=52, frame_height=34,
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

            is_charging = distance < self.charge_range

            current_speed = self.speed * self.charge_speed_multiplier if is_charging else self.speed

            self.rect.x += dx * current_speed * dt
            self.rect.y += dy * current_speed * dt

            if self.hurt_timer <= 0:
                if is_charging:
                    if self.current_animation != 'run':
                        self.current_animation = 'run'
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

        self.update_image()

    def attack(self, player, dt):
        return False

    def render(self, screen, screen_x, screen_y):
        super().render(screen, screen_x, screen_y)
