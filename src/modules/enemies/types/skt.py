from ..enemy import Enemy
from ...resource_manager import resource_manager
import pygame
import math


class Skt(Enemy):
    """双形态敌人：idle1形态远程攻击，idle2形态近战攻击"""

    def __init__(self, x, y, enemy_type='skt', difficulty="normal", level=1, scale=None):
        super().__init__(x, y, enemy_type, difficulty, level, scale)

        self.attack_range = self.config.get("attack_range", 600)
        self.min_attack_range = self.config.get("min_attack_range", 200)
        self.attack_cooldown = 0
        self.attack_cooldown_time = self.config.get("attack_cooldown", 2.0)
        self.projectile_speed = self.config.get("projectile_speed", 200)
        self.projectiles = pygame.sprite.Group()

        self.current_form = 1
        self.form_switch_timer = 0
        self.form_switch_interval = self.config.get("form_switch_interval", 5.0)

        self.load_animations()

        self.current_animation = 'idle1'
        self.image = self.animations[self.current_animation].get_current_frame()
        original_size = self.image.get_size()
        new_size = (int(original_size[0] * self.scale), int(original_size[1] * self.scale))
        self.image = pygame.transform.scale(self.image, new_size)

    def load_animations(self):
        animation_speed = self.config.get("animation_speed", 0.0333)

        idle1_spritesheet = resource_manager.load_spritesheet(
            'skt_idle1_spritesheet', 'images/enemy/skt_idle_1(52x54).png')
        idle2_spritesheet = resource_manager.load_spritesheet(
            'skt_idle2_spritesheet', 'images/enemy/skt_idle_2 (52x54).png')
        hit_spritesheet = resource_manager.load_spritesheet(
            'skt_hit_spritesheet', 'images/enemy/skt_hit (52x54).png')

        self.animations = {
            'idle1': resource_manager.create_animation(
                'skt_idle1', idle1_spritesheet,
                frame_width=52, frame_height=54,
                frame_count=8, row=0,
                frame_duration=animation_speed
            ),
            'idle2': resource_manager.create_animation(
                'skt_idle2', idle2_spritesheet,
                frame_width=52, frame_height=54,
                frame_count=8, row=0,
                frame_duration=animation_speed
            ),
            'hurt': resource_manager.create_animation(
                'skt_hurt', hit_spritesheet,
                frame_width=52, frame_height=54,
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
                self.current_animation = 'idle1' if self.current_form == 1 else 'idle2'
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
                current_idle = 'idle1' if self.current_form == 1 else 'idle2'
                if self.current_animation != current_idle:
                    self.current_animation = current_idle
                    if self.current_animation in self.animations:
                        self.animations[self.current_animation].reset()

        elif self.hurt_timer <= 0:
            current_idle = 'idle1' if self.current_form == 1 else 'idle2'
            if self.current_animation != current_idle:
                self.current_animation = current_idle
                if self.current_animation in self.animations:
                    self.animations[self.current_animation].reset()

        self.update_image()

        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

        self.projectiles.update(dt)

        self.form_switch_timer += dt
        if self.form_switch_timer >= self.form_switch_interval:
            self.form_switch_timer = 0
            self.switch_form()

    def switch_form(self):
        self.current_form = 2 if self.current_form == 1 else 1
        self.current_animation = 'idle1' if self.current_form == 1 else 'idle2'
        if self.current_animation in self.animations:
            self.animations[self.current_animation].reset()
        self.attack_cooldown = 0

    def render(self, screen, screen_x, screen_y):
        super().render(screen, screen_x, screen_y)

        for projectile in self.projectiles:
            projectile_offset_x = projectile.x - self.rect.centerx
            projectile_offset_y = projectile.y - self.rect.centery
            projectile_screen_x = screen_x + projectile_offset_x
            projectile_screen_y = screen_y + projectile_offset_y
            screen.blit(projectile.image,
                      (projectile_screen_x - projectile.image.get_width() // 2,
                       projectile_screen_y - projectile.image.get_height() // 2))

    def attack(self, player, dt):
        hit = False
        for projectile in list(self.projectiles):
            if self._check_projectile_hit(projectile, player):
                projectile.kill()
                hit = True

        if self.current_form == 1:
            if self.attack_cooldown <= 0:
                dx = player.world_x - self.rect.centerx
                dy = player.world_y - self.rect.centery
                distance = math.sqrt(dx * dx + dy * dy)

                if self.min_attack_range < distance < self.attack_range:
                    if distance > 0:
                        direction_x = dx / distance
                        direction_y = dy / distance
                        self._fire_projectile(direction_x, direction_y)
                        self.attack_cooldown = self.attack_cooldown_time

        return hit

    def _fire_projectile(self, direction_x, direction_y):
        projectile = SktProjectile(
            self.rect.centerx,
            self.rect.centery,
            direction_x,
            direction_y,
            self.damage,
            self.projectile_speed
        )
        self.projectiles.add(projectile)

    def _check_projectile_hit(self, projectile, player):
        dx = projectile.x - player.world_x
        dy = projectile.y - player.world_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < player.rect.width / 2 + projectile.radius:
            player.take_damage(projectile.damage)
            return True

        return False


class SktProjectile(pygame.sprite.Sprite):
    """Skt敌人的投射物类"""

    def __init__(self, x, y, direction_x, direction_y, damage, speed):
        super().__init__()
        self.x = x
        self.y = y
        self.direction_x = direction_x
        self.direction_y = direction_y
        self.damage = damage
        self.speed = speed
        self.radius = 10
        self.lifetime = 4.0

        self.image = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (128, 0, 128), (10, 10), 10)
        end_x = 10 - int(direction_x * 8)
        end_y = 10 - int(direction_y * 8)
        pygame.draw.line(self.image, (200, 100, 200), (10, 10), (end_x, end_y), 3)

        self.rect = self.image.get_rect(center=(x, y))

    def update(self, dt):
        self.x += self.direction_x * self.speed * dt
        self.y += self.direction_y * self.speed * dt
        self.rect.center = (self.x, self.y)
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
