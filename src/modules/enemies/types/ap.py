from ..enemy import Enemy
from ...resource_manager import resource_manager
import pygame
import math


class Ap(Enemy):
    """愤怒敌人：生命值低于50%时切换为愤怒形态，大幅提升伤害和速度"""

    def __init__(self, x, y, enemy_type='ap', difficulty="normal", level=1, scale=None):
        super().__init__(x, y, enemy_type, difficulty, level, scale)

        self.is_enraged = False
        self.enrage_threshold = 0.5
        self.enrage_damage_multiplier = self.config.get("enrage_damage_multiplier", 2.0)
        self.enrage_speed_multiplier = self.config.get("enrage_speed_multiplier", 1.5)

        self.load_animations()

        self.current_animation = 'idle'
        self.image = self.animations[self.current_animation].get_current_frame()
        original_size = self.image.get_size()
        new_size = (int(original_size[0] * self.scale), int(original_size[1] * self.scale))
        self.image = pygame.transform.scale(self.image, new_size)

    def load_animations(self):
        animation_speed = self.config.get("animation_speed", 0.0333)

        green_spritesheet = resource_manager.load_spritesheet(
            'ap_green_spritesheet', 'images/enemy/ap_green (36x30).png')
        red_spritesheet = resource_manager.load_spritesheet(
            'ap_red_spritesheet', 'images/enemy/ap_red (36x30).png')

        self.animations = {
            'idle': resource_manager.create_animation(
                'ap_idle', green_spritesheet,
                frame_width=36, frame_height=30,
                frame_count=9, row=0,
                frame_duration=animation_speed
            ),
            'enraged': resource_manager.create_animation(
                'ap_enraged', red_spritesheet,
                frame_width=36, frame_height=30,
                frame_count=12, row=0,
                frame_duration=animation_speed * 0.7
            ),
            'hurt': resource_manager.create_animation(
                'ap_hurt', green_spritesheet,
                frame_width=36, frame_height=30,
                frame_count=9, row=0,
                frame_duration=animation_speed
            )
        }

    def check_enrage(self):
        health_ratio = self.health / self.max_health
        if health_ratio <= self.enrage_threshold and not self.is_enraged:
            self.is_enraged = True
            self.damage = self.damage * self.enrage_damage_multiplier
            self.speed = self.speed * self.enrage_speed_multiplier
            self.current_animation = 'enraged'
            if self.current_animation in self.animations:
                self.animations[self.current_animation].reset()

    def update(self, dt, player):
        self.update_status_effects(dt)

        self.check_enrage()

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
                self.current_animation = 'enraged' if self.is_enraged else 'idle'
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
                current_anim = 'enraged' if self.is_enraged else 'idle'
                if self.current_animation != current_anim:
                    self.current_animation = current_anim
                    if self.current_animation in self.animations:
                        self.animations[self.current_animation].reset()

        elif self.hurt_timer <= 0:
            current_anim = 'enraged' if self.is_enraged else 'idle'
            if self.current_animation != current_anim:
                self.current_animation = current_anim
                if self.current_animation in self.animations:
                    self.animations[self.current_animation].reset()

        self.update_image()

    def attack(self, player, dt):
        return False

    def render(self, screen, screen_x, screen_y):
        super().render(screen, screen_x, screen_y)
