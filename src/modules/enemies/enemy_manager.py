import pygame
import random
import math
from .types import Ghost, Radish, Bat, Slime, Skeleton, Skt, Bsl, Xiniu, Ap, Plant, Fly

class EnemyManager:
    def __init__(self):
        self.enemies = []
        self.spawn_timer = 0
        self.base_spawn_interval = 1  # 基础生成间隔
        self.spawn_interval = 1  # 当前生成间隔
        self.difficulty = "normal"  # 默认难度为normal
        self.difficulty_level = 1   # 难度等级，随游戏时间增长
        self.game_time = 0  # 游戏进行时间
        self.bat_spawn_timer = 0  # 蝙蝠生成计时器
        self.spawn_count = 0  # 生成次数计数器
        self.boss1_spawn_count = 0  # boss1生成次数计数器
        
        # 时间递增难度相关
        self.last_difficulty_time = 120  # 上次增加难度的时间（从2分钟开始）
        self.health_multiplier = 1.0  # 血量倍率
        self.speed_multiplier = 1.0  # 生成速度倍率
        self.min_spawn_interval = 0.1  # 最小生成间隔（限制最大生成速度）
        
        # 地图边界相关
        self.map_boundaries = None  # (min_x, min_y, max_x, max_y)
        self.current_map = None  # 当前地图名称
        
        # 网络同步用敌人ID计数器，仅主机使用
        self.next_enemy_id = 1
        self.authoritative = True  # 是否为权威端（主机）
        
        # 已发送过创建事件的敌人投射物（id -> projectile，仅主机使用）
        # 注意：会在 collect_new_projectile_events 中自动清理已销毁的投射物
        self.sent_projectile_refs = {}
        
    def set_map_boundaries(self, min_x, min_y, max_x, max_y):
        """设置地图边界
        
        Args:
            min_x: 最小X坐标
            min_y: 最小Y坐标
            max_x: 最大X坐标
            max_y: 最大Y坐标
        """
        self.map_boundaries = (min_x, min_y, max_x, max_y)
        
    def set_current_map(self, map_name):
        """设置当前地图名称"""
        self.current_map = map_name
        
    def spawn_enemy(self, enemy_type, x, y, health=None, damage=None, health_multiplier=None):
        """在指定位置生成指定类型和生命值的敌人
        
        Args:
            enemy_type: 敌人类型 ('ghost', 'radish', 'bat', 'slime')
            x: 世界坐标系中的x坐标
            y: 世界坐标系中的y坐标
            health: 指定生命值，如果为None则使用该类型的默认生命值
            damage: 指定伤害值，如果为None则使用该类型的默认伤害值
            health_multiplier: 血量倍率，应用于默认生命值
            
        Returns:
            Enemy: 生成的敌人实例
        """
        # 根据类型创建对应的敌人实例
        enemy = None
        
        # 使用新的构造函数，传递敌人类型、难度和等级
        if enemy_type == 'ghost':
            enemy = Ghost(x, y, enemy_type, self.difficulty, self.difficulty_level)
        elif enemy_type == 'radish':
            enemy = Radish(x, y, enemy_type, self.difficulty, self.difficulty_level)
        elif enemy_type == 'bat':
            enemy = Bat(x, y, enemy_type, self.difficulty, self.difficulty_level)
        elif enemy_type == 'slime':
            enemy = Slime(x, y, enemy_type, self.difficulty, self.difficulty_level)
        elif enemy_type == 'boss1':
            enemy = Skeleton(x, y, enemy_type, self.difficulty, self.difficulty_level)
        elif enemy_type == 'skt':
            enemy = Skt(x, y, enemy_type, self.difficulty, self.difficulty_level)
        elif enemy_type == 'bsl':
            enemy = Bsl(x, y, enemy_type, self.difficulty, self.difficulty_level)
        elif enemy_type == 'xiniu':
            enemy = Xiniu(x, y, enemy_type, self.difficulty, self.difficulty_level)
        elif enemy_type == 'ap':
            enemy = Ap(x, y, enemy_type, self.difficulty, self.difficulty_level)
        elif enemy_type == 'plant':
            enemy = Plant(x, y, enemy_type, self.difficulty, self.difficulty_level)
        elif enemy_type == 'fly':
            enemy = Fly(x, y, enemy_type, self.difficulty, self.difficulty_level)
            
        # 应用血量倍率
        if enemy and health_multiplier is not None and health_multiplier != 1.0:
            enemy.health = int(enemy.max_health * health_multiplier)
            enemy.max_health = enemy.health
            
        # 如果指定了生命值，覆盖配置的生命值
        if enemy and health is not None:
            enemy.health = health
            enemy.max_health = health
            
        # 如果指定了伤害值，覆盖配置的伤害值
        if enemy and damage is not None:
            enemy.damage = damage
            
        if enemy:
            if self.authoritative and enemy.enemy_id is None:
                enemy.enemy_id = self.next_enemy_id
                self.next_enemy_id += 1
            self.enemies.append(enemy)
            
        return enemy
        
    def update(self, dt, local_player, remote_player=None):
        """更新敌人管理器
        
        Args:
            dt: 时间增量
            local_player: 本地玩家对象
            remote_player: 远程玩家对象（可选），提供时怪物会追击最近玩家
        """
        self.game_time += dt
        self.spawn_timer += dt
        
        # 更新难度等级（根据游戏时间）
        self.difficulty_level = max(1, int(self.game_time // 60) + 1)  # 每60秒提升一级
        
        # 每60秒增加一次难度（从2分钟开始）
        while self.game_time >= self.last_difficulty_time:
            self.health_multiplier *= 1.5
            self.speed_multiplier *= 2
            self.spawn_interval = max(self.min_spawn_interval, self.base_spawn_interval / self.speed_multiplier)
            self.last_difficulty_time += 60
            
            # 对所有已存在的敌人应用血量增加
            for enemy in self.enemies:
                enemy.max_health = int(enemy.max_health * 1.5)
                enemy.health = int(enemy.health * 1.5)
        
        # 根据时间和玩家等级生成敌人（仅权威端）
        if self.authoritative and self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            self.random_spawn_enemy(local_player)
            
        # 蝙蝠生成：只在森林地图生成，每60秒一只（仅权威端）
        if self.authoritative and local_player.level >= 1 and self.current_map not in ['ocean_map', 'volcano_map']:
            self.bat_spawn_timer += dt
            if self.bat_spawn_timer >= 60:  # 每60秒生成一只蝙蝠
                self.bat_spawn_timer = 0
                self.spawn_bat(local_player)
            
        # 更新所有敌人
        players = [local_player]
        if remote_player is not None:
            players.append(remote_player)
        
        dead_enemies = []
        for enemy in self.enemies[:]:  # 使用切片创建副本以避免在迭代时修改列表
            target_player = self._find_nearest_player(enemy, players)
            enemy.update(dt, target_player)
            
            # 检查敌人是否已死亡（包括被燃烧伤害杀死的）
            if not enemy.alive():
                dead_enemies.append(enemy)
                try:
                    self.enemies.remove(enemy)
                    # 注意：在这里我们不再播放死亡音效，因为在enemy.py中已经播放
                except ValueError:
                    # 如果敌人已经被移除，忽略错误
                    pass
        
        return dead_enemies
    
    def collect_new_projectile_events(self):
        """收集新创建的敌人投射物事件（仅主机使用）
        
        Returns:
            list: 新投射物事件字典列表
        """
        events = []
        current_ids = set()
        
        for enemy in self.enemies:
            if not hasattr(enemy, 'projectiles'):
                continue
            for projectile in enemy.projectiles:
                pid = id(projectile)
                current_ids.add(pid)
                if pid in self.sent_projectile_refs:
                    continue
                self.sent_projectile_refs[pid] = projectile
                
                event = {
                    "enemy_id": getattr(enemy, 'enemy_id', None),
                    "enemy_type": getattr(enemy, 'type', 'unknown'),
                    "x": getattr(projectile, 'x', getattr(projectile, 'world_x', 0)),
                    "y": getattr(projectile, 'y', getattr(projectile, 'world_y', 0)),
                    "direction_x": getattr(projectile, 'direction_x', 0.0),
                    "direction_y": getattr(projectile, 'direction_y', 0.0),
                    "speed": getattr(projectile, 'speed', 200),
                    "lifetime": getattr(projectile, 'lifetime', 5.0),
                    "bullet_type": getattr(projectile, 'bullet_type', 1),
                }
                events.append(event)
        
        # 清理已销毁的投射物引用，避免内存泄漏
        destroyed_ids = [pid for pid, projectile in self.sent_projectile_refs.items() if not projectile.alive()]
        for pid in destroyed_ids:
            self.sent_projectile_refs.pop(pid, None)
        
        return events
    
    def _find_nearest_player(self, enemy, players):
        """找到离敌人最近的玩家
        
        Args:
            enemy: 敌人对象
            players: 玩家对象列表
            
        Returns:
            最近的玩家对象
        """
        if not players:
            return None
        if len(players) == 1:
            return players[0]
        
        nearest = players[0]
        min_distance = float('inf')
        for player in players:
            dx = player.world_x - enemy.rect.x
            dy = player.world_y - enemy.rect.y
            distance = math.sqrt(dx * dx + dy * dy)
            if distance < min_distance:
                min_distance = distance
                nearest = player
        return nearest
            
    def render(self, screen, camera_x, camera_y, screen_center_x, screen_center_y):
        for enemy in self.enemies:
            # 计算敌人在屏幕上的位置
            screen_x = screen_center_x + (enemy.rect.x - camera_x)
            screen_y = screen_center_y + (enemy.rect.y - camera_y)
            
            # 只渲染在屏幕范围内的敌人
            if -50 <= screen_x <= screen.get_width() + 50 and -50 <= screen_y <= screen.get_height() + 50:
                enemy.render(screen, screen_x, screen_y)
            
    def remove_enemy(self, enemy):
        if enemy in self.enemies:
            self.enemies.remove(enemy)
    
    def get_enemy_by_id(self, enemy_id):
        """根据ID获取敌人
        
        Args:
            enemy_id: 敌人唯一ID
            
        Returns:
            Enemy or None
        """
        for enemy in self.enemies:
            if enemy.enemy_id == enemy_id:
                return enemy
        return None
    
    def remove_enemy_by_id(self, enemy_id):
        """根据ID移除敌人
        
        Args:
            enemy_id: 敌人唯一ID
        """
        enemy = self.get_enemy_by_id(enemy_id)
        if enemy:
            self.enemies.remove(enemy)
    
    def spawn_enemy_from_network(self, state):
        """根据网络状态生成或更新敌人（加入方使用）
        
        Args:
            state: 敌人网络状态字典
            
        Returns:
            Enemy: 生成或更新的敌人
        """
        enemy_id = state.get("id")
        enemy_type = state.get("enemy_type")
        x = state.get("x", 0)
        y = state.get("y", 0)
        health = state.get("health")
        max_health = state.get("max_health")
        
        enemy = self.get_enemy_by_id(enemy_id)
        if enemy is None:
            # 创建新敌人
            enemy = self.spawn_enemy(enemy_type, x, y)
            if enemy:
                enemy.enemy_id = enemy_id
        
        if enemy:
            enemy.apply_network_state(state)
        
        return enemy
    
    def apply_enemy_sync(self, enemy_states):
        """应用主机同步的怪物状态（加入方使用）
        
        Args:
            enemy_states: 怪物状态列表
        """
        if not enemy_states:
            return
        
        # 记录当前所有敌人的ID
        current_ids = {enemy.enemy_id for enemy in self.enemies}
        synced_ids = set()
        
        for state in enemy_states:
            enemy_id = state.get("id")
            if enemy_id is None:
                continue
            synced_ids.add(enemy_id)
            self.spawn_enemy_from_network(state)
        
        # 移除主机端已经死亡的怪物
        removed_ids = current_ids - synced_ids
        for enemy_id in removed_ids:
            self.remove_enemy_by_id(enemy_id)
    
    def apply_damage_event(self, enemy_id, damage):
        """处理加入方上报的伤害事件（仅主机使用）
        
        Args:
            enemy_id: 敌人ID
            damage: 伤害值
            
        Returns:
            bool: 是否成功造成伤害
        """
        enemy = self.get_enemy_by_id(enemy_id)
        if enemy and enemy.alive():
            enemy.take_damage(damage)
            return True
        return False
    
    def get_all_network_states(self):
        """获取所有怪物的网络状态（仅主机使用）
        
        Returns:
            list: 怪物状态字典列表
        """
        states = []
        for enemy in self.enemies:
            if enemy.alive():
                states.append(enemy.to_network_state())
        return states
            
    def random_spawn_enemy(self, player):
        """在玩家周围随机位置生成敌人，确保在地图边界内"""
        # 在玩家周围的随机位置生成敌人
        spawn_distance = 600  # 生成距离
        
        # 尝试生成位置，最多尝试10次以找到在边界内的位置
        for _ in range(10):
            # 随机角度
            angle = random.uniform(0, 2 * math.pi)
            
            # 计算生成位置（世界坐标系）
            x = player.world_x + spawn_distance * math.cos(angle)
            y = player.world_y + spawn_distance * math.sin(angle)
            
            # 如果有地图边界限制，确保敌人在边界内生成
            if self.map_boundaries:
                min_x, min_y, max_x, max_y = self.map_boundaries
                
                # 检查生成位置是否在边界内
                if min_x <= x <= max_x and min_y <= y <= max_y:
                    break  # 位置有效，跳出循环
                
                # 如果位置无效，将坐标限制在边界内
                x = max(min_x, min(x, max_x))
                y = max(min_y, min(y, max_y))
                break  # 使用修正后的位置
        
        self.spawn_count += 1
        
        if self.current_map == 'ocean_map':
            enemy_type = random.choice(['fly', 'skt', 'xiniu'])
        elif self.current_map == 'volcano_map':
            enemy_type = random.choice(['ap', 'bsl', 'plant'])
        else:
            enemy_type = random.choice(['ghost', 'radish', 'slime'])
        self.spawn_enemy(enemy_type, x, y, health_multiplier=self.health_multiplier)
            
    def set_difficulty(self, difficulty):
        """设置游戏难度
        
        Args:
            difficulty (str): 难度级别 ('easy', 'normal', 'hard', 'nightmare')
        """
        self.difficulty = difficulty
        
    def recalculate_difficulty(self):
        """根据当前游戏时间重新计算难度倍率"""
        self.health_multiplier = 1.0
        self.speed_multiplier = 1.0
        self.last_difficulty_time = 120
        
        while self.game_time >= self.last_difficulty_time:
            self.health_multiplier *= 1.5
            self.speed_multiplier *= 2
            self.last_difficulty_time += 60
        
        self.spawn_interval = max(self.min_spawn_interval, self.base_spawn_interval / self.speed_multiplier)
            
    def spawn_bat(self, player):
        """在玩家周围生成一个蝙蝠，确保在地图边界内"""
        spawn_distance = 600
        
        # 尝试生成位置，最多尝试10次以找到在边界内的位置
        for _ in range(10):
            angle = random.uniform(0, 2 * math.pi)
            x = player.world_x + spawn_distance * math.cos(angle)
            y = player.world_y + spawn_distance * math.sin(angle)
            
            # 如果有地图边界限制，确保蝙蝠在边界内生成
            if self.map_boundaries:
                min_x, min_y, max_x, max_y = self.map_boundaries
                
                # 检查生成位置是否在边界内
                if min_x <= x <= max_x and min_y <= y <= max_y:
                    break  # 位置有效，跳出循环
                
                # 如果位置无效，将坐标限制在边界内
                x = max(min_x, min(x, max_x))
                y = max(min_y, min(y, max_y))
                break  # 使用修正后的位置
        
        self.spawn_enemy('bat', x, y, health_multiplier=self.health_multiplier) 