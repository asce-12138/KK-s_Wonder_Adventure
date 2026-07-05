import random
from .item import Item

class ItemManager:
    def __init__(self):
        self.items = []
        
        # 基础掉落概率
        self.base_coin_drop_rate = 0.1  # 10%概率掉落金币
        self.base_health_drop_rate = 0.05  # 5%概率掉落医疗包
        
        # 网络同步用掉落物ID计数器，仅主机使用
        self.next_item_id = 1
        self.authoritative = True
        
        # 拾取回调，用于通知 game.py 发送网络同步事件
        self.on_collect_callback = None
        
    def _generate_item_id(self):
        """生成唯一掉落物ID"""
        item_id = f"i_{self.next_item_id}"
        self.next_item_id += 1
        return item_id
    
    def get_item_by_id(self, item_id):
        """根据ID获取掉落物"""
        for item in self.items:
            if item.item_id == item_id:
                return item
        return None
    
    def remove_item_by_id(self, item_id):
        """根据ID移除掉落物"""
        item = self.get_item_by_id(item_id)
        if item and item in self.items:
            self.items.remove(item)
    
    def spawn_network_item(self, item_id, item_type, x, y):
        """根据网络消息生成本地掉落物（加入方使用）
        
        Args:
            item_id: 掉落物唯一ID
            item_type: 掉落物类型
            x: 世界坐标x
            y: 世界坐标y
        """
        if self.get_item_by_id(item_id) is not None:
            return
        item = Item(x, y, item_type, item_id=item_id, on_collect_callback=self.on_collect_callback)
        self.items.append(item)
        
    def spawn_item(self, x, y, enemy_type=None, player=None, item_id=None):
        """生成掉落物
        
        Args:
            x: 世界坐标x
            y: 世界坐标y
            enemy_type: 敌人类型，用于判断特殊掉落
            player: 玩家对象，用于幸运值计算
            item_id: 网络同步用ID，主机端自动生成
            
        Returns:
            list: 生成的掉落物ID列表（用于主机广播）
        """
        spawned_ids = []
        
        # 获取幸运值等级
        luck_level = 0
        if player and hasattr(player, 'passive_manager') and player.passive_manager:
            luck_level = player.passive_manager.get_passive_level('luck')
        
        # 经验掉落概率绑定幸运等级：0级40%，1级60%，2级80%，3级100%
        exp_drop_rates = {0: 0.4, 1: 0.6, 2: 0.8, 3: 1.0}
        exp_drop_rate = exp_drop_rates.get(luck_level, 1.0)
        
        if random.random() < exp_drop_rate:
            exp_id = item_id or (self._generate_item_id() if self.authoritative else None)
            if exp_id:
                spawned_ids.append((exp_id, 'exp', x, y))
            self.items.append(Item(x, y, 'exp', item_id=exp_id, on_collect_callback=self.on_collect_callback))

        # 如果是boss，必定掉落宝箱
        if enemy_type == 'bat':
            chest_id = self._generate_item_id() if self.authoritative else None
            if chest_id:
                spawned_ids.append((chest_id, 'chest', x, y))
            self.items.append(Item(x, y, 'chest', item_id=chest_id, on_collect_callback=self.on_collect_callback))
            return spawned_ids
        
        # 金币和药瓶基础概率（不受 luck_multiplier 影响）
        coin_rate = self.base_coin_drop_rate
        health_rate = self.base_health_drop_rate
        
        # 幸运值满级后稍微增加金币和药瓶概率
        if luck_level >= 3:
            coin_rate += 0.05
            health_rate += 0.03
        
        # 随机掉落金币
        if random.random() < coin_rate:
            coin_id = self._generate_item_id() if self.authoritative else None
            coin_x = x + random.randint(-10, 10)
            coin_y = y + random.randint(-10, 10)
            if coin_id:
                spawned_ids.append((coin_id, 'coin', coin_x, coin_y))
            self.items.append(Item(coin_x, coin_y, 'coin', item_id=coin_id, on_collect_callback=self.on_collect_callback))
            
        # 随机掉落医疗包
        if random.random() < health_rate:
            health_id = self._generate_item_id() if self.authoritative else None
            health_x = x + random.randint(-10, 10)
            health_y = y + random.randint(-10, 10)
            if health_id:
                spawned_ids.append((health_id, 'health', health_x, health_y))
            self.items.append(Item(health_x, health_y, 'health', item_id=health_id, on_collect_callback=self.on_collect_callback))
        
        return spawned_ids
            
    def update(self, dt, player):
        for item in self.items[:]:  # 使用切片创建副本以避免在迭代时修改列表
            item.update(dt, player)
            if item.collected:
                self.items.remove(item)
                
    def render(self, screen, camera_x, camera_y, screen_center_x, screen_center_y):
        for item in self.items:
            item.render(screen, camera_x, camera_y, screen_center_x, screen_center_y) 