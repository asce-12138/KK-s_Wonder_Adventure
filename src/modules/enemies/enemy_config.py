"""
敌人配置文件
定义所有敌人的基础属性、技能和难度相关的缩放系数
"""

# 全局难度系数设置 - 根据游戏难度调整敌人属性
DIFFICULTY_MULTIPLIERS = {
    "health": {  # 生命值难度系数
        "easy": 0.8,       # 简单难度：80%生命值
        "normal": 1.0,     # 普通难度：100%生命值
        "hard": 1.3,       # 困难难度：130%生命值
        "nightmare": 1.8   # 噩梦难度：180%生命值
    },
    "damage": {  # 伤害值难度系数
        "easy": 0.7,       # 简单难度：70%伤害
        "normal": 1.0,     # 普通难度：100%伤害
        "hard": 1.5,       # 困难难度：150%伤害
        "nightmare": 2.0   # 噩梦难度：200%伤害
    },
    "speed": {  # 移动速度难度系数
        "easy": 0.9,       # 简单难度：90%速度
        "normal": 1.0,     # 普通难度：100%速度
        "hard": 1.2,       # 困难难度：120%速度
        "nightmare": 1.5   # 噩梦难度：150%速度
    }
}

# 敌人等级系数 - 随游戏时间（每分钟一级）增长
LEVEL_SCALING = {
    "health_per_level": 0,      # 每级生命值加成（目前为0，由时间递增难度系统处理）
    "damage_per_level": 0.05,   # 每级增加5%伤害
    "speed_per_level": 0.05,    # 每级增加5%速度
}

# 敌人基础配置 - 定义每种敌人的属性
ENEMY_CONFIGS = {
    # 幽灵 - 基础敌人，移动速度中等，血量较低
    "ghost": {
        "health": 80,           # 基础生命值
        "damage": 25,           # 基础伤害
        "speed": 100,           # 基础移动速度
        "score_value": 50,      # 击败后获得的分数
        "animation_speed": 0.0333, # 动画播放速度
        "scale": 1.0,           # 图像缩放大小
    },
    
    # 萝卜 - 较慢但更健壮的敌人，近战攻击
    "radish": {
        "health": 150,          # 高生命值
        "damage": 35,           # 较高伤害
        "speed": 70,            # 移动速度较慢
        "score_value": 15,      # 击败分数
        "animation_speed": 0.0333, # 动画速度
        "scale": 1.0,           # 缩放大小
    },
    
    # 蝙蝠 - 快速但脆弱的敌人，森林地图专属
    "bat": {
        "health": 60,           # 低生命值（脆弱）
        "damage": 25,           # 中等伤害
        "speed": 280,           # 极快移动速度
        "score_value": 80,      # 击败分数
        "animation_speed": 0.0333, # 动画速度
        "scale": 2.0,           # 较大的缩放
    },
    
    # 史莱姆 - 远程攻击敌人，发射子弹
    "slime": {
        "health": 100,          # 中等生命值
        "damage": 30,           # 子弹伤害
        "speed": 80,            # 移动速度较慢
        "score_value": 150,     # 击败分数
        "animation_speed": 0.0333, # 动画速度
        "scale": 1.0,           # 缩放大小
        "attack_range": 800,    # 最大攻击距离
        "min_attack_range": 300, # 最小攻击距离（太近不攻击）
        "attack_cooldown": 2.0,  # 攻击冷却时间（秒）
        "projectile_speed": 180, # 投射物飞行速度
    },
    
    # boss1（骷髅）- Boss级敌人，数值较高
    "boss1": {
        "health": 200,          # 高生命值
        "damage": 50,           # 高伤害
        "speed": 150,           # 移动速度中等偏快
        "score_value": 200,     # 击败分数
        "animation_speed": 0.0333, # 动画速度
        "scale": 1.5,           # 较大的Boss体型
    },
    
    # skt - 双形态敌人，idle1远程攻击(无近战)，idle2近战攻击(无远程)
    "skt": {
        "health": 120,          # 中等生命值
        "damage": 40,           # 伤害值
        "speed": 90,            # 移动速度
        "score_value": 200,     # 击败分数
        "animation_speed": 0.0333, # 动画速度
        "scale": 1.0,           # 缩放大小
        "attack_range": 600,    # 远程攻击范围
        "min_attack_range": 200, # 最小攻击距离
        "attack_cooldown": 2.0,  # 攻击冷却时间
        "projectile_speed": 200, # 投射物速度
        "form_switch_interval": 5.0, # 形态切换间隔（秒）
    },
    
    # bsl - 隐身敌人，远离玩家时透明，靠近才可见
    "bsl": {
        "health": 150,          # 中等生命值
        "damage": 35,           # 伤害值
        "speed": 120,           # 移动速度
        "score_value": 250,     # 击败分数
        "animation_speed": 0.0333, # 动画速度
        "scale": 1.0,           # 缩放大小
        "visibility_range": 150, # 可见范围（距离玩家多少单位内可见）
        "visibility_fade_range": 50, # 渐隐范围（超出可见范围后开始透明）
    },
    
    # xiniu（犀牛）- 疾跑敌人，靠近玩家时加速冲刺
    "xiniu": {
        "health": 100,          # 中等生命值
        "damage": 45,           # 冲刺伤害较高
        "speed": 100,           # 普通移动速度
        "score_value": 180,     # 击败分数
        "animation_speed": 0.0333, # 动画速度
        "scale": 1.0,           # 缩放大小
        "charge_range": 200,    # 冲刺触发范围（距离玩家多少单位内开始冲刺）
        "charge_speed_multiplier": 1.8, # 冲刺速度倍率
    },
    
    # ap - 愤怒敌人，生命值低于50%时切换愤怒形态
    "ap": {
        "health": 200,          # 较高生命值
        "damage": 30,           # 正常状态伤害
        "speed": 80,            # 正常状态速度
        "score_value": 300,     # 击败分数
        "animation_speed": 0.0333, # 动画速度
        "scale": 1.0,           # 缩放大小
        "enrage_damage_multiplier": 2.0, # 愤怒状态伤害倍率（×2）
        "enrage_speed_multiplier": 2.0,  # 愤怒状态速度倍率（×2）
    },
    
    # plant（植物）- 固定炮台敌人，不移动，根据距离发射不同弹幕
    "plant": {
        "health": 180,          # 中等生命值
        "damage": 0,            # 无近战伤害
        "speed": 0,             # 不移动
        "score_value": 250,     # 击败分数
        "animation_speed": 0.0333, # 动画速度
        "scale": 1.0,           # 缩放大小
        "attack_cooldown": 1.5,       # 远程攻击冷却时间
        "attack_cooldown_near": 0.8,  # 近距离攻击冷却时间（更快）
        "near_range": 250,            # 近距离阈值
        "bullet_speed": 200,          # 子弹速度
        "bullet_damage": 20,          # 子弹伤害
    },
    
    # fly（苍蝇）- 飞行敌人，有碰撞伤害，发射减速子弹
    "fly": {
        "health": 90,           # 中等生命值
        "damage": 30,           # 碰撞伤害
        "speed": 140,           # 飞行速度
        "score_value": 200,     # 击败分数
        "animation_speed": 0.0333, # 动画速度
        "scale": 0.35,          # 较小体型
        "attack_range": 500,    # 攻击范围
        "min_attack_range": 150, # 最小攻击距离
        "attack_cooldown": 2.0,  # 攻击冷却时间
        "bullet_speed": 220,    # 子弹速度
        "bullet_damage": 25,    # 子弹伤害
        "slow_percent": 0.4,    # 减速百分比（减速40%）
        "slow_duration": 3.0,   # 减速持续时间（秒）
    }
}

def get_enemy_config(enemy_type, difficulty="normal", level=1):
    """
    获取指定类型、难度和等级的敌人配置
    
    Args:
        enemy_type (str): 敌人类型
        difficulty (str): 游戏难度 ('easy', 'normal', 'hard', 'nightmare')
        level (int): 游戏当前等级
        
    Returns:
        dict: 包含敌人属性的字典
    """
    # 获取基础配置
    if enemy_type not in ENEMY_CONFIGS:
        raise ValueError(f"未知的敌人类型: {enemy_type}")
    
    config = ENEMY_CONFIGS[enemy_type].copy()
    
    # 应用难度系数
    if difficulty in DIFFICULTY_MULTIPLIERS["health"]:
        config["health"] *= DIFFICULTY_MULTIPLIERS["health"][difficulty]
        config["damage"] *= DIFFICULTY_MULTIPLIERS["damage"][difficulty]
        config["speed"] *= DIFFICULTY_MULTIPLIERS["speed"][difficulty]
    
    # 应用等级系数
    if level > 1:
        level_factor = level - 1  # 从第2级开始计算额外加成
        config["health"] *= (1 + LEVEL_SCALING["health_per_level"] * level_factor)
        config["damage"] *= (1 + LEVEL_SCALING["damage_per_level"] * level_factor)
        config["speed"] *= (1 + LEVEL_SCALING["speed_per_level"] * level_factor)
    
    # 确保数值合理
    config["health"] = round(config["health"])
    config["damage"] = round(config["damage"])
    config["speed"] = round(config["speed"])
    
    return config 