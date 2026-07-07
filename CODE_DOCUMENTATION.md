# KK的奇妙冒险 - 代码文档

## 目录

- [一、核心架构](#一核心架构)
- [二、玩家系统](#二玩家系统)
- [三、敌人系统](#三敌人系统)
- [四、武器系统](#四武器系统)
- [五、道具系统](#五道具系统)
- [六、地图系统](#六地图系统)
- [七、UI和菜单系统](#七ui和菜单系统)
- [八、升级系统](#八升级系统)
- [九、资源管理](#九资源管理)
- [十、存档系统](#十存档系统)
- [十一、网络系统](#十一网络系统)
- [十二、资源文件](#十二资源文件)

---

## 一、核心架构

### 提纲

| 序号 | 代码块 | 功能描述 | 链接 |
|------|--------|---------|------|
| C1 | main.py | 游戏启动入口，场景切换管理，主循环控制 | [main.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/main.py) |
| C2 | game.py | 游戏核心类，协调所有子系统，状态机管理，碰撞检测，网络同步 | [game.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/game.py) |

### C1 - 游戏启动入口 [main.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/main.py)

**功能**: 初始化Pygame、创建窗口、管理场景切换（网络大厅/单机菜单/游戏）、控制主循环

**关键逻辑**:
- 场景状态机: `lobby` → `standalone_menu` → `game`
- 主循环: 60FPS帧率控制，事件分发，更新渲染
- 网络模式支持: 通过 `network_mode` 和 `is_host` 参数控制

---

### C2 - 游戏核心类 [game.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/game.py)

**功能**: 协调玩家、敌人、道具、地图、UI等所有子系统，管理游戏状态

**关键逻辑**:
- 状态管理: `in_main_menu`、`paused`、`game_over`、`level_complete`
- 事件分发: 根据当前状态路由输入事件
- 碰撞检测: 武器投射物与敌人、敌人与玩家碰撞
- 网络同步: 主机权威模式，玩家/敌人/道具状态同步

---

## 二、玩家系统

### 提纲

| 序号 | 代码块 | 功能描述 | 链接 |
|------|--------|---------|------|
| P1 | player.py | 玩家实体类，整合所有组件（ECS架构） | [player.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/player.py) |
| P2 | MovementComponent | 移动组件，处理输入和物理移动 | [movement_component.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/components/movement_component.py) |
| P3 | AnimationComponent | 动画组件，管理精灵表和帧播放 | [animation_component.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/components/animation_component.py) |
| P4 | HealthComponent | 生命值组件，处理伤害、防御、回血 | [health_component.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/components/health_component.py) |
| P5 | WeaponManager | 武器管理器，管理武器列表和攻击 | [weapon_manager.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/components/weapon_manager.py) |
| P6 | PassiveManager | 被动技能管理器，计算属性加成 | [passive_manager.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/components/passive_manager.py) |
| P7 | ProgressionSystem | 进阶系统，管理经验、等级、金币 | [progression_system.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/components/progression_system.py) |
| P8 | hero_config.py | 角色配置，定义不同角色的属性和动画 | [hero_config.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/hero_config.py) |

### P1 - 玩家实体类 [player.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/player.py)

**功能**: 玩家主类，使用ECS架构整合所有组件，提供统一接口

**关键逻辑**:
- `_init_components()`: 初始化6个核心组件
- `_update_stats()`: 根据被动加成重新计算所有属性
- `_update_animation_state()`: 根据移动/受伤状态切换动画
- `@property` 装饰器: 提供兼容旧接口的属性访问

---

### P2 - 移动组件 [movement_component.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/components/movement_component.py)

**功能**: 处理玩家输入（WASD）、计算移动方向、更新世界坐标

**关键逻辑**:
- `handle_event()`: 监听键盘按下/释放，更新移动状态字典
- `update()`: 根据方向向量和速度更新实体位置
- `set_boundaries()`: 设置地图边界限制
- `set_speed_multiplier()`: 支持减速/加速debuff

---

### P3 - 动画组件 [animation_component.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/components/animation_component.py)

**功能**: 加载精灵表、播放动画帧、支持闪烁效果和镜像翻转

**关键逻辑**:
- `load_animations()`: 从配置加载多个动画（idle/run/hurt等）
- `set_animation()`: 切换当前动画并重置帧索引
- `get_current_frame()`: 获取当前帧，支持水平翻转
- `start_blinking()`: 无敌状态闪烁效果

---

### P4 - 生命值组件 [health_component.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/components/health_component.py)

**功能**: 管理生命值、防御、回血、无敌时间

**关键逻辑**:
- `take_damage()`: 扣血前减去防御，触发无敌时间
- `heal()`: 恢复生命值，不超过最大值
- `update()`: 处理无敌时间和持续回血
- `on_damaged`: 受伤回调，触发受伤动画

---

### P5 - 武器管理器 [weapon_manager.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/components/weapon_manager.py)

**功能**: 管理玩家武器列表、攻击冷却、武器升级

**关键逻辑**:
- `add_weapon()`: 添加武器到列表
- `apply_weapon_upgrade()`: 应用升级效果到武器属性
- `update()`: 更新所有武器的冷却时间和投射物
- `on_projectile_created`: 投射物创建回调（网络同步用）

---

### P6 - 被动技能管理器 [passive_manager.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/components/passive_manager.py)

**功能**: 管理被动技能等级，计算属性加成

**关键逻辑**:
- `apply_passive_upgrade()`: 应用被动升级
- `calculate_stats()`: 根据被动等级计算加成后的属性
- `on_stats_changed`: 属性变化回调，触发玩家属性更新

---

### P7 - 进阶系统 [progression_system.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/components/progression_system.py)

**功能**: 管理经验值、等级提升、金币积累

**关键逻辑**:
- `add_experience()`: 添加经验，判断是否升级
- `level_up()`: 升级处理，增加属性上限
- `add_coins()`: 添加金币
- 经验公式: 等级越高，升级所需经验越多

---

### P8 - 角色配置 [hero_config.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/hero_config.py)

**功能**: 定义不同角色的基础属性和动画配置

**关键逻辑**:
- `get_hero_config()`: 根据角色类型返回配置
- 支持角色: KK、Loli_Mage、Masked_Dude、Ninja_frog、Pink_Man、YoungLoli
- 配置包含: `base_stats`、`animations`、`starting_weapon`、`scale_factor`

---

## 三、敌人系统

### 提纲

| 序号 | 代码块 | 功能描述 | 链接 |
|------|--------|---------|------|
| E1 | enemy_manager.py | 敌人生成、更新、渲染、难度递增管理 | [enemy_manager.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/enemy_manager.py) |
| E2 | enemy.py | 敌人基类，定义通用属性和方法 | [enemy.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/enemy.py) |
| E3 | enemy_config.py | 敌人属性配置（血量、伤害、速度等） | [enemy_config.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/enemy_config.py) |
| E4 | Ghost/Radish/Bat/Slime | 基础敌人类型 | [types/](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/) |
| E5 | Skt | 双形态敌人（远程/近战切换） | [skt.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/skt.py) |
| E6 | Bsl | 隐身敌人（靠近时可见） | [bsl.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/bsl.py) |
| E7 | Xiniu | 冲刺敌人（靠近玩家加速） | [xiniu.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/xiniu.py) |
| E8 | Ap | 愤怒状态敌人（低血量触发） | [ap.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/ap.py) |
| E9 | Plant | 远程射击敌人（发射子弹） | [plant.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/plant.py) |
| E10 | Fly | 飞行敌人 | [fly.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/fly.py) |
| E11 | Skeleton (Boss1) | Boss敌人 | [skeleton.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/skeleton.py) |
| E12 | visual_enemy_projectile.py | 敌人投射物视觉副本（网络同步用） | [visual_enemy_projectile.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/visual_enemy_projectile.py) |

### E1 - 敌人管理器 [enemy_manager.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/enemy_manager.py)

**功能**: 管理敌人生成、更新、渲染、难度递增和网络同步

**关键逻辑**:
- `random_spawn_enemy()`: 在玩家周围随机位置生成敌人
- `update()`: 更新敌人AI，处理难度递增
- 难度递增: 从2分钟开始，每60秒生成速度翻倍、怪物血量×1.5
- 地图限制: 根据当前地图决定生成哪种类型敌人
- 网络同步: 主机广播状态，加入方接收同步

---

### E2 - 敌人基类 [enemy.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/enemy.py)

**功能**: 定义敌人通用属性和方法

**关键逻辑**:
- `__init__()`: 初始化位置、血量、伤害、速度
- `update()`: 更新敌人位置和动画
- `take_damage()`: 处理受伤，播放受伤动画
- `render()`: 绘制敌人图像和血条
- `to_network_state()`/`apply_network_state()`: 网络同步方法

---

### E3 - 敌人配置 [enemy_config.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/enemy_config.py)

**功能**: 存储所有敌人的属性配置

**关键配置项**:
- `health`: 生命值
- `damage`: 伤害值
- `speed`: 移动速度
- `visibility_range`/`visibility_fade_range`: 隐身参数（Bsl专用）
- `charge_range`/`charge_speed_multiplier`: 冲刺参数（Xiniu专用）
- `enrage_damage_multiplier`/`enrage_speed_multiplier`: 愤怒状态参数（Ap专用）

---

### E4 - 基础敌人类型 [types/](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/)

**功能**: Ghost、Radish、Bat、Slime 四种基础敌人

**共同逻辑**:
- 追踪玩家移动
- 碰撞造成伤害
- 死亡后生成掉落物

---

### E5 - Skt双形态敌人 [skt.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/skt.py)

**功能**: 每5秒切换形态的敌人

**形态切换**:
- **Form 1 (idle1)**: 远程攻击，无近战伤害
- **Form 2 (idle2)**: 近战碰撞伤害，无远程攻击

---

### E6 - Bsl隐身敌人 [bsl.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/bsl.py)

**功能**: 根据距离动态调整透明度的敌人

**隐身逻辑**:
- 距离 < 100: 完全可见
- 100 ≤ 距离 < 133: 逐渐透明
- 距离 ≥ 133: 完全透明

---

### E7 - Xiniu冲刺敌人 [xiniu.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/xiniu.py)

**功能**: 当玩家进入范围时加速冲刺的敌人

**冲刺逻辑**:
- 距离 > 200: 慢速移动，使用idle动画
- 距离 ≤ 200: 加速到180速度，使用run动画

---

### E8 - Ap愤怒敌人 [ap.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/ap.py)

**功能**: 低血量时进入愤怒状态的敌人

**愤怒触发**:
- 血量 > 50%: 绿色形态（ap_green），伤害30，速度80
- 血量 ≤ 50%: 红色形态（ap_red），伤害60，速度160（伤害×2，速度×2）

---

### E9 - Plant远程敌人 [plant.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/plant.py)

**功能**: 发射子弹攻击玩家的敌人

**攻击逻辑**:
- 定时发射子弹
- 子弹有300距离限制
- 子弹存活时间5秒

---

### E10 - Fly飞行敌人 [fly.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/fly.py)

**功能**: 飞行移动的敌人

**特点**:
- 使用飞行动画
- 较小的碰撞体积
- 血条固定32×5像素

---

### E11 - Skeleton Boss [skeleton.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/types/skeleton.py)

**功能**: Boss级敌人

**特点**:
- 高血量和伤害
- 使用特殊动画
- 较大的缩放比例

---

### E12 - 视觉投射物 [visual_enemy_projectile.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/enemies/visual_enemy_projectile.py)

**功能**: 网络模式下客户端显示的敌人投射物视觉副本

**用途**: 主机广播敌人投射物事件后，客户端创建视觉副本进行渲染，无需执行完整物理逻辑

---

## 四、武器系统

### 提纲

| 序号 | 代码块 | 功能描述 | 链接 |
|------|--------|---------|------|
| W1 | weapon.py | 武器基类，定义通用属性和方法 | [weapon.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/weapons/weapon.py) |
| W2 | Knife | 投掷武器，支持穿透 | [knife.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/weapons/types/knife.py) |
| W3 | Fireball | 火球武器，追踪敌人 | [fireball.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/weapons/types/fireball.py) |
| W4 | FrostNova | 冰系武器，发射冰锥 | [frost_nova.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/weapons/types/frost_nova.py) |
| W5 | weapon_stats.py | 武器属性枚举和默认值 | [weapon_stats.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/weapons/weapon_stats.py) |
| W6 | weapons_data.py | 武器配置数据 | [weapons_data.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/weapons/weapons_data.py) |

### W1 - 武器基类 [weapon.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/weapons/weapon.py)

**功能**: 定义武器通用属性和方法

**关键逻辑**:
- `attack_timer`/`attack_interval`: 攻击冷却控制
- `base_stats`/`current_stats`: 基础属性和升级后属性
- `handle_collision()`: 处理投射物与敌人碰撞，支持穿透
- `apply_effects()`: 应用升级效果

---

### W2 - 飞刀武器 [knife.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/weapons/types/knife.py)

**功能**: 投掷型武器

**特点**:
- 快速攻击
- 支持穿透多个敌人
- 伤害随距离衰减

---

### W3 - 火球武器 [fireball.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/weapons/types/fireball.py)

**功能**: 追踪型远程武器

**特点**:
- 追踪最近的敌人
- 命中后爆炸造成范围伤害
- 可升级为巨型火球（伤害×3，范围×3）

---

### W4 - 霜冻新星 [frost_nova.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/weapons/types/frost_nova.py)

**功能**: 冰系范围武器

**特点**:
- 发射多个冰锥
- 命中敌人造成减速效果
- 冰锥有追踪能力

---

### W5 - 武器属性枚举 [weapon_stats.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/weapons/weapon_stats.py)

**功能**: 定义武器属性类型和默认值

**属性类型**:
- DAMAGE: 伤害
- ATTACK_SPEED: 攻击速度
- PROJECTILE_SPEED: 投射物速度
- LIFETIME: 存活时间
- PENETRATION: 穿透次数
- EXPLOSION_RADIUS: 爆炸半径

---

### W6 - 武器配置数据 [weapons_data.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/weapons/weapons_data.py)

**功能**: 存储武器的基础配置数据

**配置内容**:
- 每种武器的基础属性值
- 图标路径
- 升级效果定义

---

## 五、道具系统

### 提纲

| 序号 | 代码块 | 功能描述 | 链接 |
|------|--------|---------|------|
| I1 | item.py | 道具基类，定义通用属性和方法 | [item.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/items/item.py) |
| I2 | item_manager.py | 道具生成、更新、渲染、拾取管理 | [item_manager.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/items/item_manager.py) |

### I1 - 道具基类 [item.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/items/item.py)

**功能**: 定义道具通用属性和方法

**道具类型**:
- 草莓: 恢复生命值
- 金币: 增加金币数量
- 宝箱: 随机奖励
- 宝石: 增加经验
- 药水: 恢复大量生命值

**关键逻辑**:
- `update()`: 更新道具动画
- `render()`: 渲染道具图像
- `on_collected()`: 被拾取时的回调

---

### I2 - 道具管理器 [item_manager.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/items/item_manager.py)

**功能**: 管理道具的生成、更新、渲染和拾取

**关键逻辑**:
- `spawn_item()`: 在指定位置生成道具
- `update()`: 更新所有道具状态，检测玩家拾取
- `render()`: 渲染所有道具
- `on_collect_callback`: 拾取回调（网络同步用）

---

## 六、地图系统

### 提纲

| 序号 | 代码块 | 功能描述 | 链接 |
|------|--------|---------|------|
| M1 | map_manager.py | TMX地图加载和渲染，支持双重渲染方式 | [map_manager.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/map_manager.py) |

### M1 - 地图管理器 [map_manager.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/map_manager.py)

**功能**: 加载和渲染TMX格式地图

**关键逻辑**:
- `load_map()`: 使用pytmx加载TMX文件，预缓存图块
- `render()`: 使用pyscroll渲染，失败时回退到直接渲染
- `_cache_all_tiles()`: 预缓存所有图块，提高性能
- `_calculate_visible_tiles()`: 只计算视口内可见图块
- `get_map_size()`: 获取地图尺寸
- `get_collision_tiles()`: 获取碰撞图块
- `get_objects()`: 获取对象层对象

**三张地图**:
- **simple_map**: 森林地图，使用FieldsTileset.png
- **ocean_map**: 海洋地图，使用OceanTileset.png
- **volcano_map**: 火山地图，使用VolcanoTileset.png

---

## 七、UI和菜单系统

### 提纲

| 序号 | 代码块 | 功能描述 | 链接 |
|------|--------|---------|------|
| U1 | ui.py | 游戏内UI（血条、经验条、武器图标等） | [ui.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/ui.py) |
| U2 | menu.py | 暂停菜单、游戏结束菜单、升级菜单 | [menu.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/menu.py) |
| U3 | main_menu.py | 主菜单 | [main_menu.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/menus/main_menu.py) |
| U4 | map_hero_select_menu.py | 地图和角色选择菜单 | [map_hero_select_menu.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/menus/map_hero_select_menu.py) |
| U5 | save_menu.py | 存档/读档菜单 | [save_menu.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/menus/save_menu.py) |
| U6 | lobby.py | 网络联机大厅 | [lobby.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/menus/lobby.py) |

### U1 - 游戏内UI [ui.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/ui.py)

**功能**: 渲染游戏内HUD界面

**UI元素**:
- 顶部: 经验条 + 等级显示
- 底部: 血条 + 武器图标 + 被动技能图标
- 左上角: 游戏时间
- 中间: 击杀数
- 右上角: 金币数

---

### U2 - 游戏菜单 [menu.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/menu.py)

**功能**: 暂停菜单、游戏结束菜单、升级菜单

**菜单类型**:
- **PauseMenu**: 暂停时显示，包含继续、存档、重新开始、主菜单
- **GameOverMenu**: 游戏结束时显示，包含重新开始、主菜单、退出
- **UpgradeMenu**: 升级时显示，列出可用升级项供玩家选择

---

### U3 - 主菜单 [main_menu.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/menus/main_menu.py)

**功能**: 游戏启动时显示的主菜单

**选项**:
- 开始游戏
- 读取存档
- 联机模式（单机模式下显示）
- 退出游戏

---

### U4 - 地图角色选择 [map_hero_select_menu.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/menus/map_hero_select_menu.py)

**功能**: 选择地图和角色的界面

**选择内容**:
- 地图: 森林、海洋、火山
- 角色: KK、Loli_Mage、Masked_Dude、Ninja_frog、Pink_Man、YoungLoli

---

### U5 - 存档菜单 [save_menu.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/menus/save_menu.py)

**功能**: 存档和读档界面

**功能**:
- 显示多个存档槽位
- 保存当前游戏进度
- 加载已保存的游戏

---

### U6 - 网络大厅 [lobby.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/menus/lobby.py)

**功能**: 网络联机大厅界面

**功能**:
- 创建房间（作为主机）
- 加入房间（作为客户端）
- 返回单机模式

---

## 八、升级系统

### 提纲

| 序号 | 代码块 | 功能描述 | 链接 |
|------|--------|---------|------|
| UG1 | upgrade_system.py | 武器升级和被动技能升级系统 | [upgrade_system.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/upgrade_system.py) |

### UG1 - 升级系统 [upgrade_system.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/upgrade_system.py)

**功能**: 管理武器升级和被动技能升级

**升级类型**:
- **WeaponUpgradeLevel**: 武器升级，每级提供属性加成（伤害、攻速、范围等）
- **PassiveUpgradeLevel**: 被动技能升级，提供全局属性加成

**被动技能列表**:
- 伤害提升: 增加攻击伤害
- 防御提升: 增加防御力
- 速度提升: 增加移动速度
- 血量提升: 增加最大生命值
- 幸运提升: 增加掉落概率
- 吸血: 攻击时恢复生命值
- 回血: 持续恢复生命值

**升级流程**:
1. 玩家获得经验 → 经验满 → 触发 `level_up()`
2. 显示 `UpgradeMenu`，列出可用升级项
3. 玩家选择升级 → 调用 `_apply_upgrade()`
4. 更新武器属性或被动等级 → 调用 `_update_stats()` 重新计算玩家属性

---

## 九、资源管理

### 提纲

| 序号 | 代码块 | 功能描述 | 链接 |
|------|--------|---------|------|
| R1 | resource_manager.py | 统一管理图像、音频资源的加载和缓存 | [resource_manager.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/resource_manager.py) |

### R1 - 资源管理器 [resource_manager.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/resource_manager.py)

**功能**: 单例模式，统一管理所有游戏资源

**资源类型**:
- 图像: 使用 `load_image()` 加载，自动缓存
- 精灵表: 使用 `load_spritesheet()` 加载
- 动画: 使用 `create_animation()` 创建
- 音乐: 使用 `play_music()` 播放背景音乐
- 音效: 使用 `play_sound()` 播放音效

**关键逻辑**:
- 单例模式: 全局唯一实例
- 缓存机制: 已加载的资源存储在字典中，避免重复加载
- 路径管理: 通过 `resource_dir` 统一管理资源路径

---

## 十、存档系统

### 提纲

| 序号 | 代码块 | 功能描述 | 链接 |
|------|--------|---------|------|
| S1 | save_system.py | 游戏进度保存和读取 | [save_system.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/save_system.py) |

### S1 - 存档系统 [save_system.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/save_system.py)

**功能**: 保存和加载游戏进度

**存档数据结构**:
- `player_data`: 玩家属性、装备、被动等级
  - `health`: 当前生命值
  - `max_health`: 最大生命值
  - `level`: 等级
  - `experience`: 经验值
  - `coins`: 金币数
  - `world_x`/`world_y`: 玩家位置
  - `component_states`: 各组件状态
  - `weapons`: 武器列表和等级
- `game_data`: 游戏时间、击杀数、难度等级
- `enemies_data`: 当前存活敌人状态

**存档流程**:
- 保存: `save_game(slot_id, game, screen)` → 收集数据 → JSON序列化 → 写入文件
- 加载: 读取文件 → JSON解析 → 恢复玩家状态 → 恢复敌人状态

---

## 十一、网络系统

### 提纲

| 序号 | 代码块 | 功能描述 | 链接 |
|------|--------|---------|------|
| N1 | network_client.py | 网络客户端，WebSocket通信 | [network_client.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/network_client.py) |
| N2 | remote_player.py | 远程玩家同步和渲染 | [remote_player.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/remote_player.py) |
| N3 | server.py | 游戏服务器 | [server.py](file:///e:/72kk/KK-s_Wonder_Adventure/server.py) |

### N1 - 网络客户端 [network_client.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/network_client.py)

**功能**: WebSocket客户端，处理网络通信

**通信协议**:
- 玩家数据: 20Hz同步（位置、血量、移动状态）
- 敌人状态: 10Hz全量同步
- 事件: 实时（伤害、死亡、生成、拾取）

**消息类型**:
- `player_data`: 玩家位置和状态
- `enemy_damage`: 敌人伤害事件
- `enemy_death`: 敌人死亡事件
- `enemy_spawn`: 敌人生成事件
- `item_spawn/remove/pickup`: 道具事件
- `weapon_attack`: 武器攻击特效

---

### N2 - 远程玩家 [remote_player.py](file:///e:/72kk/KK-s_Wonder_Adventure/src/modules/remote_player.py)

**功能**: 网络模式下远程玩家的本地镜像

**关键逻辑**:
- `update_from_network()`: 根据网络数据更新位置和状态
- `render()`: 渲染远程玩家图像和武器特效
- 宽松命中判定: 对远程玩家使用更宽松的子弹命中范围，补偿网络延迟

---

### N3 - 游戏服务器 [server.py](file:///e:/72kk/KK-s_Wonder_Adventure/server.py)

**功能**: WebSocket服务器，处理客户端连接和消息转发

**关键逻辑**:
- 管理客户端连接
- 转发玩家数据和事件
- 保持游戏状态同步

---

## 十二、资源文件

### 提纲

| 序号 | 目录 | 功能描述 | 路径 |
|------|------|---------|------|
| RF1 | images/enemy/ | 敌人动画精灵表 | [images/enemy/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/images/enemy) |
| RF2 | images/player/ | 玩家角色动画精灵表 | [images/player/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/images/player) |
| RF3 | images/weapons/ | 武器图标和投射物图像 | [images/weapons/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/images/weapons) |
| RF4 | images/items/ | 道具图标 | [images/items/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/images/items) |
| RF5 | images/passives/ | 被动技能图标 | [images/passives/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/images/passives) |
| RF6 | images/effects/ | 特效图像（爆炸等） | [images/effects/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/images/effects) |
| RF7 | maps/ | TMX地图文件和图块集 | [maps/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/maps) |
| RF8 | bgm/ | 背景音乐 | [bgm/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/bgm) |
| RF9 | sfx/ | 音效 | [sfx/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/sfx) |

### RF1 - 敌人精灵表 [images/enemy/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/images/enemy)

**精灵表命名规则**: `{enemy_type}_{state}_{width}x{height}.png`

**示例**:
- `ghost_idle_100x100.png`: 幽灵待机动画
- `ap_green_80x80.png`: Ap绿色形态
- `ap_red_80x80.png`: Ap红色形态

---

### RF2 - 玩家精灵表 [images/player/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/images/player)

**精灵表命名规则**: `{hero_type}_{state}_{width}x{height}.png`

**示例**:
- `ninja_frog_idle_64x64.png`: 忍者蛙待机动画
- `kk_run_64x64.png`: KK奔跑动画

---

### RF3 - 武器图像 [images/weapons/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/images/weapons)

**内容**:
- 武器图标（用于UI）
- 投射物图像（飞刀、火球、冰锥）

---

### RF4 - 道具图标 [images/items/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/images/items)

**内容**:
- 草莓图标
- 金币图标
- 宝箱图标
- 宝石图标
- 药水图标

---

### RF5 - 被动技能图标 [images/passives/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/images/passives)

**内容**:
- 伤害提升图标
- 防御提升图标
- 速度提升图标
- 血量提升图标
- 幸运提升图标
- 吸血图标
- 回血图标

---

### RF6 - 特效图像 [images/effects/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/images/effects)

**内容**:
- 爆炸特效
- 火焰特效
- 冰霜特效

---

### RF7 - 地图资源 [maps/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/maps)

**内容**:
- TMX地图文件: `simple_map.tmx`、`ocean_map.tmx`、`volcano_map.tmx`
- 图块集: `FieldsTileset.png`、`OceanTileset.png`、`VolcanoTileset.png`

---

### RF8 - 背景音乐 [bgm/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/bgm)

**内容**:
- 菜单背景音乐
- 游戏背景音乐
- 各地图专属音乐

---

### RF9 - 音效 [sfx/](file:///e:/72kk/KK-s_Wonder_Adventure/assets/sfx)

**内容**:
- 攻击音效
- 受伤音效
- 死亡音效
- 升级音效
- 拾取音效
- 玩家死亡音效

---

## 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py (入口)                            │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Game (核心类)                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │   Player    │ │EnemyManager │ │ ItemManager │ │ MapManager│ │
│  │  (ECS架构)   │ │ (敌人管理)   │ │  (道具管理)  │ │ (地图管理)│ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────┬─────┘ │
│         │               │               │               │       │
│  ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌─────▼─────┐ │
│  │Component组  │ │ Enemy Types │ │    Items    │ │  TMX Maps │ │
│  │(6个组件)    │ │(11种敌人)   │ │(5种道具)    │ │(3张地图)  │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │  UI/HUD     │ │    Menus    │ │UpgradeSystem│ │Network    │ │
│  │(血条/经验)  │ │(暂停/菜单)   │ │(武器/被动)  │ │(联机)     │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ResourceManager (资源管理)                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │   Images    │ │    BGM      │ │    SFX      │ │   Cache   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 数据流

```
玩家输入 → Game.handle_event() → Player.handle_event() → MovementComponent
                                                         → WeaponManager
                                                         
Game.update() → Player.update() → 各组件update()
              → EnemyManager.update() → 各Enemy.update()
              → ItemManager.update()
              → 碰撞检测
              → 网络同步（联机模式）
              
Game.render() → MapManager.render()
              → EnemyManager.render()
              → ItemManager.render()
              → Player.render()
              → UI.render()
              → 菜单渲染
```

## 难度递增规则

| 时间点 | 生成间隔 | 血量倍率 | 说明 |
|--------|---------|---------|------|
| 0-2分钟 | 1秒 | ×1.0 | 初始难度 |
| 2分钟 | 0.5秒 | ×1.5 | 第一次提升 |
| 3分钟 | 0.25秒 | ×2.25 | 第二次提升 |
| 4分钟 | 0.125秒 | ×3.375 | 第三次提升 |
| 5分钟+ | 0.1秒(上限) | 持续×1.5 | 生成速度达到上限 |

---

*文档版本: v1.0*  
*最后更新: 2026-07-07*  
*项目名称: KK的奇妙冒险*
