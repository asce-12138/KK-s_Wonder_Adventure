from ..enemy import Enemy
from ...resource_manager import resource_manager
import pygame
import math


class FlyProjectile(pygame.sprite.Sprite):
    """Fly的投射物类，蓝色子弹，击中玩家后减速"""
    
    def __init__(self, x, y, direction_x, direction_y, damage, speed):
        super().__init__()
        self.x = x
        self.y = y
        self.direction_x = direction_x
        self.direction_y = direction_y
        self.damage = damage
        self.speed = speed
        self.radius = 8
        self.lifetime = 5.0
        
        self.image = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (50, 150, 255), (8, 8), 8)
        pygame.draw.circle(self.image, (100, 200, 255), (8, 8), 4)
        
        end_x = 8 - int(direction_x * 8)
        end_y = 8 - int(direction_y * 8)
        pygame.draw.line(self.image, (150, 220, 255), (8, 8), (end_x, end_y), 2)
        
        self.rect = self.image.get_rect(center=(x, y))
        
    def update(self, dt):
        self.x += self.direction_x * self.speed * dt
        self.y += self.direction_y * self.speed * dt
        self.rect.center = (self.x, self.y)
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()


class Fly(Enemy):
    """飞行敌人：有碰撞伤害，发射蓝色子弹减速玩家"""

    def __init__(self, x, y, enemy_type='fly', difficulty="normal", level=1, scale=None):
        super().__init__(x, y, enemy_type, difficulty, level, scale)

        self.attack_cooldown = 0
        self.attack_cooldown_time = self.config.get("attack_cooldown", 2.0)
        self.attack_range = self.config.get("attack_range", 500)
        self.min_attack_range = self.config.get("min_attack_range", 150)
        self.bullet_speed = self.config.get("bullet_speed", 220)
        self.bullet_damage = self.config.get("bullet_damage", 25)
        self.slow_percent = self.config.get("slow_percent", 0.4)
        self.slow_duration = self.config.get("slow_duration", 3.0)
        
        self.projectiles = pygame.sprite.Group()
        
        self.load_animations()

        self.current_animation = 'idle'
        self.image = self.animations[self.current_animation].get_current_frame()
        original_size = self.image.get_size()
        new_size = (int(original_size[0] * self.scale), int(original_size[1] * self.scale))
        self.image = pygame.transform.scale(self.image, new_size)

    def load_animations(self):
        animation_speed = self.config.get("animation_speed", 0.0333)

        spritesheet = resource_manager.load_spritesheet(
            'fly_spritesheet', 'images/enemy/fly.png')

        self.animations = {
            'idle': resource_manager.create_animation(
                'fly_idle', spritesheet,
                frame_width=128, frame_height=66,
                frame_count=5, row=0,
                frame_duration=animation_speed
            ),
            'walk': resource_manager.create_animation(
                'fly_walk', spritesheet,
                frame_width=128, frame_height=66,
                frame_count=5, row=1,
                frame_duration=animation_speed * 0.8
            ),
            'hurt': resource_manager.create_animation(
                'fly_hurt', spritesheet,
                frame_width=128, frame_height=66,
                frame_count=5, row=2,
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
                self.current_animation = 'walk'
                if self.current_animation in self.animations:
                    self.animations[self.current_animation].reset()

        self.attack_cooldown -= dt
        
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
                if self.current_animation != 'walk':
                    self.current_animation = 'walk'
                    if self.current_animation in self.animations:
                        self.animations[self.current_animation].reset()

        elif self.hurt_timer <= 0:
            if self.current_animation != 'idle':
                self.current_animation = 'idle'
                if self.current_animation in self.animations:
                    self.animations[self.current_animation].reset()

        self.projectiles.update(dt)

        self.update_image()

    def attack(self, player, dt):
        hit = False
        
        for projectile in list(self.projectiles):
            if self._check_projectile_hit(projectile, player):
                projectile.kill()
                hit = True

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
        projectile = FlyProjectile(
            self.rect.centerx,
            self.rect.centery,
            direction_x,
            direction_y,
            self.bullet_damage,
            self.bullet_speed
        )
        self.projectiles.add(projectile)

    def _check_projectile_hit(self, projectile, player):
        dx = projectile.x - player.world_x
        dy = projectile.y - player.world_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < player.rect.width / 2 + projectile.radius:
            player.take_damage(projectile.damage)
            
            if hasattr(player, 'movement'):
                # 使用倍率叠加，避免覆盖加速升级
                # 实际速度 = base_speed × speed_multiplier
                new_multiplier = 1.0 - self.slow_percent
                player.movement.set_speed_multiplier(new_multiplier)

                if not hasattr(player, 'slow_timer'):
                    player.slow_timer = 0
                player.slow_timer = self.slow_duration
            
            return True

        return False

    def render(self, screen, screen_x, screen_y):
        draw_rect = self.rect.copy()
        draw_rect.x = screen_x
        draw_rect.y = screen_y

        if hasattr(self, 'image'):
            if self.show_outline:
                from ...utils import create_outlined_sprite
                outlined_image = create_outlined_sprite(
                    self,
                    outline_color=self.outline_color,
                    outline_thickness=self.outline_thickness
                )
                screen.blit(outlined_image, draw_rect)
            else:
                screen.blit(self.image, draw_rect)

        health_bar_width = 32
        health_bar_height = 5
        health_ratio = self.health / self.max_health

        bar_x = screen_x + (self.image.get_width() - health_bar_width) / 2
        bar_y = screen_y - 10

        pygame.draw.rect(screen, (255, 0, 0),
                        (bar_x, bar_y,
                         health_bar_width, health_bar_height))
        pygame.draw.rect(screen, (0, 255, 0),
                        (bar_x, bar_y,
                         health_bar_width * health_ratio, health_bar_height))
        
        for projectile in self.projectiles:
            projectile_offset_x = projectile.x - self.rect.centerx
            projectile_offset_y = projectile.y - self.rect.centery
            proj_screen_x = screen_x + projectile_offset_x
            proj_screen_y = screen_y + projectile_offset_y
            screen.blit(projectile.image, (proj_screen_x - projectile.image.get_width() // 2,
                                           proj_screen_y - projectile.image.get_height() // 2))
