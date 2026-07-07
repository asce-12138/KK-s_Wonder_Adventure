import pygame
from ..resource_manager import resource_manager

class Item(pygame.sprite.Sprite):
    """道具类，代表游戏中的可拾取物品（经验、金币、药水、宝箱等）"""
    
    def __init__(self, x, y, item_type, item_id=None, on_collect_callback=None):
        """初始化道具实例
        
        Args:
            x: 世界坐标X
            y: 世界坐标Y
            item_type: 道具类型（'exp'经验宝石, 'coin'金币, 'health'药水, 'chest'宝箱）
            item_id: 网络同步用唯一ID
            on_collect_callback: 拾取时的回调函数（用于网络同步）
        """
        super().__init__()
        self.world_x = x  # 在游戏世界中的X坐标
        self.world_y = y  # 在游戏世界中的Y坐标
        self.item_type = item_type  # 道具类型
        self.item_id = item_id  # 网络同步用唯一ID
        self.collected = False  # 是否已被拾取
        self.on_collect_callback = on_collect_callback  # 拾取回调
        
        # 根据物品类型设置图像和属性
        if item_type == 'exp':
            # 经验宝石 - 击杀敌人有概率掉落
            spritesheet = resource_manager.load_spritesheet('gems_spritesheet', 'images/items/gems.png')
            self.image = resource_manager.create_animation('exp_gem', spritesheet,
                                                         frame_width=16, frame_height=16,
                                                         frame_count=1, row=0,
                                                         frame_duration=0.1).get_current_frame()
            self.value = 100  # 经验值
        elif item_type == 'coin':
            # 金币 - 击杀敌人有概率掉落
            spritesheet = resource_manager.load_spritesheet('money_spritesheet', 'images/items/money.png')
            self.image = resource_manager.create_animation('coin', spritesheet,
                                                         frame_width=16, frame_height=16,
                                                         frame_count=1, row=0,
                                                         frame_duration=0.1).get_current_frame()
            self.value = 1  # 金币值
        elif item_type == 'health':
            # 药水 - 击杀敌人有概率掉落，恢复生命值
            spritesheet = resource_manager.load_spritesheet('potions_spritesheet', 'images/items/potions.png')
            self.image = resource_manager.create_animation('health', spritesheet,
                                                         frame_width=16, frame_height=16,
                                                         frame_count=1, row=0,
                                                         frame_duration=0.1).get_current_frame()
            self.value = 20  # 恢复血量
        # 宝箱 - 杀boss掉落，开宝箱抽奖(武器、被动升级卡片，组合超武升级只能通过宝箱)
        elif item_type == 'chest':
            spritesheet = resource_manager.load_spritesheet('chest_spritesheet', 'images/items/chests_bundled_16x16.png')
            self.image = resource_manager.create_animation('chest', spritesheet,
                                                         frame_width=16, frame_height=16, 
                                                         frame_count=1, row=0, col=6,
                                                         frame_duration=0.1).get_current_frame()

        # 缩放图片到合适大小
        if item_type == 'chest':
            self.image = pygame.transform.scale(self.image, (24, 24))  # 宝箱略大（24x24）
        else:
            self.image = pygame.transform.scale(self.image, (16, 16))  # 普通道具（16x16）
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        
        # 物品移动速度（被吸引向玩家移动的速度）
        self.attract_speed = 350
        
    def update(self, dt, player):
        """更新道具状态，实现向玩家吸引的逻辑
        
        Args:
            dt: 时间增量
            player: 玩家对象
        """
        if self.collected:
            return
            
        # 计算与玩家的距离
        dx = player.world_x - self.world_x
        dy = player.world_y - self.world_y
        distance = (dx**2 + dy**2)**0.5
        
        # 如果在玩家的拾取范围内，向玩家移动
        if distance < player.pickup_range:
            if distance > 0:
                self.world_x += (dx/distance) * self.attract_speed * dt
                self.world_y += (dy/distance) * self.attract_speed * dt
                
        # 如果足够接近玩家，触发收集
        if distance < 10:
            self.collect(player)
            
    def collect(self, player):
        """处理道具被玩家拾取的逻辑
        
        Args:
            player: 拾取道具的玩家对象
        """
        if self.collected:
            return
            
        self.collected = True
        
        if self.item_type == 'exp':
            player.add_experience(self.value)
        elif self.item_type == 'coin':
            player.add_coins(self.value)
        elif self.item_type == 'health':
            player.heal(self.value)
        elif self.item_type == 'chest':
            # TODO: 宝箱掉落物品,随机掉落武器、被动升级卡片、组合超武升级
            pass
        
        # 通知外部拾取事件，用于网络同步
        if self.on_collect_callback:
            self.on_collect_callback(self.item_id, self.item_type)

    def render(self, screen, camera_x, camera_y, screen_center_x, screen_center_y):
        if self.collected:
            return
            
        # 计算屏幕位置
        screen_x = screen_center_x + (self.world_x - camera_x)
        screen_y = screen_center_y + (self.world_y - camera_y)
        self.rect.center = (screen_x, screen_y)
        
        screen.blit(self.image, self.rect) 