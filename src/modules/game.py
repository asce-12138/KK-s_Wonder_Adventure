# ============================================================
# 第一部分：模块导入
# 功能：导入所有游戏子系统模块，包括玩家、敌人、道具、UI、菜单、网络、武器等
# ============================================================
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
    """游戏主类，负责协调所有游戏子系统"""
    
    # ============================================================
    # 第二部分：游戏初始化 (__init__)
    # 功能：初始化游戏状态、创建所有子系统管理器、菜单实例、网络相关变量
    # 结构：状态标志 → 网络变量 → 资源初始化 → 管理器实例 → 菜单系统 → 统计数据
    # ============================================================
    def __init__(self, screen, network_mode=False, is_host=False, local_player_id=1, on_return_to_lobby=None):
        """初始化游戏实例
        
        Args:
            screen: Pygame屏幕表面
            network_mode: 是否为网络联机模式
            is_host: 是否为主机
            local_player_id: 本地玩家ID（1或2）
            on_return_to_lobby: 返回网络大厅的回调函数
        """
        # 2.1 游戏状态标志（状态机模式）
        self.screen = screen        # 游戏屏幕
        self.running = True         # 游戏运行状态
        self.paused = False         # 暂停状态
        self.game_over = False      # 游戏结束状态
        self.in_main_menu = True    # 是否在主菜单
        self.in_map_hero_select = False  # 是否在地图和角色选择界面
        
        # 2.2 网络模式相关变量
        self.network_mode = network_mode        # 是否为联机模式
        self.is_host = is_host                  # 是否为主机（主机负责怪物AI和碰撞判定）
        self.local_player_id = local_player_id  # 本地玩家编号（1或2）
        self.on_return_to_lobby = on_return_to_lobby  # 返回联机大厅的回调
        self.disconnect_message = None          # 断开连接提示消息
        self.network_sync_timer = 0             # 网络同步计时器
        self.network_sync_interval = 0.05       # 网络同步间隔（20Hz，高频同步玩家状态）
        
        # 2.3 怪物同步相关变量
        self.enemy_sync_timer = 0               # 怪物状态同步计时器
        self.enemy_sync_interval = 0.1          # 怪物状态同步间隔（10Hz，低频同步怪物）
        self.pending_dead_enemies = []          # 本帧死亡的敌人，用于主机广播
        
        # 2.4 敌人投射物视觉副本（客户端显示主机敌人子弹，不参与碰撞）
        self.visual_enemy_projectiles = pygame.sprite.Group()
        
        # 2.5 远程玩家相关变量
        self.remote_player = None              # 远程玩家实例（镜像）
        self.remote_player_data = None          # 远程玩家网络数据
        self.show_disconnect_popup = False     # 是否显示断开连接弹窗
        self.disconnect_popup_timer = 0        # 断开连接弹窗倒计时
        
        # 2.6 初始化资源管理器（加载所有图像、音频资源）
        resource_manager._init_resources()
        
        # 2.7 屏幕和相机相关
        self.screen_center_x = self.screen.get_width() // 2  # 屏幕中心点X坐标
        self.screen_center_y = self.screen.get_height() // 2  # 屏幕中心点Y坐标
        self.camera_x = 0  # 相机X坐标（跟随玩家）
        self.camera_y = 0  # 相机Y坐标（跟随玩家）
        
        # 2.8 网格相关（备用渲染，地图加载失败时显示）
        self.grid_size = 50    # 网格大小
        self.grid_color = (50, 50, 50)  # 网格颜色
        
        # 2.9 管理器实例（核心子系统）
        self.enemy_manager = None       # 敌人管理器（生成、更新、渲染敌人）
        self.item_manager = None        # 道具管理器（生成、更新、拾取道具）
        self.save_system = SaveSystem() # 存档系统（保存/读取游戏进度）
        self.upgrade_manager = UpgradeManager()  # 升级管理器（武器升级、被动升级）
        self.map_manager = MapManager(screen)    # 地图管理器（加载TMX地图、渲染地图）
        
        # 2.10 UI组件（游戏内HUD界面）
        self.ui = UI(screen)  # 血条、经验条、武器/被动图标、金币、时间、击杀数
        
        # 2.11 菜单系统（游戏流程控制）
        if self.network_mode:
            # 联机模式直接进入地图选择，不显示主菜单
            self.main_menu = None
            self.in_main_menu = False
            self.in_map_hero_select = True
        else:
            # 单机模式显示主菜单，包含联机模式选项
            extra_options = [{'text': '联机模式', 'action': 'multiplayer'}]
            self.main_menu = MainMenu(screen, extra_options=extra_options)
        
        # 创建各类菜单实例
        self.pause_menu = PauseMenu(screen)          # 暂停菜单（继续/存档/重新开始/退出）
        self.game_over_menu = GameOverMenu(screen)   # 游戏结束菜单（重新开始/主菜单/退出）
        self.victory_menu = GameOverMenu(screen, title="你过关")  # 胜利菜单（过关后显示）
        self.upgrade_menu = UpgradeMenu(screen)      # 升级菜单（玩家升级时选择升级项）
        self.save_menu = SaveMenu(screen, True)      # 存档菜单（保存当前进度）
        self.load_menu = SaveMenu(screen, False)     # 读档菜单（加载存档进度）
        
        # 地图和角色选择菜单（开始游戏前选择地图和角色）
        self.map_hero_select_menu = MapHeroSelectMenu(
            screen,
            on_start_game=self._start_game_with_selection,  # 开始游戏回调
            on_back=self._back_to_main_menu                 # 返回主菜单回调
        )
        
        # 2.12 游戏统计数据
        self.game_time = 0                     # 游戏时间（秒）
        self.kill_num = 0                      # 击杀数
        self.level = 1                         # 当前等级（每分钟提升一级）
        self.level_complete = False            # 是否过关
        self.victory_coin_threshold = 300      # 过关所需金币数
        
        # 2.13 当前地图名称（用于地图特定敌人生成）
        self.current_map = None
        
        # 2.14 弹窗字体（用于断开连接等提示）
        self.popup_font = FontManager.get_font(28)
        
        # 2.15 根据模式初始化
        if self.network_mode:
            self._setup_network()              # 设置网络回调
            self.map_hero_select_menu.show()   # 显示地图选择
        else:
            self._play_menu_music()            # 播放菜单背景音乐
        
    # ============================================================
    # 第三部分：网络通信相关方法
    # 功能：处理网络同步、事件分发、远程玩家状态更新、武器/敌人投射物特效同步
    # 架构：主机权威模式（主机负责AI和碰撞，加入方只发送输入和接收状态）
    # ============================================================
    
    def _setup_network(self):
        """设置网络回调，创建远程玩家镜像"""
        net_client = get_network_client()
        net_client.on_disconnected = self._on_network_disconnected  # 设置断开连接回调
        self.remote_player = RemotePlayer(hero_type="ninja_frog")    # 创建远程玩家镜像
        self.remote_player.player_name = f"玩家{2 if self.local_player_id == 1 else 1}"  # 设置玩家名
        # 设置不同颜色区分两个玩家
        if self.local_player_id == 1:
            self.remote_player.name_color = (0, 255, 255)   # 玩家2为青色
        else:
            self.remote_player.name_color = (255, 200, 0)  # 玩家1为金色
        
        self._play_game_music()  # 播放游戏背景音乐
    
    def _on_network_disconnected(self):
        """网络断开回调：显示断开连接弹窗，2秒后返回大厅"""
        self.disconnect_message = "连接已断开，正在返回联机大厅..."
        self.show_disconnect_popup = True
        self.disconnect_popup_timer = 2.0  # 2秒倒计时
    
    def _return_to_lobby(self):
        """返回联机大厅：调用回调函数，传递断开连接消息"""
        if self.on_return_to_lobby:
            msg = self.disconnect_message if self.disconnect_message else None
            self.on_return_to_lobby(msg)
    
    def _on_item_collected(self, item_id, item_type):
        """掉落物被拾取时的回调：通知主机移除道具"""
        if not self.network_mode or not item_id:
            return
        net_client = get_network_client()
        net_client.send_item_pickup(item_id)
    
    def _process_network_enemy_sync(self):
        """处理怪物全量同步数据（仅加入方）：从主机获取所有怪物状态并同步"""
        if self.is_host:
            return
        net_client = get_network_client()
        sync_data = net_client.get_enemy_sync_data()
        if sync_data and self.enemy_manager:
            enemy_states = sync_data.get("enemies", [])
            self.enemy_manager.apply_enemy_sync(enemy_states)  # 更新本地怪物状态
    
    def _process_network_enemy_events(self):
        """处理怪物事件（主机/加入方职责分离）：
        - 主机：处理加入方上报的伤害事件
        - 加入方：处理主机广播的生成/死亡事件"""
        if not self.network_mode:
            return
        net_client = get_network_client()
        events = net_client.get_enemy_events()
        for event in events:
            msg_type = event.get("type")
            if msg_type == "enemy_damage":
                # 只有主机处理伤害事件（主机权威）
                if self.is_host and self.enemy_manager:
                    enemy_id = event.get("enemy_id")
                    damage = event.get("damage", 0)
                    self.enemy_manager.apply_damage_event(enemy_id, damage)
            elif msg_type == "enemy_death":
                # 加入方处理死亡事件（主机已判定死亡）
                if not self.is_host and self.enemy_manager:
                    enemy_id = event.get("enemy_id")
                    self.enemy_manager.remove_enemy_by_id(enemy_id)
            elif msg_type == "enemy_spawn":
                # 加入方处理生成事件（主机已生成）
                if not self.is_host and self.enemy_manager:
                    state = event.copy()
                    state.pop("type", None)
                    state.pop("timestamp", None)
                    self.enemy_manager.spawn_enemy_from_network(state)
    
    def _process_network_item_events(self):
        """处理掉落物事件：生成/移除/拾取同步"""
        if not self.network_mode:
            return
        net_client = get_network_client()
        events = net_client.get_item_events()
        for event in events:
            msg_type = event.get("type")
            if msg_type == "item_spawn":
                # 加入方生成主机广播的道具
                item_id = event.get("item_id")
                item_type = event.get("item_type")
                x = event.get("x")
                y = event.get("y")
                if item_id and item_type and x is not None and y is not None and self.item_manager:
                    self.item_manager.spawn_network_item(item_id, item_type, x, y)
            elif msg_type == "item_remove":
                # 移除道具（主机广播）
                item_id = event.get("item_id")
                if item_id and self.item_manager:
                    self.item_manager.remove_item_by_id(item_id)
            elif msg_type == "item_pickup":
                # 主机收到拾取事件，广播移除给所有客户端
                if self.is_host:
                    item_id = event.get("item_id")
                    if item_id and self.item_manager:
                        self.item_manager.remove_item_by_id(item_id)
                        net_client.send_item_remove(item_id)
    
    def _broadcast_enemy_death(self, enemy):
        """处理怪物死亡：
        - 单机模式：直接生成掉落物
        - 网络主机：广播死亡事件和掉落物信息
        - 加入方：不处理（等待主机广播）"""
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
        """加入方上报怪物伤害给主机（主机权威判定）"""
        if not self.network_mode or self.is_host:
            return
        if enemy.enemy_id is None:
            return
        net_client = get_network_client()
        net_client.send_enemy_damage(enemy.enemy_id, damage)
    
    def _on_projectile_created(self, weapon_type, projectile):
        """本地玩家创建投射物时的回调：发送网络特效事件给远程玩家"""
        if not self.network_mode:
            return
        self._send_weapon_attack_event(weapon_type, projectile)
    
    def _send_weapon_attack_event(self, weapon_type, projectile):
        """发送武器攻击特效事件：包含武器类型、位置、方向、等级、是否巨型"""
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
        
        # 对于 FrostNova 的额外冰锥，使用原始方向（而非追踪方向）
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
        """处理接收到的武器特效事件：为远程玩家创建视觉投射物"""
        if not self.network_mode or not self.remote_player:
            return
        net_client = get_network_client()
        events = net_client.get_weapon_attack_events()
        for event in events:
            self._create_visual_projectile(event)
    
    def _create_visual_projectile(self, event):
        """根据网络事件创建视觉投射物（仅显示，不参与碰撞）：
        - 使用远程玩家当前位置避免网络延迟导致位置偏差
        - 支持三种武器类型：飞刀、火球、霜冻新星
        - 设置visual_only=True标记为纯视觉模式"""
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
                # 创建虚拟目标用于冰锥发射
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
            projectile.visual_only = True  # 标记为纯视觉模式，不参与碰撞检测
            # 设置特效组，使爆炸特效能在远程玩家处渲染
            projectile.effects_group = self.remote_player.visual_effects
            self.remote_player.add_visual_projectile(projectile)
    
    def _broadcast_enemy_projectiles(self):
        """主机广播新创建的敌人投射物事件：加入方收到后创建视觉副本"""
        if not self.network_mode or not self.is_host or not self.enemy_manager:
            return
        events = self.enemy_manager.collect_new_projectile_events()
        if not events:
            return
        net_client = get_network_client()
        for event in events:
            net_client.send_enemy_projectile(event)
    
    def _process_enemy_projectile_events(self):
        """客户端处理敌人投射物事件（仅加入方）：创建视觉副本显示主机敌人子弹"""
        if not self.network_mode or self.is_host:
            return
        net_client = get_network_client()
        events = net_client.get_enemy_projectile_events()
        for event in events:
            self._create_visual_enemy_projectile(event)
    
    def _create_visual_enemy_projectile(self, event):
        """根据网络事件创建敌人投射物的视觉副本：使用VisualEnemyProjectile类"""
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
        
    # ============================================================
    # 第四部分：游戏流程控制方法
    # 功能：处理游戏开始、地图加载、存档读取、返回主菜单等游戏流程
    # ============================================================
    
    def _set_map_boundaries(self):
        """设置地图边界：限制玩家和敌人在地图范围内活动（留出64像素围栏空间）"""
        if not self.current_map:
            return
            
        map_width, map_height = self.map_manager.get_map_size()
        
        fence_width = 2 * 32  # 留出2个图块作为边界围栏
        
        min_x = fence_width
        min_y = fence_width
        max_x = map_width - fence_width
        max_y = map_height - fence_width
        
        if self.player:
            self.player.movement.set_boundaries(min_x, min_y, max_x, max_y)  # 设置玩家移动边界
            
        if self.enemy_manager:
            self.enemy_manager.set_map_boundaries(min_x, min_y, max_x, max_y)  # 设置敌人生成边界
            self.enemy_manager.set_current_map(self.current_map)               # 设置当前地图（用于地图特定敌人生成）
            
    def _set_player_boundaries(self):
        """设置玩家边界（调用_set_map_boundaries）"""
        self._set_map_boundaries()
        
    def _start_game_with_selection(self, map_id, hero_id):
        """开始新游戏（地图和角色选择后的回调）：
        - 初始化玩家、敌人管理器、道具管理器
        - 设置网络权威端
        - 重置游戏状态
        - 播放地图背景音乐"""
        self.in_map_hero_select = False  # 退出地图选择界面
        self.game_over = False           # 重置游戏结束状态
        self.paused = False              # 重置暂停状态
        
        self.load_map(map_id)  # 加载选择的地图
        
        map_width, map_height = self.map_manager.get_map_size()
        
        # 创建玩家实例（传入角色类型）
        self.player = Player(self.screen_center_x, self.screen_center_y, hero_id)
        
        # 将玩家放置在地图中心
        self.player.world_x = map_width // 2
        self.player.world_y = map_height // 2
        
        # 联机模式下玩家2从偏移位置开始（避免重叠）
        if self.network_mode and self.local_player_id == 2:
            self.player.world_x = map_width // 2 + 100
            self.player.world_y = map_height // 2 + 100
        
        # 创建敌人管理器并设置难度
        self.enemy_manager = EnemyManager()
        self.enemy_manager.set_difficulty("normal")
        
        # 创建道具管理器并设置拾取回调
        self.item_manager = ItemManager()
        self.item_manager.on_collect_callback = self._on_item_collected
        
        # 网络模式下只有主机是权威端（负责怪物AI和碰撞判定）
        if self.network_mode:
            self.enemy_manager.authoritative = self.is_host
            self.item_manager.authoritative = self.is_host
        
        # 设置武器投射物创建回调，用于网络特效同步
        if self.player and self.player.weapon_manager:
            self.player.weapon_manager.on_projectile_created = self._on_projectile_created
        
        # 设置地图边界
        self._set_map_boundaries()
        
        # 重置游戏统计数据
        self.game_time = 0
        self.kill_num = 0
        self.level = 1
        self.level_complete = False
        
        # 相机跟随玩家
        self.camera_x = self.player.world_x
        self.camera_y = self.player.world_y
        
        # 播放地图特定背景音乐
        resource_manager.play_map_music(map_id, loops=-1)
        
        # 联机模式下同步远程玩家初始位置
        if self.network_mode and self.remote_player:
            self.remote_player.world_x = self.player.world_x + 80
            self.remote_player.world_y = self.player.world_y
        
    def _back_to_main_menu(self):
        """返回主菜单：单机模式返回主菜单，联机模式返回大厅"""
        if self.network_mode:
            self._return_to_lobby()
            return
        self.in_map_hero_select = False
        self.in_main_menu = True
        self._play_menu_music()  # 播放菜单背景音乐
        
    def _play_menu_music(self):
        """播放菜单背景音乐"""
        resource_manager.play_music("menu", loops=-1)
        
    def _play_game_music(self):
        """播放游戏背景音乐"""
        resource_manager.play_music("background", loops=-1)
        
    def start_new_game(self):
        """开始新游戏：退出主菜单，进入地图和角色选择界面"""
        self.in_main_menu = False
        self.in_map_hero_select = True
        self.map_hero_select_menu.show()
            
    def load_map(self, map_name):
        """加载地图：通过map_manager加载TMX地图文件，设置当前地图名称和边界"""
        success = self.map_manager.load_map(map_name)
        if success:
            self.current_map = map_name
            
            map_width, map_height = self.map_manager.get_map_size()
            
            if self.player:
                # 将玩家移动到地图中心
                self.player.world_x = map_width // 2
                self.player.world_y = map_height // 2
                
                # 相机跟随玩家
                self.camera_x = self.player.world_x
                self.camera_y = self.player.world_y
                
                # 设置地图边界
                self._set_map_boundaries()
            
        else:
            print(f"加载地图 '{map_name}' 失败")
            
        return success

    # ============================================================
    # 第五部分：存档加载方法
    # 功能：从存档数据恢复游戏状态，包括玩家属性、武器、被动、敌人、游戏时间等
    # 结构：状态重置 → 玩家数据恢复 → 组件状态恢复 → 武器数据恢复 → 游戏数据恢复 → 敌人数据恢复
    # ============================================================
    
    def load_game_state(self, save_data):
        """从存档数据加载游戏状态
        
        Args:
            save_data: 存档字典，包含玩家数据、游戏数据、敌人数据等
            
        Returns:
            bool: 加载成功返回True，失败返回False并启动新游戏
        """
        try:
            # 5.1 重置游戏状态标志
            self.in_main_menu = False
            self.game_over = False
            self.paused = False
            
            # 5.2 恢复玩家基础数据
            player_data = save_data.get('player_data', {})
            if not player_data:
                print("存档数据损坏：缺少玩家数据")
                return False
                
            hero_type = player_data.get('hero_type', 'ninja_frog')
            self.player = Player(self.screen_center_x, self.screen_center_y, hero_type)
            
            # 恢复玩家核心属性
            self.player.health = player_data.get('health', self.player.health)
            self.player.health_component.max_health = player_data.get('max_health', self.player.health_component.max_health)
            self.player.progression.level = player_data.get('level', self.player.progression.level)
            self.player.progression.experience = player_data.get('experience', 0)
            self.player.progression.coins = player_data.get('coins', 0)
            self.player.world_x = player_data.get('world_x', self.screen_center_x)
            self.player.world_y = player_data.get('world_y', self.screen_center_y)
            
            # 5.3 恢复玩家组件状态（移动、生命值、进度、被动）
            component_states = player_data.get('component_states', {})
            if component_states:
                # 5.3.1 移动组件状态恢复
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
                
                # 5.3.2 生命值组件状态恢复（防御、回血）
                health_states = component_states.get('health', {})
                if health_states:
                    self.player.health_component.defense = health_states.get('defense', self.player.health_component.defense)
                    self.player.health_component.health_regen = health_states.get('health_regen', self.player.health_component.health_regen)
                
                # 5.3.3 进度组件状态恢复（经验倍率、幸运值）
                progression_states = component_states.get('progression', {})
                if progression_states:
                    self.player.progression.exp_multiplier = progression_states.get('exp_multiplier', self.player.progression.exp_multiplier)
                    self.player.progression.luck = progression_states.get('luck', self.player.progression.luck)
                
                # 5.3.4 被动技能状态恢复
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
            
            # 5.4 恢复武器数据（先清空现有武器，再加载存档武器）
            weapons_data = player_data.get('weapons', [])
            if weapons_data:
                for weapon in list(self.player.weapons):
                    self.player.weapon_manager.remove_weapon(weapon.type)
                
                for weapon_type, level in weapons_data:
                    weapon = self.player.add_weapon(weapon_type)
                    if weapon:
                        weapon.level = level
            
            # 5.5 重建管理器实例
            self.enemy_manager = EnemyManager()
            self.item_manager = ItemManager()
            
            # 5.6 恢复游戏全局数据
            game_data = save_data.get('game_data', {})
            self.game_time = game_data.get('game_time', 0)
            self.kill_num = game_data.get('kill_num', 0)
            self.level = game_data.get('level', 1)
            
            # 5.7 设置敌人管理器难度（根据存档等级重新计算）
            self.enemy_manager.difficulty_level = self.level
            self.enemy_manager.set_difficulty(game_data.get('difficulty', 'normal'))
            self.enemy_manager.game_time = self.game_time
            self.enemy_manager.recalculate_difficulty()
            
            # 5.8 恢复敌人数据（按存档状态重新生成敌人）
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
            
            # 5.9 恢复相机位置和地图边界
            self.camera_x = self.player.world_x
            self.camera_y = self.player.world_y
            self._set_map_boundaries()
            
            # 5.10 播放背景音乐
            resource_manager.play_music("background", loops=-1)
            
            return True
            
        except Exception as e:
            # 加载失败时启动新游戏
            print(f"加载存档时出错: {e}")
            self.start_new_game()
            return False
        
    # ============================================================
    # 第六部分：事件处理方法
    # 功能：处理所有用户输入事件（键盘、鼠标），根据当前游戏状态分发到对应菜单或玩家
    # 架构：状态机模式，按优先级顺序处理各状态的事件
    # ============================================================
    
    def handle_event(self, event):
        """处理Pygame事件
        
        事件处理优先级：
        1. 断开连接弹窗（最高优先级，阻断其他操作）
        2. 地图和角色选择界面
        3. 主菜单界面（含读档子菜单）
        4. 读档菜单
        5. 存档菜单
        6. 过关状态菜单
        7. 游戏结束菜单
        8. 暂停菜单
        9. 升级菜单
        10. 全局快捷键（ESC暂停、F2显示轮廓）
        11. 玩家输入事件
        
        Args:
            event: Pygame事件对象
            
        Returns:
            bool: 是否处理了事件
        """
        # 6.1 断开连接弹窗（最高优先级，阻断所有其他操作）
        if self.show_disconnect_popup:
            return
        
        # 6.2 地图和角色选择界面
        if self.in_map_hero_select:
            result = self.map_hero_select_menu.handle_event(event)
            return
            
        # 6.3 主菜单界面（含读档子菜单）
        if self.in_main_menu:
            # 6.3.1 读档子菜单优先处理
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
            
            # 6.3.2 主菜单操作
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
            
        # 6.4 读档菜单（游戏中打开）
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
            
        # 6.5 存档菜单
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
            
        # 6.6 过关状态菜单
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
            
        # 6.7 游戏结束菜单
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
            
        # 6.8 暂停菜单
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
               
        # 6.9 升级菜单（玩家升级时弹出）
        if self.upgrade_menu.is_active:
            selected_upgrade = self.upgrade_menu.handle_event(event)
            if selected_upgrade:
                self._apply_upgrade(selected_upgrade)
                self.upgrade_menu.hide()
            return True
            
        # 6.10 全局快捷键
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.toggle_pause()
                return True
            elif event.key == pygame.K_F2:
                # F2显示/隐藏玩家和敌人轮廓（调试用）
                if self.player:
                    self.player.toggle_outline()
                    for enemy in self.enemy_manager.enemies:
                        enemy.toggle_outline()
                return True
            
        # 6.11 玩家输入事件（移动、攻击等）
        if self.player:
            self.player.handle_event(event)
            
        return True
        
    # ============================================================
    # 第七部分：升级系统方法
    # 功能：应用玩家升级选择的武器或被动技能升级效果
    # ============================================================
    
    def _apply_upgrade(self, upgrade_level):
        """应用升级效果到玩家
        
        根据升级类型（武器升级或被动升级），将升级效果应用到玩家对象上。
        对于武器升级，如果玩家尚未拥有该武器，则自动添加。
        
        Args:
            upgrade_level: 升级等级对象（WeaponUpgradeLevel 或 PassiveUpgradeLevel）
        """
        # 7.1 武器升级处理
        if isinstance(upgrade_level, WeaponUpgradeLevel):
            weapon_type = None
            # 通过遍历升级管理器找到对应的武器类型
            for type_, upgrade in self.upgrade_manager.weapon_upgrades.items():
                if upgrade_level in upgrade.levels:
                    weapon_type = type_
                    break
                    
            if weapon_type:
                # 应用武器升级效果
                if self.player.apply_weapon_upgrade(weapon_type, upgrade_level.level, upgrade_level.effects):
                    # 如果玩家尚未拥有该武器，自动添加
                    if len([w for w in self.player.weapons if w.type == weapon_type]) == 0:
                        self.player.add_weapon(weapon_type)
                        
        # 7.2 被动技能升级处理
        elif isinstance(upgrade_level, PassiveUpgradeLevel):
            passive_type = None
            # 通过遍历升级管理器找到对应的被动类型
            for type_, upgrade in self.upgrade_manager.passive_upgrades.items():
                if upgrade_level in upgrade.levels:
                    passive_type = type_
                    break
                    
            if passive_type:
                # 应用被动升级效果
                self.player.apply_passive_upgrade(passive_type, upgrade_level.level, upgrade_level.effects)
                
    # ============================================================
    # 第八部分：暂停控制方法
    # 功能：切换游戏暂停状态，控制菜单显示和背景音乐暂停
    # ============================================================
    
    def toggle_pause(self):
        """切换游戏暂停状态
        
        - 暂停时：显示暂停菜单，暂停背景音乐
        - 恢复时：隐藏暂停菜单，恢复背景音乐
        """
        self.paused = not self.paused
        if self.paused:
            self.pause_menu.show()
            resource_manager.pause_music()
        else:
            self.pause_menu.hide()
            resource_manager.unpause_music()
        
    # ============================================================
    # 第九部分：游戏更新循环
    # 功能：每帧更新游戏状态，包括网络同步、玩家/敌人更新、碰撞检测、进度检查
    # 架构：状态检查 → 网络更新 → 游戏逻辑更新 → 碰撞检测 → 升级检查
    # ============================================================
    
    def update(self, dt):
        """每帧更新游戏状态
        
        Args:
            dt: 时间增量（秒），用于帧速率无关的更新
        """
        # 9.1 断开连接弹窗处理（阻断其他更新）
        if self.show_disconnect_popup:
            self.disconnect_popup_timer -= dt
            if self.disconnect_popup_timer <= 0:
                self._return_to_lobby()
            return
        
        # 9.2 主菜单和地图选择界面不进行游戏逻辑更新
        if self.in_main_menu:
            return
            
        if self.in_map_hero_select:
            return
            
        # 9.3 网络模式更新（连接检测、远程玩家同步、本地玩家状态发送）
        if self.network_mode:
            net_client = get_network_client()
            
            # 9.3.1 连接状态检测
            if not net_client.is_connected():
                if not self.show_disconnect_popup:
                    self.disconnect_message = "网络连接已中断"
                    self.show_disconnect_popup = True
                    self.disconnect_popup_timer = 2.0
                return
            
            # 9.3.2 远程玩家状态同步（从主机/加入方接收）
            remote_data = net_client.get_remote_player_data()
            if remote_data:
                self.remote_player_data = remote_data
                if self.remote_player:
                    self.remote_player.update_from_network(remote_data)
            
            # 9.3.3 本地玩家状态发送（20Hz高频同步）
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
            
        # 9.4 游戏结束判定（玩家生命值归零）
        if self.player and self.player.health <= 0 and not self.game_over:
            self.game_over = True
            self.game_over_menu.show()
            resource_manager.play_sound("player_death")
            return
        
        # 9.5 过关判定（金币达到目标数量）
        if (self.player and self.player.coins >= self.victory_coin_threshold
                and not self.level_complete and not self.game_over):
            self.level_complete = True
            self.victory_menu.show()
            resource_manager.play_sound("level_up")
            return
            
        # 9.6 过关和游戏结束状态只更新菜单
        if self.level_complete:
            self.victory_menu.update(pygame.mouse.get_pos())
            return
            
        if self.game_over:
            self.game_over_menu.update(pygame.mouse.get_pos())
            return
            
        # 9.7 暂停/升级/存档状态不更新游戏逻辑
        if self.paused or self.upgrade_menu.is_active or self.save_menu.is_active:
            return
            
        # 9.8 更新游戏时间
        self.game_time += dt
        
        # 9.9 更新玩家状态和相机位置
        if self.player:
            self.player.update(dt)
            self.camera_x = self.player.world_x
            self.camera_y = self.player.world_y
        
        # 9.10 更新远程玩家（联机模式）
        if self.network_mode and self.remote_player:
            self.remote_player.update(dt)
        
        # 9.11 处理网络同步事件（敌人、道具、武器特效、敌人投射物）
        if self.network_mode:
            self._process_network_enemy_events()
            self._process_network_item_events()
            self._process_weapon_attack_events()
            self._process_enemy_projectile_events()
        
        # 9.12 敌人和道具更新
        if self.enemy_manager and self.player:
            # 9.12.1 主机/单机 vs 加入方分支
            if self.network_mode and not self.is_host:
                # 加入方：只应用主机同步的怪物状态，不运行AI
                self._process_network_enemy_sync()
                self.player.update_weapons(dt, self.enemy_manager.enemies)
            else:
                # 主机/单机：运行完整的怪物AI
                remote_player = self.remote_player if self.network_mode else None
                dead_enemies = self.enemy_manager.update(dt, self.player, remote_player)
                
                # 处理自然死亡（燃烧等持续伤害）的怪物
                for enemy in dead_enemies:
                    self.kill_num += 1
                    self._broadcast_enemy_death(enemy)
                
                # 主机广播新创建的敌人投射物
                if self.network_mode and self.is_host:
                    self._broadcast_enemy_projectiles()
                
                # 主机定时广播怪物全量状态（10Hz低频同步）
                if self.network_mode and self.is_host:
                    self.enemy_sync_timer += dt
                    if self.enemy_sync_timer >= self.enemy_sync_interval:
                        self.enemy_sync_timer = 0
                        net_client = get_network_client()
                        net_client.send_enemy_sync(self.enemy_manager.get_all_network_states())
                
                self.player.update_weapons(dt, self.enemy_manager.enemies)
            
            # 9.12.2 更新道具管理器
            if self.item_manager:
                self.item_manager.update(dt, self.player)
            
            # 9.12.3 碰撞检测
            self._check_collisions()
        
        # 9.13 更新敌人投射物视觉副本（客户端显示主机敌人子弹）
        self.visual_enemy_projectiles.update(dt)
        for projectile in list(self.visual_enemy_projectiles):
            if not projectile.alive():
                self.visual_enemy_projectiles.remove(projectile)
        
        # 9.14 检查玩家升级（经验值满时显示升级菜单）
        if self.player and self.player.add_experience(0):
            self.player.level_up()
            self.upgrade_menu.show(self.player, self)
        
    # ============================================================
    # 第十部分：游戏渲染方法
    # 功能：按层级渲染所有游戏元素，包括地图、敌人、道具、玩家、UI、菜单等
    # 渲染顺序：背景 → 地图 → 敌人 → 道具 → 远程玩家 → 本地玩家 → UI → 菜单 → 弹窗
    # ============================================================
    
    def render(self):
        """渲染所有游戏元素到屏幕
        
        渲染层级（从后到前）：
        1. 背景填充（黑色）
        2. 地图（或备用网格）
        3. 敌人
        4. 敌人投射物视觉副本（客户端）
        5. 道具
        6. 远程玩家（联机模式）
        7. 本地玩家
        8. HUD UI（血条、经验条等）
        9. 菜单（暂停、存档、升级、过关、游戏结束）
        10. 断开连接弹窗（最顶层）
        """
        # 10.1 清空屏幕（黑色背景）
        self.screen.fill((0, 0, 0))
        
        # 10.2 主菜单渲染（独立分支）
        if self.in_main_menu:
            if self.load_menu.is_active:
                self.load_menu.render()
            else:
                self.main_menu.render()
            pygame.display.flip()
            return
            
        # 10.3 地图和角色选择界面渲染
        if self.in_map_hero_select:
            self.map_hero_select_menu.render()
            pygame.display.flip()
            return
            
        # 10.4 存档菜单渲染（覆盖在游戏画面上）
        if self.save_menu.is_active:
            self.save_menu.render()
            return
            
        # 10.5 地图渲染（或备用网格，地图加载失败时显示）
        if self.current_map:
            self.map_manager.render(self.camera_x, self.camera_y)
        else:
            self._draw_grid()
        
        # 10.6 敌人渲染
        if self.enemy_manager:
            self.enemy_manager.render(self.screen, self.camera_x, self.camera_y, 
                                   self.screen_center_x, self.screen_center_y)
        
        # 10.7 敌人投射物视觉副本渲染（客户端显示主机敌人子弹）
        for projectile in self.visual_enemy_projectiles:
            if hasattr(projectile, 'render'):
                projectile.render(self.screen, self.camera_x, self.camera_y)
        
        # 10.8 道具渲染
        if self.item_manager:
            self.item_manager.render(self.screen, self.camera_x, self.camera_y, 
                                  self.screen_center_x, self.screen_center_y)
        
        # 10.9 远程玩家渲染（联机模式，在本地玩家之后渲染）
        if self.network_mode and self.remote_player:
            self.remote_player.render(self.screen, self.camera_x, self.camera_y,
                                     self.screen_center_x, self.screen_center_y)
        
        # 10.10 本地玩家和UI渲染
        if self.player:
            self.player.render(self.screen)
            self.player.render_weapons(self.screen, self.camera_x, self.camera_y)
            self.ui.render(self.player, self.game_time, self.kill_num)
            
        # 10.11 覆盖层菜单渲染（暂停、存档、升级、过关、游戏结束）
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
        
        # 10.12 断开连接弹窗（最顶层）
        if self.show_disconnect_popup:
            self._render_disconnect_popup()
            
        # 10.13 刷新屏幕显示
        pygame.display.flip()
    
    def _render_disconnect_popup(self):
        """渲染网络断开连接弹窗
        
        效果：半透明黑色遮罩 + 红色边框弹窗 + 断开连接提示文字
        """
        # 创建半透明遮罩
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # 计算弹窗位置（屏幕中央）
        popup_width = 500
        popup_height = 150
        popup_x = (self.screen.get_width() - popup_width) // 2
        popup_y = (self.screen.get_height() - popup_height) // 2
        
        # 绘制弹窗背景和边框
        pygame.draw.rect(self.screen, (60, 30, 30), (popup_x, popup_y, popup_width, popup_height), border_radius=15)
        pygame.draw.rect(self.screen, (200, 80, 80), (popup_x, popup_y, popup_width, popup_height), 3, border_radius=15)
        
        # 绘制提示文字
        if self.disconnect_message:
            text = self.popup_font.render(self.disconnect_message, True, (255, 100, 100))
        else:
            text = self.popup_font.render("连接已断开，正在返回大厅...", True, (255, 100, 100))
        text_rect = text.get_rect(center=(self.screen.get_width() // 2, popup_y + popup_height // 2))
        self.screen.blit(text, text_rect)
        
    def _draw_grid(self):
        """绘制备用网格（地图加载失败时显示）
        
        网格跟随相机移动，提供坐标参考
        """
        offset_x = (self.camera_x % self.grid_size)
        offset_y = (self.camera_y % self.grid_size)
        
        # 绘制垂直线
        for i in range(int(self.screen.get_width() / self.grid_size) + 2):
            x = i * self.grid_size - offset_x
            pygame.draw.line(self.screen, self.grid_color, (x, 0), (x, self.screen.get_height()))
            
        # 绘制水平线
        for i in range(int(self.screen.get_height() / self.grid_size) + 2):
            y = i * self.grid_size - offset_y
            pygame.draw.line(self.screen, self.grid_color, (0, y), (self.screen.get_width(), y))
        
    # ============================================================
    # 第十一部分：碰撞检测方法
    # 功能：处理玩家武器与敌人的碰撞、敌人与玩家的碰撞、击退计算与同步
    # 架构：武器投射物碰撞 → 敌人玩家碰撞 → 击退系统 → 网络同步
    # ============================================================
    
    def _handle_client_weapon_collision(self, projectile, enemy, weapon):
        """加入方处理武器命中：不上报已无敌敌人，只发送伤害事件并处理子弹销毁
        
        Args:
            projectile: 投射物对象
            enemy: 敌人对象
            weapon: 武器对象
        """
        # 无效敌人（已死亡或无ID）跳过
        if not enemy or not enemy.alive() or enemy.enemy_id is None:
            return
        
        # 敌人无敌时不造成伤害，但子弹仍按穿透逻辑处理
        if getattr(enemy, 'invincible', False):
            projectile.hit_count = getattr(projectile, 'hit_count', 0) + 1
            should_destroy = self._should_destroy_projectile(projectile)
            if should_destroy:
                projectile.kill()
            return
        
        # 发送伤害事件给主机（主机权威判定）
        damage = getattr(projectile, 'damage', 0)
        self._send_enemy_damage(enemy, damage)
        resource_manager.play_sound("hit")
        
        # 处理命中计数与穿透逻辑
        projectile.hit_count = getattr(projectile, 'hit_count', 0) + 1
        if self._should_destroy_projectile(projectile):
            projectile.kill()
    
    def _should_destroy_projectile(self, projectile):
        """判断投射物是否应该被销毁
        
        根据投射物的穿透属性决定是否销毁：
        - 不可穿透：命中即销毁
        - 可穿透：未达到最大穿透次数时保留，每次穿透降低伤害
        
        Args:
            projectile: 投射物对象
            
        Returns:
            bool: 是否应该销毁
        """
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
        """主碰撞检测方法
        
        处理两类碰撞：
        1. 玩家武器投射物与敌人的碰撞
        2. 敌人与玩家的碰撞（近战+远程子弹）
        
        网络模式下职责分离：
        - 主机：本地处理所有碰撞和伤害
        - 加入方：武器碰撞只上报伤害，玩家受伤通过主机同步
        """
        if not self.player or not self.enemy_manager:
            return
            
        # 11.1 玩家武器投射物与敌人碰撞
        for weapon in self.player.weapons:
            for projectile in weapon.get_projectiles():
                # 视觉模式（网络同步的特效副本）不参与碰撞和伤害
                if getattr(projectile, 'visual_only', False):
                    continue
                
                for enemy in self.enemy_manager.enemies:
                    # 快速距离检测（圆形包围盒）
                    dx = enemy.rect.x - projectile.world_x
                    dy = enemy.rect.y - projectile.world_y
                    distance = (dx**2 + dy**2)**0.5
                    
                    if distance < enemy.rect.width / 2 + projectile.rect.width / 2:
                        # 精确遮罩碰撞检测
                        projectile_rect = projectile.rect.copy()
                        projectile_rect.centerx = projectile.world_x
                        projectile_rect.centery = projectile.world_y
                        
                        if apply_mask_collision(enemy, projectile):
                            # 加入方：不本地扣血，只上报伤害给主机
                            if self.network_mode and not self.is_host:
                                self._handle_client_weapon_collision(projectile, enemy, weapon)
                            else:
                                # 主机/单机：本地处理伤害
                                should_destroy = weapon.handle_collision(projectile, enemy, self.enemy_manager.enemies)
                                resource_manager.play_sound("hit")
                                
                                # 处理敌人死亡
                                if enemy.health <= 0:
                                    self.kill_num += 1
                                    self._broadcast_enemy_death(enemy)
                                    self.enemy_manager.remove_enemy(enemy)
                                    resource_manager.play_sound("enemy_death")
                                    
                                # 销毁投射物
                                if should_destroy:
                                    projectile.kill()
        
        # 11.2 敌人与玩家碰撞（近战+远程子弹）
        # 仅单机或主机处理伤害；加入方通过主机同步的伤害事件扣血
        if not self.network_mode or self.is_host:
            players = [self.player]
            if self.network_mode and self.remote_player:
                players.append(self.remote_player)
            
            for player in players:
                self._handle_enemy_player_collision(player)
        else:
            self._process_player_damage_events()
        
    def _handle_enemy_player_collision(self, player):
        """处理敌人对单个玩家造成的伤害（单机或主机端）
        
        处理两类攻击：
        1. 远程攻击（敌人子弹）
        2. 近战碰撞
        
        对远程玩家（镜像）使用更宽松的碰撞判定补偿网络延迟。
        
        Args:
            player: 玩家对象（本地玩家或远程玩家镜像）
        """
        # 无敌玩家跳过
        if getattr(player, 'invincible', False):
            return
        
        # 创建玩家碰撞矩形（基于世界坐标）
        player_rect = player.rect.copy()
        player_rect.centerx = player.world_x
        player_rect.centery = player.world_y
        
        for enemy in self.enemy_manager.enemies:
            # 11.2.1 远程/特殊攻击（子弹等）
            if hasattr(enemy, 'projectiles'):
                enemy.attack_player(player)
                # 对远程玩家（镜像）做宽松的子弹命中补充检测，补偿网络同步延迟
                if self.network_mode and player is self.remote_player:
                    self._apply_loose_projectile_hits(enemy, player)
            
            # 11.2.2 近战碰撞排除特定敌人类型
            # skt怪物第一形态不参与近战碰撞
            if enemy.type == 'skt' and getattr(enemy, 'current_form', 1) == 1:
                continue
            # plant怪物不参与近战碰撞（只有远程攻击）
            if enemy.type == 'plant':
                continue
            
            # 11.2.3 近战碰撞检测
            # 远程玩家（镜像）使用矩形碰撞提高命中率，本地玩家使用精确遮罩
            if self.network_mode and player is self.remote_player:
                collided = player_rect.colliderect(enemy.rect)
            else:
                saved_rect = player.rect
                player.rect = player_rect
                collided = apply_mask_collision(player, enemy)
                player.rect = saved_rect
                
            if collided:
                # 近战伤害为敌人伤害的50%
                damage_amount = enemy.damage * 0.5
                if player.take_damage(damage_amount):
                    resource_manager.play_sound("player_hurt")
                    
                    # 计算击退方向和距离
                    kb_dx, kb_dy, kb_dist = self._calc_knockback_vector(player, enemy)
                    
                    if player is self.player:
                        # 本地玩家直接应用击退
                        self._apply_knockback_vector(player, kb_dx, kb_dy, kb_dist)
                    elif self.network_mode and player is self.remote_player:
                        # 镜像玩家受伤，通知加入方并同步击退
                        self._send_player_damage(damage_amount, kb_dx, kb_dy, kb_dist)
                    break
    
    def _apply_loose_projectile_hits(self, enemy, player):
        """对远程玩家使用更宽松的敌人子弹命中判定，补偿网络延迟
        
        由于网络同步延迟，远程玩家的位置可能与实际位置有偏差。
        使用距离检测代替精确碰撞，增加20像素容差。
        
        Args:
            enemy: 敌人对象
            player: 远程玩家镜像
        """
        for projectile in list(enemy.projectiles):
            px = getattr(projectile, 'x', getattr(projectile, 'world_x', 0))
            py = getattr(projectile, 'y', getattr(projectile, 'world_y', 0))
            dx = px - player.world_x
            dy = py - player.world_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            # 宽松半径：玩家半宽 + 子弹半径 + 20像素容差
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
        
        击退方向为从敌人指向玩家的方向，距离固定为50像素。
        
        Args:
            player: 玩家对象
            enemy: 敌人对象
            
        Returns:
            tuple: (dx, dy, distance) - 归一化方向向量和距离
        """
        dx = player.world_x - enemy.rect.centerx
        dy = player.world_y - enemy.rect.centery
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > 0:
            dx /= distance
            dy /= distance
        return dx, dy, 50.0
    
    def _apply_knockback_vector(self, player, dx, dy, distance):
        """对指定玩家应用击退
        
        Args:
            player: 玩家对象
            dx: 击退方向X分量（归一化）
            dy: 击退方向Y分量（归一化）
            distance: 击退距离
        """
        if distance <= 0:
            return
        player.world_x += dx * distance
        player.world_y += dy * distance
    
    def _send_player_damage(self, amount, knockback_dx=0.0, knockback_dy=0.0, knockback_distance=0.0):
        """主机通知加入方玩家受到伤害
        
        包含伤害值和击退信息，确保加入方玩家也能正确显示击退效果。
        
        Args:
            amount: 伤害值
            knockback_dx: 击退方向X分量
            knockback_dy: 击退方向Y分量
            knockback_distance: 击退距离
        """
        if not self.network_mode or not self.is_host:
            return
        net_client = get_network_client()
        net_client.send_player_damage(amount, "enemy", knockback_dx, knockback_dy, knockback_distance)
    
    def _process_player_damage_events(self):
        """加入方处理主机同步的玩家受伤事件
        
        接收主机发送的伤害和击退信息，应用到本地玩家。
        
        """
        if not self.network_mode or self.is_host or not self.player:
            return
        net_client = get_network_client()
        events = net_client.get_player_damage_events()
        for event in events:
            amount = event.get("amount", 0)
            if amount > 0 and self.player.take_damage(amount):
                resource_manager.play_sound("player_hurt")
                # 应用击退（take_damage 内部已设置无敌帧）
                kb_dx = event.get("knockback_dx", 0.0)
                kb_dy = event.get("knockback_dy", 0.0)
                kb_dist = event.get("knockback_distance", 0.0)
                self._apply_knockback_vector(self.player, kb_dx, kb_dy, kb_dist)
    
    # ============================================================
    # 第十二部分：辅助方法
    # 功能：游戏状态更新、玩家击退等辅助功能
    # ============================================================
    
    def _update_game_state(self):
        """更新游戏状态（难度等级）
        
        每分钟提升一个难度等级，等级变化时播放升级音效，并更新敌人管理器的难度等级。
        难度等级影响怪物生成速度、血量等参数（由enemy_manager内部处理）。
        """
        # 计算当前等级（游戏时间每60秒提升一级）
        current_level = int(self.game_time // 60) + 1
        
        # 等级提升时播放音效
        if current_level > self.level:
            resource_manager.play_sound("level_up")
            
        self.level = current_level
        
        # 更新敌人管理器难度等级（影响怪物生成和属性）
        if self.enemy_manager:
            self.enemy_manager.difficulty_level = self.level
    
    def _knockback_player(self, enemy):
        """将本地玩家击退（旧版方法，保留兼容）
        
        根据敌人位置计算击退方向，将玩家向远离敌人的方向推开50像素。
        
        Args:
            enemy: 造成击退的敌人对象
        """
        if not self.player or not enemy:
            return
        
        # 计算从敌人指向玩家的方向向量
        dx = self.player.world_x - enemy.rect.centerx
        dy = self.player.world_y - enemy.rect.centery
        distance = (dx**2 + dy**2)**0.5
        
        # 避免除以零
        if distance == 0:
            return
        
        # 归一化方向向量
        dx = dx / distance
        dy = dy / distance
        
        # 应用击退（固定距离50像素）
        knockback_distance = 50
        self.player.world_x += dx * knockback_distance
        self.player.world_y += dy * knockback_distance
