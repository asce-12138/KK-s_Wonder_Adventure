import pygame
import math
from .player import Player
from .enemies.enemy_manager import EnemyManager
from .items.item_manager import ItemManager
from .ui import UI
from .menu import PauseMenu, GameOverMenu, UpgradeMenu
from .menus.main_menu import MainMenu
from .menus.save_menu import SaveMenu
from .save_system import SaveSystem
from .resource_manager import resource_manager
from .upgrade_system import UpgradeManager, WeaponUpgradeLevel, PassiveUpgradeLevel
from .utils import apply_mask_collision
from .map_manager import MapManager
from .menus.map_hero_select_menu import MapHeroSelectMenu
from .network_client import get_network_client
from .remote_player import RemotePlayer
from .utils import FontManager
from .weapons.types.knife import ThrownKnife
from .weapons.types.fireball import FireballProjectile
from .weapons.types.frost_nova import FrostNovaProjectile
from .weapons.weapon_stats import WeaponStatType, DEFAULT_WEAPON_STATS
from .enemies.visual_enemy_projectile import VisualEnemyProjectile

class Game:
    def __init__(self, screen, network_mode=False, is_host=False, local_player_id=1, on_return_to_lobby=None):
        self.screen = screen
        self.running = True
        self.paused = False
        self.game_over = False
        self.in_main_menu = True
        self.in_map_hero_select = False
        
        self.network_mode = network_mode
        self.is_host = is_host
        self.local_player_id = local_player_id
        self.on_return_to_lobby = on_return_to_lobby
        self.disconnect_message = None
        self.network_sync_timer = 0
        self.network_sync_interval = 0.05
        
        # 怪物同步相关
        self.enemy_sync_timer = 0
        self.enemy_sync_interval = 0.1  # 10Hz 怪物状态同步
        self.pending_dead_enemies = []  # 本帧死亡的敌人，用于主机广播
        
        # 敌人投射物视觉副本（客户端显示主机敌人子弹）
        self.visual_enemy_projectiles = pygame.sprite.Group()
        
        self.remote_player = None
        self.remote_player_data = None
        self.show_disconnect_popup = False
        self.disconnect_popup_timer = 0
        
        resource_manager._init_resources()
        
        self.screen_center_x = self.screen.get_width() // 2
        self.screen_center_y = self.screen.get_height() // 2
        
        self.player = None
        
        self.camera_x = 0
        self.camera_y = 0
        
        self.grid_size = 50
        self.grid_color = (50, 50, 50)
        
        self.enemy_manager = None
        self.item_manager = None
        self.save_system = SaveSystem()
        self.upgrade_manager = UpgradeManager()
        self.map_manager = MapManager(screen)
        
        self.ui = UI(screen)
        
        if self.network_mode:
            self.main_menu = None
            self.in_main_menu = False
            self.in_map_hero_select = True
        else:
            extra_options = [{'text': '联机模式', 'action': 'multiplayer'}]
            self.main_menu = MainMenu(screen, extra_options=extra_options)
        
        self.pause_menu = PauseMenu(screen)
        self.game_over_menu = GameOverMenu(screen)
        self.victory_menu = GameOverMenu(screen, title="你过关")
        self.upgrade_menu = UpgradeMenu(screen)
        self.save_menu = SaveMenu(screen, True)
        self.load_menu = SaveMenu(screen, False)
        
        self.map_hero_select_menu = MapHeroSelectMenu(
            screen,
            on_start_game=self._start_game_with_selection,
            on_back=self._back_to_main_menu
        )
        
        self.game_time = 0
        self.kill_num = 0
        self.level = 1
        self.level_complete = False
        self.victory_coin_threshold = 300
        
        self.current_map = None
        
        self.popup_font = FontManager.get_font(28)
        
        if self.network_mode:
            self._setup_network()
            self.map_hero_select_menu.show()
        else:
            self._play_menu_music()
        
    def _setup_network(self):
        """设置网络回调"""
        net_client = get_network_client()
        net_client.on_disconnected = self._on_network_disconnected
        self.remote_player = RemotePlayer(hero_type="ninja_frog")
        self.remote_player.player_name = f"玩家{2 if self.local_player_id == 1 else 1}"
        if self.local_player_id == 1:
            self.remote_player.name_color = (0, 255, 255)
        else:
            self.remote_player.name_color = (255, 200, 0)
        
        self._play_game_music()
    
    def _on_network_disconnected(self):
        """网络断开回调"""
        self.disconnect_message = "连接已断开，正在返回联机大厅..."
        self.show_disconnect_popup = True
        self.disconnect_popup_timer = 2.0
    
    def _return_to_lobby(self):
        """返回联机大厅"""
        if self.on_return_to_lobby:
            msg = self.disconnect_message if self.disconnect_message else None
            self.on_return_to_lobby(msg)
    
    def _on_item_collected(self, item_id, item_type):
        """掉落物被拾取时的回调"""
        if not self.network_mode or not item_id:
            return
        net_client = get_network_client()
        net_client.send_item_pickup(item_id)
    
    def _process_network_enemy_sync(self):
        """处理怪物全量同步数据（加入方）"""
        if self.is_host:
            return
        net_client = get_network_client()
        sync_data = net_client.get_enemy_sync_data()
        if sync_data and self.enemy_manager:
            enemy_states = sync_data.get("enemies", [])
            self.enemy_manager.apply_enemy_sync(enemy_states)
    
    def _process_network_enemy_events(self):
        """处理怪物事件（主机处理加入方伤害，加入方处理生成/死亡）"""
        if not self.network_mode:
            return
        net_client = get_network_client()
        events = net_client.get_enemy_events()
        for event in events:
            msg_type = event.get("type")
            if msg_type == "enemy_damage":
                # 只有主机处理伤害事件
                if self.is_host and self.enemy_manager:
                    enemy_id = event.get("enemy_id")
                    damage = event.get("damage", 0)
                    self.enemy_manager.apply_damage_event(enemy_id, damage)
            elif msg_type == "enemy_death":
                # 加入方处理死亡事件
                if not self.is_host and self.enemy_manager:
                    enemy_id = event.get("enemy_id")
                    self.enemy_manager.remove_enemy_by_id(enemy_id)
            elif msg_type == "enemy_spawn":
                # 加入方处理生成事件
                if not self.is_host and self.enemy_manager:
                    state = event.copy()
                    state.pop("type", None)
                    state.pop("timestamp", None)
                    self.enemy_manager.spawn_enemy_from_network(state)
    
    def _process_network_item_events(self):
        """处理掉落物事件"""
        if not self.network_mode:
            return
        net_client = get_network_client()
        events = net_client.get_item_events()
        for event in events:
            msg_type = event.get("type")
            if msg_type == "item_spawn":
                item_id = event.get("item_id")
                item_type = event.get("item_type")
                x = event.get("x")
                y = event.get("y")
                if item_id and item_type and x is not None and y is not None and self.item_manager:
                    self.item_manager.spawn_network_item(item_id, item_type, x, y)
            elif msg_type == "item_remove":
                item_id = event.get("item_id")
                if item_id and self.item_manager:
                    self.item_manager.remove_item_by_id(item_id)
            elif msg_type == "item_pickup":
                # 主机收到拾取事件，广播移除
                if self.is_host:
                    item_id = event.get("item_id")
                    if item_id and self.item_manager:
                        self.item_manager.remove_item_by_id(item_id)
                        net_client.send_item_remove(item_id)
    
    def _broadcast_enemy_death(self, enemy):
        """处理怪物死亡：单机直接生成掉落物；网络主机广播死亡事件和掉落物"""
        x = enemy.rect.x
        y = enemy.rect.y
        enemy_type = enemy.type
        
        # 单机模式直接生成掉落物
        if not self.network_mode:
            if self.item_manager:
                self.item_manager.spawn_item(x, y, enemy_type, self.player)
            return
        
        # 加入方不处理
        if not self.is_host:
            return
        
        net_client = get_network_client()
        enemy_id = enemy.enemy_id
        
        # 广播死亡事件
        net_client.send_enemy_death(enemy_id, x, y, enemy_type)
        
        # 生成掉落物并广播
        if self.item_manager:
            spawned = self.item_manager.spawn_item(x, y, enemy_type, self.player)
            for item_id, item_type, ix, iy in spawned:
                net_client.send_item_spawn(item_id, item_type, ix, iy)
    
    def _send_enemy_damage(self, enemy, damage):
        """加入方上报怪物伤害"""
        if not self.network_mode or self.is_host:
            return
        if enemy.enemy_id is None:
            return
        net_client = get_network_client()
        net_client.send_enemy_damage(enemy.enemy_id, damage)
    
    def _on_projectile_created(self, weapon_type, projectile):
        """本地玩家创建投射物时的回调，发送网络特效事件"""
        if not self.network_mode:
            return
        self._send_weapon_attack_event(weapon_type, projectile)
    
    def _send_weapon_attack_event(self, weapon_type, projectile):
        """发送武器攻击特效事件"""
        if not self.network_mode:
            return
        net_client = get_network_client()
        if not net_client.connected:
            return
        
        direction_x = getattr(projectile, 'direction_x', 0.0)
        direction_y = getattr(projectile, 'direction_y', 0.0)
        level = self.player.weapon_manager.get_weapon_level(weapon_type) if self.player and self.player.weapon_manager else 1
        is_mega = getattr(projectile, 'is_mega', False)
        spawn_direction = getattr(projectile, 'spawn_direction', None)
        
        # 对于 FrostNova 的额外冰锥，使用原始方向
        if spawn_direction is not None:
            direction_x, direction_y = spawn_direction[0], spawn_direction[1]
        
        net_client.send_weapon_attack(
            weapon_type,
            self.player.world_x,
            self.player.world_y,
            (direction_x, direction_y),
            level=level,
            is_mega=is_mega
        )
    
    def _process_weapon_attack_events(self):
        """处理接收到的武器特效事件，创建视觉投射物"""
        if not self.network_mode or not self.remote_player:
            return
        net_client = get_network_client()
        events = net_client.get_weapon_attack_events()
        for event in events:
            self._create_visual_projectile(event)
    
    def _create_visual_projectile(self, event):
        """根据网络事件创建视觉投射物"""
        if not self.remote_player:
            return
        
        weapon_type = event.get("weapon_type")
        x = event.get("x", self.remote_player.world_x)
        y = event.get("y", self.remote_player.world_y)
        direction_x = event.get("direction_x", 1.0)
        direction_y = event.get("direction_y", 0.0)
        level = event.get("level", 1)
        
        # 优先使用远程玩家当前位置，避免网络延迟导致位置偏差过大
        x = self.remote_player.world_x
        y = self.remote_player.world_y
        
        # 构造武器当前属性（用于特效外观）
        stats = DEFAULT_WEAPON_STATS.copy()
        # 根据等级简单放大部分属性以匹配视觉效果
        stats[WeaponStatType.DAMAGE] = stats.get(WeaponStatType.DAMAGE, 20) * (1 + (level - 1) * 0.3)
        stats[WeaponStatType.PROJECTILE_SPEED] = stats.get(WeaponStatType.PROJECTILE_SPEED, 300)
        stats[WeaponStatType.LIFETIME] = stats.get(WeaponStatType.LIFETIME, 2.0)
        
        projectile = None
        try:
            if weapon_type == 'knife':
                projectile = ThrownKnife(x, y, direction_x, direction_y, stats)
            elif weapon_type == 'fireball':
                # 火球使用固定方向，避免追踪近处目标导致旋转/震荡
                is_mega = event.get("is_mega", False)
                if is_mega:
                    stats[WeaponStatType.BIG_FIREBALL_SCALE] = 5.0
                    stats[WeaponStatType.BIG_FIREBALL_DAMAGE_MULTIPLIER] = 3.0
                    stats[WeaponStatType.BIG_FIREBALL_RADIUS_MULTIPLIER] = 3.0
                projectile = FireballProjectile(x, y, None, stats, is_mega=is_mega, fixed_direction=(direction_x, direction_y))
            elif weapon_type == 'frost_nova':
                class DummyTarget:
                    def __init__(self, x, y):
                        self.rect = pygame.Rect(x, y, 1, 1)
                    def alive(self):
                        return True
                target = DummyTarget(x + direction_x * 100, y + direction_y * 100)
                projectile = FrostNovaProjectile(x, y, target, stats, direction=(direction_x, direction_y))
        except Exception as e:
            print(f"[game] 创建视觉投射物失败: {e}")
            return
        
        if projectile:
            projectile.visual_only = True
            # 设置特效组，使爆炸特效能在远程玩家处渲染
            projectile.effects_group = self.remote_player.visual_effects
            self.remote_player.add_visual_projectile(projectile)
    
    def _broadcast_enemy_projectiles(self):
        """主机广播新创建的敌人投射物事件"""
        if not self.network_mode or not self.is_host or not self.enemy_manager:
            return
        events = self.enemy_manager.collect_new_projectile_events()
        if not events:
            return
        net_client = get_network_client()
        for event in events:
            net_client.send_enemy_projectile(event)
    
    def _process_enemy_projectile_events(self):
        """客户端处理敌人投射物事件，创建视觉副本"""
        if not self.network_mode or self.is_host:
            return
        net_client = get_network_client()
        events = net_client.get_enemy_projectile_events()
        for event in events:
            self._create_visual_enemy_projectile(event)
    
    def _create_visual_enemy_projectile(self, event):
        """根据网络事件创建敌人投射物的视觉副本"""
        try:
            projectile = VisualEnemyProjectile(
                x=event.get("x", 0),
                y=event.get("y", 0),
                direction_x=event.get("direction_x", 0.0),
                direction_y=event.get("direction_y", 0.0),
                enemy_type=event.get("enemy_type", "unknown"),
                speed=event.get("speed", 200),
                lifetime=event.get("lifetime", 5.0),
                bullet_type=event.get("bullet_type", 1)
            )
            self.visual_enemy_projectiles.add(projectile)
        except Exception as e:
            print(f"[game] 创建敌人视觉投射物失败: {e}")
        
    def _set_map_boundaries(self):
        if not self.current_map:
            return
            
        map_width, map_height = self.map_manager.get_map_size()
        
        fence_width = 2 * 32
        
        min_x = fence_width
        min_y = fence_width
        max_x = map_width - fence_width
        max_y = map_height - fence_width
        
        if self.player:
            self.player.movement.set_boundaries(min_x, min_y, max_x, max_y)
            
        if self.enemy_manager:
            self.enemy_manager.set_map_boundaries(min_x, min_y, max_x, max_y)
            self.enemy_manager.set_current_map(self.current_map)
            
    def _set_player_boundaries(self):
        self._set_map_boundaries()
        
    def _start_game_with_selection(self, map_id, hero_id):
        self.in_map_hero_select = False
        self.game_over = False
        self.paused = False
        
        self.load_map(map_id)
        
        map_width, map_height = self.map_manager.get_map_size()
        
        self.player = Player(self.screen_center_x, self.screen_center_y, hero_id)
        
        self.player.world_x = map_width // 2
        self.player.world_y = map_height // 2
        
        if self.network_mode and self.local_player_id == 2:
            self.player.world_x = map_width // 2 + 100
            self.player.world_y = map_height // 2 + 100
        
        self.enemy_manager = EnemyManager()
        self.enemy_manager.set_difficulty("normal")
        
        self.item_manager = ItemManager()
        self.item_manager.on_collect_callback = self._on_item_collected
        
        # 网络模式下只有主机是权威端
        if self.network_mode:
            self.enemy_manager.authoritative = self.is_host
            self.item_manager.authoritative = self.is_host
        
        # 设置武器投射物创建回调，用于网络特效同步
        if self.player and self.player.weapon_manager:
            self.player.weapon_manager.on_projectile_created = self._on_projectile_created
        
        self._set_map_boundaries()
        
        self.game_time = 0
        self.kill_num = 0
        self.level = 1
        self.level_complete = False
        
        self.camera_x = self.player.world_x
        self.camera_y = self.player.world_y
        
        resource_manager.play_map_music(map_id, loops=-1)
        
        if self.network_mode and self.remote_player:
            self.remote_player.world_x = self.player.world_x + 80
            self.remote_player.world_y = self.player.world_y
        
    def _back_to_main_menu(self):
        if self.network_mode:
            self._return_to_lobby()
            return
        self.in_map_hero_select = False
        self.in_main_menu = True
        self._play_menu_music()
        
    def _play_menu_music(self):
        resource_manager.play_music("menu", loops=-1)
        
    def _play_game_music(self):
        resource_manager.play_music("background", loops=-1)
        
    def start_new_game(self):
        self.in_main_menu = False
        self.in_map_hero_select = True
        self.map_hero_select_menu.show()
            
    def load_map(self, map_name):
        success = self.map_manager.load_map(map_name)
        if success:
            self.current_map = map_name
            
            map_width, map_height = self.map_manager.get_map_size()
            
            if self.player:
                self.player.world_x = map_width // 2
                self.player.world_y = map_height // 2
                
                self.camera_x = self.player.world_x
                self.camera_y = self.player.world_y
                
                self._set_map_boundaries()
            
        else:
            print(f"加载地图 '{map_name}' 失败")
            
        return success

    def load_game_state(self, save_data):
        try:
            self.in_main_menu = False
            self.game_over = False
            self.paused = False
            
            player_data = save_data.get('player_data', {})
            if not player_data:
                print("存档数据损坏：缺少玩家数据")
                return False
                
            hero_type = player_data.get('hero_type', 'ninja_frog')
            self.player = Player(self.screen_center_x, self.screen_center_y, hero_type)
            
            self.player.health = player_data.get('health', self.player.health)
            self.player.health_component.max_health = player_data.get('max_health', self.player.health_component.max_health)
            self.player.progression.level = player_data.get('level', self.player.progression.level)
            self.player.progression.experience = player_data.get('experience', 0)
            self.player.progression.coins = player_data.get('coins', 0)
            self.player.world_x = player_data.get('world_x', self.screen_center_x)
            self.player.world_y = player_data.get('world_y', self.screen_center_y)
            
            component_states = player_data.get('component_states', {})
            if component_states:
                movement_states = component_states.get('movement', {})
                if movement_states:
                    self.player.movement.speed = movement_states.get('speed', self.player.movement.speed)
                    self.player.movement.direction = pygame.math.Vector2(0, 0)
                    self.player.movement.velocity = pygame.math.Vector2(0, 0)
                    self.player.movement.moving = {
                        'up': False, 
                        'down': False, 
                        'left': False, 
                        'right': False
                    }
                    if 'facing_right' in movement_states:
                        self.player.movement.facing_right = movement_states.get('facing_right')
                    if 'last_direction_x' in movement_states and 'last_direction_y' in movement_states:
                        self.player.movement.last_movement_direction.x = movement_states.get('last_direction_x', 1)
                        self.player.movement.last_movement_direction.y = movement_states.get('last_direction_y', 0)
                
                health_states = component_states.get('health', {})
                if health_states:
                    self.player.health_component.defense = health_states.get('defense', self.player.health_component.defense)
                    self.player.health_component.health_regen = health_states.get('health_regen', self.player.health_component.health_regen)
                
                progression_states = component_states.get('progression', {})
                if progression_states:
                    self.player.progression.exp_multiplier = progression_states.get('exp_multiplier', self.player.progression.exp_multiplier)
                    self.player.progression.luck = progression_states.get('luck', self.player.progression.luck)
                
                passive_states = component_states.get('passive', {})
                if passive_states and 'passive_levels' in passive_states:
                    passive_levels = passive_states['passive_levels']
                    for passive_type, level in passive_levels.items():
                        if passive_type in self.upgrade_manager.passive_upgrades:
                            upgrade = self.upgrade_manager.passive_upgrades[passive_type]
                            effect = None
                            for lvl in upgrade.levels:
                                if lvl.level == level:
                                    effect = lvl.effects
                                    break
                            if effect:
                                self.player.apply_passive_upgrade(passive_type, level, effect)
                            else:
                                self.player.passive_manager.passive_levels[passive_type] = level
                        else:
                            self.player.passive_manager.passive_levels[passive_type] = level
                    self.player._update_stats()
            
            weapons_data = player_data.get('weapons', [])
            if weapons_data:
                for weapon in list(self.player.weapons):
                    self.player.weapon_manager.remove_weapon(weapon.type)
                
                for weapon_type, level in weapons_data:
                    weapon = self.player.add_weapon(weapon_type)
                    if weapon:
                        weapon.level = level
            
            self.enemy_manager = EnemyManager()
            self.item_manager = ItemManager()
            
            game_data = save_data.get('game_data', {})
            self.game_time = game_data.get('game_time', 0)
            self.kill_num = game_data.get('kill_num', 0)
            self.level = game_data.get('level', 1)
            
            self.enemy_manager.difficulty_level = self.level
            self.enemy_manager.set_difficulty(game_data.get('difficulty', 'normal'))
            self.enemy_manager.game_time = self.game_time
            self.enemy_manager.recalculate_difficulty()
            
            enemies_data = save_data.get('enemies_data', [])
            for enemy_data in enemies_data:
                try:
                    self.enemy_manager.spawn_enemy(
                        enemy_data.get('type', 'normal'),
                        enemy_data.get('x', 0),
                        enemy_data.get('y', 0),
                        enemy_data.get('health', 50)
                    )
                except Exception as e:
                    print(f"加载敌人时出错: {e}")
                    continue
            
            self.camera_x = self.player.world_x
            self.camera_y = self.player.world_y
            
            self._set_map_boundaries()
            
            resource_manager.play_music("background", loops=-1)
            
            return True
            
        except Exception as e:
            print(f"加载存档时出错: {e}")
            self.start_new_game()
            return False
        
    def handle_event(self, event):
        if self.show_disconnect_popup:
            return
        
        if self.in_map_hero_select:
            result = self.map_hero_select_menu.handle_event(event)
            return
            
        if self.in_main_menu:
            if self.load_menu.is_active:
                action = self.load_menu.handle_event(event)
                if action == "back":
                    self.load_menu.hide()
                elif isinstance(action, dict):
                    if self.load_game_state(action):
                        self.in_main_menu = False
                        self.load_menu.hide()
                    else:
                        print("加载存档失败")
                return
            
            action = self.main_menu.handle_event(event)
            if action == "start":
                self.start_new_game()
            elif action == "load":
                print("显示读取菜单")
                self.load_menu.show()
            elif action == "multiplayer":
                self._return_to_lobby()
            elif action == "quit":
                self.running = False
            return
            
        if self.load_menu.is_active:
            action = self.load_menu.handle_event(event)
            if action == "back":
                self.load_menu.hide()
            elif isinstance(action, dict):
                if self.load_game_state(action):
                    self.load_menu.hide()
                    self.paused = False
                else:
                    print("加载存档失败")
            return
            
        if self.save_menu.is_active:
            action = self.save_menu.handle_event(event)
            if action and action.startswith("slot_"):
                slot_id = int(action.split("_")[1])
                self.save_system.save_game(slot_id, self, self.screen)
                self.save_menu.hide()
                self.paused = False
            elif action == "back":
                self.save_menu.hide()
            return
            
        if self.level_complete:
            action = self.victory_menu.handle_event(event)
            if action == "restart":
                self.start_new_game()
            elif action == "main_menu":
                if self.network_mode:
                    self._return_to_lobby()
                else:
                    self.in_main_menu = True
                    self.level_complete = False
                    self._play_menu_music()
            elif action == "exit":
                if self.network_mode:
                    self._return_to_lobby()
                else:
                    self.running = False
            return
            
        if self.game_over:
            action = self.game_over_menu.handle_event(event)
            if action == "restart":
                self.start_new_game()
            elif action == "main_menu":
                if self.network_mode:
                    self._return_to_lobby()
                else:
                    self.in_main_menu = True
                    self.game_over = False
                    self._play_menu_music()
            elif action == "exit":
                if self.network_mode:
                    self._return_to_lobby()
                else:
                    self.running = False
            return
            
        if self.paused:
            action = self.pause_menu.handle_event(event)
            if action == "continue":
                self.toggle_pause()
            elif action == "save":
                self.save_menu.show()
            elif action == "restart":
                self.start_new_game()
            elif action == "main_menu":
                if self.network_mode:
                    self._return_to_lobby()
                else:
                    self.in_main_menu = True
                    self.paused = False
                    self._play_menu_music()
            elif action == "exit":
                if self.network_mode:
                    self._return_to_lobby()
                else:
                    self.running = False
            return
               
        if self.upgrade_menu.is_active:
            selected_upgrade = self.upgrade_menu.handle_event(event)
            if selected_upgrade:
                self._apply_upgrade(selected_upgrade)
                self.upgrade_menu.hide()
            return True
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.toggle_pause()
                return True
            elif event.key == pygame.K_F2:
                if self.player:
                    self.player.toggle_outline()
                    for enemy in self.enemy_manager.enemies:
                        enemy.toggle_outline()
                return True
            
        if self.player:
            self.player.handle_event(event)
            
        return True
        
    def _apply_upgrade(self, upgrade_level):
        if isinstance(upgrade_level, WeaponUpgradeLevel):
            weapon_type = None
            for type_, upgrade in self.upgrade_manager.weapon_upgrades.items():
                if upgrade_level in upgrade.levels:
                    weapon_type = type_
                    break
                    
            if weapon_type:
                if self.player.apply_weapon_upgrade(weapon_type, upgrade_level.level, upgrade_level.effects):
                    if len([w for w in self.player.weapons if w.type == weapon_type]) == 0:
                        self.player.add_weapon(weapon_type)
                        
        elif isinstance(upgrade_level, PassiveUpgradeLevel):
            passive_type = None
            for type_, upgrade in self.upgrade_manager.passive_upgrades.items():
                if upgrade_level in upgrade.levels:
                    passive_type = type_
                    break
                    
            if passive_type:
                self.player.apply_passive_upgrade(passive_type, upgrade_level.level, upgrade_level.effects)
                
    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.pause_menu.show()
            resource_manager.pause_music()
        else:
            self.pause_menu.hide()
            resource_manager.unpause_music()
        
    def update(self, dt):
        if self.show_disconnect_popup:
            self.disconnect_popup_timer -= dt
            if self.disconnect_popup_timer <= 0:
                self._return_to_lobby()
            return
        
        if self.in_main_menu:
            return
            
        if self.in_map_hero_select:
            return
            
        if self.network_mode:
            net_client = get_network_client()
            if not net_client.is_connected():
                if not self.show_disconnect_popup:
                    self.disconnect_message = "网络连接已中断"
                    self.show_disconnect_popup = True
                    self.disconnect_popup_timer = 2.0
                return
            
            remote_data = net_client.get_remote_player_data()
            if remote_data:
                self.remote_player_data = remote_data
                if self.remote_player:
                    self.remote_player.update_from_network(remote_data)
            
            self.network_sync_timer += dt
            if self.network_sync_timer >= self.network_sync_interval and self.player:
                self.network_sync_timer = 0
                is_moving = self.player.movement.is_moving()
                facing_right = self.player.movement.facing_right
                is_hurt = self.player.health_component.is_hurt()
                
                net_client.send_player_data(
                    self.player.world_x,
                    self.player.world_y,
                    self.player.health,
                    self.player.max_health,
                    self.player.hero_type,
                    is_moving,
                    facing_right,
                    is_hurt
                )
            
        if self.player and self.player.health <= 0 and not self.game_over:
            self.game_over = True
            self.game_over_menu.show()
            resource_manager.play_sound("player_death")
            return
        
        # 金币达到目标数量，显示过关
        if (self.player and self.player.coins >= self.victory_coin_threshold
                and not self.level_complete and not self.game_over):
            self.level_complete = True
            self.victory_menu.show()
            resource_manager.play_sound("level_up")
            return
            
        if self.level_complete:
            self.victory_menu.update(pygame.mouse.get_pos())
            return
            
        if self.game_over:
            self.game_over_menu.update(pygame.mouse.get_pos())
            return
            
        if self.paused or self.upgrade_menu.is_active or self.save_menu.is_active:
            return
            
        self.game_time += dt
        
        if self.player:
            self.player.update(dt)
            
            self.camera_x = self.player.world_x
            self.camera_y = self.player.world_y
        
        if self.network_mode and self.remote_player:
            self.remote_player.update(dt)
        
        # 处理网络同步事件
        if self.network_mode:
            self._process_network_enemy_events()
            self._process_network_item_events()
            self._process_weapon_attack_events()
            self._process_enemy_projectile_events()
        
        if self.enemy_manager and self.player:
            # 主机/单机：运行完整的怪物AI；加入方：只应用主机同步的怪物状态
            if self.network_mode and not self.is_host:
                self._process_network_enemy_sync()
                self.player.update_weapons(dt, self.enemy_manager.enemies)
            else:
                remote_player = self.remote_player if self.network_mode else None
                dead_enemies = self.enemy_manager.update(dt, self.player, remote_player)
                
                # 处理自然死亡（燃烧等）的怪物
                for enemy in dead_enemies:
                    self.kill_num += 1
                    self._broadcast_enemy_death(enemy)
                
                # 主机广播新创建的敌人投射物
                if self.network_mode and self.is_host:
                    self._broadcast_enemy_projectiles()
                
                # 主机定时广播怪物全量状态
                if self.network_mode and self.is_host:
                    self.enemy_sync_timer += dt
                    if self.enemy_sync_timer >= self.enemy_sync_interval:
                        self.enemy_sync_timer = 0
                        net_client = get_network_client()
                        net_client.send_enemy_sync(self.enemy_manager.get_all_network_states())
                
                self.player.update_weapons(dt, self.enemy_manager.enemies)
            
            if self.item_manager:
                self.item_manager.update(dt, self.player)
            
            self._check_collisions()
        
        # 更新敌人投射物视觉副本（客户端）
        self.visual_enemy_projectiles.update(dt)
        for projectile in list(self.visual_enemy_projectiles):
            if not projectile.alive():
                self.visual_enemy_projectiles.remove(projectile)
        
        if self.player and self.player.add_experience(0):
            self.player.level_up()
            self.upgrade_menu.show(self.player, self)
        
    def render(self):
        self.screen.fill((0, 0, 0))
        
        if self.in_main_menu:
            if self.load_menu.is_active:
                self.load_menu.render()
            else:
                self.main_menu.render()
            pygame.display.flip()
            return
            
        if self.in_map_hero_select:
            self.map_hero_select_menu.render()
            pygame.display.flip()
            return
            
        if self.save_menu.is_active:
            self.save_menu.render()
            return
            
        if self.current_map:
            self.map_manager.render(self.camera_x, self.camera_y)
        else:
            self._draw_grid()
        
        if self.enemy_manager:
            self.enemy_manager.render(self.screen, self.camera_x, self.camera_y, 
                                   self.screen_center_x, self.screen_center_y)
        
        # 渲染敌人投射物视觉副本（客户端）
        for projectile in self.visual_enemy_projectiles:
            if hasattr(projectile, 'render'):
                projectile.render(self.screen, self.camera_x, self.camera_y)
        
        if self.item_manager:
            self.item_manager.render(self.screen, self.camera_x, self.camera_y, 
                                  self.screen_center_x, self.screen_center_y)
        
        if self.network_mode and self.remote_player:
            self.remote_player.render(self.screen, self.camera_x, self.camera_y,
                                     self.screen_center_x, self.screen_center_y)
        
        if self.player:
            self.player.render(self.screen)
            self.player.render_weapons(self.screen, self.camera_x, self.camera_y)
            
            self.ui.render(self.player, self.game_time, self.kill_num)
            
        if self.paused:
            self.pause_menu.render()
            
        if self.save_menu.is_active:
            self.save_menu.render()
            
        if self.upgrade_menu.is_active:
            self.upgrade_menu.render()
            
        if self.level_complete:
            self.victory_menu.render()
            
        if self.game_over:
            self.game_over_menu.render()
        
        if self.show_disconnect_popup:
            self._render_disconnect_popup()
            
        pygame.display.flip()
    
    def _render_disconnect_popup(self):
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        popup_width = 500
        popup_height = 150
        popup_x = (self.screen.get_width() - popup_width) // 2
        popup_y = (self.screen.get_height() - popup_height) // 2
        
        pygame.draw.rect(self.screen, (60, 30, 30), (popup_x, popup_y, popup_width, popup_height), border_radius=15)
        pygame.draw.rect(self.screen, (200, 80, 80), (popup_x, popup_y, popup_width, popup_height), 3, border_radius=15)
        
        if self.disconnect_message:
            text = self.popup_font.render(self.disconnect_message, True, (255, 100, 100))
        else:
            text = self.popup_font.render("连接已断开，正在返回大厅...", True, (255, 100, 100))
        text_rect = text.get_rect(center=(self.screen.get_width() // 2, popup_y + popup_height // 2))
        self.screen.blit(text, text_rect)
        
    def _draw_grid(self):
        offset_x = (self.camera_x % self.grid_size)
        offset_y = (self.camera_y % self.grid_size)
        
        for i in range(int(self.screen.get_width() / self.grid_size) + 2):
            x = i * self.grid_size - offset_x
            pygame.draw.line(self.screen, self.grid_color, (x, 0), (x, self.screen.get_height()))
            
        for i in range(int(self.screen.get_height() / self.grid_size) + 2):
            y = i * self.grid_size - offset_y
            pygame.draw.line(self.screen, self.grid_color, (0, y), (self.screen.get_width(), y))
        
    def _handle_client_weapon_collision(self, projectile, enemy, weapon):
        """加入方处理武器命中：不上报已无敌敌人，只发送伤害事件并处理子弹销毁"""
        if not enemy or not enemy.alive() or enemy.enemy_id is None:
            return
        
        # 敌人无敌时不造成伤害，但子弹仍按穿透逻辑处理
        if getattr(enemy, 'invincible', False):
            projectile.hit_count = getattr(projectile, 'hit_count', 0) + 1
            should_destroy = self._should_destroy_projectile(projectile)
            if should_destroy:
                projectile.kill()
            return
        
        # 发送伤害事件给主机
        damage = getattr(projectile, 'damage', 0)
        self._send_enemy_damage(enemy, damage)
        resource_manager.play_sound("hit")
        
        # 处理命中计数与穿透
        projectile.hit_count = getattr(projectile, 'hit_count', 0) + 1
        if self._should_destroy_projectile(projectile):
            projectile.kill()
    
    def _should_destroy_projectile(self, projectile):
        """判断投射物是否应该被销毁"""
        can_penetrate = getattr(projectile, 'can_penetrate', False)
        if not can_penetrate:
            return True
        max_penetration = getattr(projectile, 'max_penetration', 1)
        hit_count = getattr(projectile, 'hit_count', 0)
        if hit_count < max_penetration:
            # 每次穿透后降低伤害
            reduction = getattr(projectile, 'penetration_damage_reduction', 0)
            projectile.damage *= (1 - reduction)
            return False
        return True
    
    def _check_collisions(self):
        if not self.player or not self.enemy_manager:
            return
            
        for weapon in self.player.weapons:
            for projectile in weapon.get_projectiles():
                # 视觉模式（网络同步的特效副本）不参与碰撞和伤害
                if getattr(projectile, 'visual_only', False):
                    continue
                for enemy in self.enemy_manager.enemies:
                    dx = enemy.rect.x - projectile.world_x
                    dy = enemy.rect.y - projectile.world_y
                    distance = (dx**2 + dy**2)**0.5
                    
                    if distance < enemy.rect.width / 2 + projectile.rect.width / 2:
                        projectile_rect = projectile.rect.copy()
                        projectile_rect.centerx = projectile.world_x
                        projectile_rect.centery = projectile.world_y
                        
                        if apply_mask_collision(enemy, projectile):
                            # 加入方：不本地扣血，只上报伤害
                            if self.network_mode and not self.is_host:
                                self._handle_client_weapon_collision(projectile, enemy, weapon)
                            else:
                                # 主机/单机：本地处理伤害
                                should_destroy = weapon.handle_collision(projectile, enemy, self.enemy_manager.enemies)
                                resource_manager.play_sound("hit")
                                
                                if enemy.health <= 0:
                                    self.kill_num += 1
                                    self._broadcast_enemy_death(enemy)
                                    self.enemy_manager.remove_enemy(enemy)
                                    resource_manager.play_sound("enemy_death")
                                    
                                if should_destroy:
                                    projectile.kill()
        
        # 敌人碰撞玩家：仅单机或主机处理伤害；加入方通过主机同步的伤害事件扣血
        if not self.network_mode or self.is_host:
            players = [self.player]
            if self.network_mode and self.remote_player:
                players.append(self.remote_player)
            
            for player in players:
                self._handle_enemy_player_collision(player)
        else:
            self._process_player_damage_events()
        
    def _handle_enemy_player_collision(self, player):
        """处理敌人对单个玩家造成的伤害（单机或主机端）"""
        if getattr(player, 'invincible', False):
            return
        
        player_rect = player.rect.copy()
        player_rect.centerx = player.world_x
        player_rect.centery = player.world_y
        
        for enemy in self.enemy_manager.enemies:
            # 远程/特殊攻击（子弹等）
            if hasattr(enemy, 'projectiles'):
                enemy.attack_player(player)
                # 对远程玩家（镜像）做宽松的子弹命中补充检测，补偿网络同步延迟
                if self.network_mode and player is self.remote_player:
                    self._apply_loose_projectile_hits(enemy, player)
            
            # 近战碰撞
            if enemy.type == 'skt' and getattr(enemy, 'current_form', 1) == 1:
                continue
            
            if enemy.type == 'plant':
                continue
            
            # 远程玩家（镜像）使用矩形碰撞提高命中率，本地玩家使用精确遮罩
            if self.network_mode and player is self.remote_player:
                collided = player_rect.colliderect(enemy.rect)
            else:
                saved_rect = player.rect
                player.rect = player_rect
                collided = apply_mask_collision(player, enemy)
                player.rect = saved_rect
            if collided:
                damage_amount = enemy.damage * 0.5
                if player.take_damage(damage_amount):
                    resource_manager.play_sound("player_hurt")
                    
                    # 计算击退方向和距离
                    kb_dx, kb_dy, kb_dist = self._calc_knockback_vector(player, enemy)
                    
                    if player is self.player:
                        # 本地玩家直接击退
                        self._apply_knockback_vector(player, kb_dx, kb_dy, kb_dist)
                    elif self.network_mode and player is self.remote_player:
                        # 镜像玩家受伤，通知加入方并同步击退
                        self._send_player_damage(damage_amount, kb_dx, kb_dy, kb_dist)
                    break
    
    def _apply_loose_projectile_hits(self, enemy, player):
        """对远程玩家使用更宽松的敌人子弹命中判定，补偿网络延迟"""
        for projectile in list(enemy.projectiles):
            px = getattr(projectile, 'x', getattr(projectile, 'world_x', 0))
            py = getattr(projectile, 'y', getattr(projectile, 'world_y', 0))
            dx = px - player.world_x
            dy = py - player.world_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            # 宽松半径：玩家半宽 + 子弹半径 + 20 像素容差
            hit_radius = player.rect.width / 2 + getattr(projectile, 'radius', 8) + 20
            
            if distance < hit_radius:
                damage = getattr(projectile, 'damage', getattr(enemy, 'damage', 10))
                if player.take_damage(damage):
                    resource_manager.play_sound("player_hurt")
                    self._send_player_damage(damage, 0, 0, 0)
                projectile.kill()
                break
    
    def _calc_knockback_vector(self, player, enemy):
        """计算击退方向与距离
        
        Returns:
            tuple: (dx, dy, distance)
        """
        dx = player.world_x - enemy.rect.centerx
        dy = player.world_y - enemy.rect.centery
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > 0:
            dx /= distance
            dy /= distance
        return dx, dy, 50.0
    
    def _apply_knockback_vector(self, player, dx, dy, distance):
        """对指定玩家应用击退"""
        if distance <= 0:
            return
        player.world_x += dx * distance
        player.world_y += dy * distance
    
    def _send_player_damage(self, amount, knockback_dx=0.0, knockback_dy=0.0, knockback_distance=0.0):
        """主机通知加入方玩家受到伤害"""
        if not self.network_mode or not self.is_host:
            return
        net_client = get_network_client()
        net_client.send_player_damage(amount, "enemy", knockback_dx, knockback_dy, knockback_distance)
    
    def _process_player_damage_events(self):
        """加入方处理主机同步的玩家受伤事件"""
        if not self.network_mode or self.is_host or not self.player:
            return
        net_client = get_network_client()
        events = net_client.get_player_damage_events()
        for event in events:
            amount = event.get("amount", 0)
            if amount > 0 and self.player.take_damage(amount):
                resource_manager.play_sound("player_hurt")
                # 应用击退（take_damage 内部已设置无敌）
                kb_dx = event.get("knockback_dx", 0.0)
                kb_dy = event.get("knockback_dy", 0.0)
                kb_dist = event.get("knockback_distance", 0.0)
                self._apply_knockback_vector(self.player, kb_dx, kb_dy, kb_dist)
    
    def _update_game_state(self):
        current_level = int(self.game_time // 60) + 1
        
        if current_level > self.level:
            resource_manager.play_sound("level_up")
            
        self.level = current_level
        
        if self.enemy_manager:
            self.enemy_manager.difficulty_level = self.level
    
    def _knockback_player(self, enemy):
        if not self.player or not enemy:
            return
        
        dx = self.player.world_x - enemy.rect.centerx
        dy = self.player.world_y - enemy.rect.centery
        distance = (dx**2 + dy**2)**0.5
        
        if distance == 0:
            return
        
        dx = dx / distance
        dy = dy / distance
        
        knockback_distance = 50
        self.player.world_x += dx * knockback_distance
        self.player.world_y += dy * knockback_distance
