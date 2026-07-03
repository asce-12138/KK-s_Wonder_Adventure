from ..enemy import Enemy
from ...resource_manager import resource_manager
import pygame
import math


class PlantProjectile(pygame.sprite.Sprite):
    """Plant的投射物类"""
    
    def __init__(self, x, y, direction_x, direction_y, damage, speed, bullet_type=1):
        super().__init__()
        self.x = x
        self.y = y
        self.start_x = x
        self.start_y = y
        self.direction_x = direction_x
        self.direction_y = direction_y
        self.damage = damage
        self.speed = speed
        self.radius = 8
        self.lifetime = 5.0
        self.max_distance = 300
        
        if bullet_type == 1:
            image_path = 'images/enemy/plant_Bullet1.png'
        else:
            image_path = 'images/enemy/plant_Bullet 2.png'
        
        self.image = resource_manager.load_image(f'plant_bullet_{bullet_type}', image_path)
        self.rect = self.image.get_rect(center=(x, y))
        
    def update(self, dt):
        self.x += self.direction_x * self.speed * dt
        self.y += self.direction_y * self.speed * dt
        self.rect.center = (self.x, self.y)
        self.lifetime -= dt
        
        distance = math.sqrt((self.x - self.start_x) ** 2 + (self.y - self.start_y) ** 2)
        if self.lifetime <= 0 or distance >= self.max_distance:
            self.kill()


class Plant(Enemy):
    """固定炮台敌人：不移动，根据玩家距离发射不同模式的弹幕"""

    def __init__(self, x, y, enemy_type='plant', difficulty="normal", level=1, scale=None):
        super().__init__(x, y, enemy_type, difficulty, level, scale)

        self.attack_cooldown = 0
        self.attack_cooldown_time = self.config.get("attack_cooldown", 1.5)
        self.attack_cooldown_near = self.config.get("attack_cooldown_near", 0.8)
        
        self.near_range = self.config.get("near_range", 250)
        
        self.bullet_speed = self.config.get("bullet_speed", 200)
        self.bullet_damage = self.config.get("bullet_damage", 20)
        
        self.projectiles = pygame.sprite.Group()
        
        self.load_animations()

        self.current_animation = 'idle'
        self.image = self.animations[self.current_animation].get_current_frame()
        original_size = self.image.get_size()
        new_size = (int(original_size[0] * self.scale), int(original_size[1] * self.scale))
        self.image = pygame.transform.scale(self.image, new_size)

    def load_animations(self):
        animation_speed = self.config.get("animation_speed", 0.0333)

        idle_spritesheet = resource_manager.load_spritesheet(
            'plant_idle_spritesheet', 'images/enemy/plant_idle.png')
        hit_spritesheet = resource_manager.load_spritesheet(
            'plant_hit_spritesheet', 'images/enemy/plant_hit (44x42).png')

        self.animations = {
            'idle': resource_manager.create_animation(
                'plant_idle', idle_spritesheet,
                frame_width=44, frame_height=42,
                frame_count=11, row=0,
                frame_duration=animation_speed
            ),
            'hurt': resource_manager.create_animation(
                'plant_hurt', hit_spritesheet,
                frame_width=44, frame_height=42,
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

        self.attack_cooldown -= dt
        
        self.facing_right = player.world_x > self.rect.x

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

            if distance < self.near_range:
                self._fire_near_pattern()
                self.attack_cooldown = self.attack_cooldown_near
            else:
                self._fire_far_pattern()
                self.attack_cooldown = self.attack_cooldown_time

        return hit

    def _fire_far_pattern(self):
        for i in range(8):
            angle = math.radians(i * 45)
            direction_x = math.cos(angle)
            direction_y = math.sin(angle)
            self._fire_projectile(direction_x, direction_y, bullet_type=1)

    def _fire_near_pattern(self):
        for i in range(16):
            angle = math.radians(i * 22.5)
            direction_x = math.cos(angle)
            direction_y = math.sin(angle)
            self._fire_projectile(direction_x, direction_y, bullet_type=2)

    def _fire_projectile(self, direction_x, direction_y, bullet_type=1):
        projectile = PlantProjectile(
            self.rect.centerx,
            self.rect.centery,
            direction_x,
            direction_y,
            self.bullet_damage,
            self.bullet_speed,
            bullet_type
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

    def render(self, screen, screen_x, screen_y):
        super().render(screen, screen_x, screen_y)
        
        for projectile in self.projectiles:
            projectile_offset_x = projectile.x - self.rect.centerx
            projectile_offset_y = projectile.y - self.rect.centery
            proj_screen_x = screen_x + projectile_offset_x
            proj_screen_y = screen_y + projectile_offset_y
            screen.blit(projectile.image, (proj_screen_x - projectile.image.get_width() // 2,
                                           proj_screen_y - projectile.image.get_height() // 2))
