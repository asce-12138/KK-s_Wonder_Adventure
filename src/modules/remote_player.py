import pygame
import math
from .resource_manager import resource_manager
from .hero_config import get_hero_config
from .utils import FontManager


class RemotePlayer:
    """
    远程联机玩家类
    只负责接收网络同步数据并渲染，不处理输入、碰撞、武器等逻辑
    """
    
    def __init__(self, hero_type="ninja_frog"):
        self.hero_type = hero_type
        self.hero_config = get_hero_config(hero_type)
        
        # 世界坐标（从网络同步）
        self.world_x = 0
        self.world_y = 0
        
        # 状态（从网络同步）
        self.health = 100
        self.max_health = 100
        self.is_moving = False
        self.facing_right = True
        self.is_hurt = False
        
        # 动画相关
        self.current_animation = 'idle'
        self.animations = {}
        self.animation_time = 0
        self.current_frame_index = 0
        self.image = None
        self.rect = None
        
        # 玩家名称标签
        self.font = FontManager.get_font(16)
        self.player_name = "玩家2"
        self.name_color = (0, 255, 255)
        
        # 缩放因子
        self.scale_factor = self.hero_config.get("scale_factor", 1.0)
        
        # 初始化动画
        self._init_animations()
        
        # 设置初始图像
        self._update_image()
    
    def _init_animations(self):
        """初始化动画帧"""
        hero_scale = self.hero_config.get("scale_factor", 1.0)
        
        for anim_name, anim_info in self.hero_config.get("animations", {}).items():
            sprite_sheet = resource_manager.load_spritesheet(
                f"remote_{self.hero_type}_{anim_name}_sprite",
                anim_info['sprite_sheet']
            )
            
            frame_width = anim_info.get('frame_width', 32)
            frame_height = anim_info.get('frame_height', 32)
            frame_count = anim_info.get('frame_count', 1)
            frame_duration = anim_info.get('frame_duration', 0.1)
            
            anim_scale = anim_info.get('scale_factor', hero_scale)
            
            frames = []
            for i in range(frame_count):
                x = i * frame_width
                frame_surface = sprite_sheet.get_sprite(x, 0, frame_width, frame_height)
                
                if anim_scale != 1.0:
                    new_w = int(frame_width * anim_scale)
                    new_h = int(frame_height * anim_scale)
                    frame_surface = pygame.transform.scale(frame_surface, (new_w, new_h))
                
                frames.append({
                    'surface': frame_surface,
                    'duration': frame_duration
                })
            
            self.animations[anim_name] = frames
    
    def update_from_network(self, data):
        """
        从网络数据更新远程玩家状态
        
        Args:
            data: 网络同步的玩家数据字典
        """
        self.world_x = data.get('world_x', self.world_x)
        self.world_y = data.get('world_y', self.world_y)
        self.health = data.get('health', self.health)
        self.max_health = data.get('max_health', self.max_health)
        self.is_moving = data.get('is_moving', False)
        self.facing_right = data.get('facing_right', True)
        self.is_hurt = data.get('is_hurt', False)
        
        # 如果英雄类型变化，重新初始化动画
        new_hero_type = data.get('hero_type', self.hero_type)
        if new_hero_type != self.hero_type:
            self.hero_type = new_hero_type
            self.hero_config = get_hero_config(new_hero_type)
            self._init_animations()
            self.current_animation = 'idle'
            self.current_frame_index = 0
            self.animation_time = 0
    
    def update(self, dt):
        """
        更新动画状态
        
        Args:
            dt: 时间增量（秒）
        """
        # 确定当前应该播放的动画
        if self.is_hurt:
            target_anim = 'hurt'
        elif self.is_moving:
            target_anim = 'run'
        else:
            target_anim = 'idle'
        
        # 如果动画状态改变，重置动画
        if target_anim != self.current_animation:
            self.current_animation = target_anim
            self.animation_time = 0
            self.current_frame_index = 0
        
        # 更新动画帧
        anim_frames = self.animations.get(self.current_animation)
        if anim_frames and len(anim_frames) > 0:
            # 防止帧索引越界
            if self.current_frame_index >= len(anim_frames):
                self.current_frame_index = 0
            
            self.animation_time += dt
            current_frame = anim_frames[self.current_frame_index]
            
            while self.animation_time >= current_frame['duration']:
                self.animation_time -= current_frame['duration']
                self.current_frame_index = (self.current_frame_index + 1) % len(anim_frames)
                current_frame = anim_frames[self.current_frame_index]
            
            self._update_image()
    
    def _update_image(self):
        """更新当前显示的图像"""
        anim_frames = self.animations.get(self.current_animation)
        if anim_frames and len(anim_frames) > 0:
            frame_index = self.current_frame_index % len(anim_frames)
            frame = anim_frames[frame_index]
            self.image = frame['surface'].copy()
            
            # 根据朝向翻转图像
            if not self.facing_right:
                self.image = pygame.transform.flip(self.image, True, False)
            
            if self.rect is None:
                self.rect = self.image.get_rect()
            else:
                old_center = self.rect.center
                self.rect = self.image.get_rect()
                self.rect.center = old_center
    
    def render(self, screen, camera_x, camera_y, screen_center_x, screen_center_y):
        """
        渲染远程玩家（考虑相机偏移）
        
        Args:
            screen: 目标Surface
            camera_x: 相机X坐标
            camera_y: 相机Y坐标
            screen_center_x: 屏幕中心X
            screen_center_y: 屏幕中心Y
        """
        if self.image is None:
            return
        
        # 计算相对于本地玩家屏幕位置的渲染位置
        # 远程玩家的世界坐标与本地玩家世界坐标的差值，加上本地玩家在屏幕上的中心位置
        local_screen_x = screen_center_x
        local_screen_y = screen_center_y
        
        dx = self.world_x - camera_x
        dy = self.world_y - camera_y
        
        screen_x = local_screen_x + dx
        screen_y = local_screen_y + dy
        
        # 更新矩形位置
        if self.rect:
            self.rect.center = (screen_x, screen_y)
            
            # 绘制玩家精灵
            screen.blit(self.image, self.rect)
            
            # 绘制玩家名称
            name_text = self.font.render(self.player_name, True, self.name_color)
            name_rect = name_text.get_rect()
            name_rect.midbottom = (screen_x, self.rect.top - 5)
            
            # 绘制名称阴影
            shadow_text = self.font.render(self.player_name, True, (0, 0, 0))
            shadow_rect = shadow_text.get_rect()
            shadow_rect.midbottom = (screen_x + 1, self.rect.top - 4)
            screen.blit(shadow_text, shadow_rect)
            screen.blit(name_text, name_rect)
            
            # 绘制血条
            self._render_health_bar(screen, screen_x, screen_y)
    
    def _render_health_bar(self, screen, screen_x, screen_y):
        """
        渲染远程玩家的血条
        
        Args:
            screen: 目标Surface
            screen_x: 玩家在屏幕上的X中心
            screen_y: 玩家在屏幕上的Y中心
        """
        if self.max_health <= 0:
            return
        
        bar_width = 40
        bar_height = 5
        bar_y_offset = 35
        
        bar_x = screen_x - bar_width // 2
        bar_y = screen_y - bar_y_offset
        
        health_percent = self.health / self.max_health
        
        # 血条背景
        pygame.draw.rect(screen, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        
        # 当前血量
        if health_percent > 0.5:
            bar_color = (0, 255, 0)
        elif health_percent > 0.25:
            bar_color = (255, 255, 0)
        else:
            bar_color = (255, 0, 0)
        
        fill_width = int(bar_width * health_percent)
        if fill_width > 0:
            pygame.draw.rect(screen, bar_color, (bar_x, bar_y, fill_width, bar_height))
        
        # 血条边框
        pygame.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 1)
