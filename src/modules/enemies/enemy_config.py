"""
敌人配置文件
定义所有敌人的基础属性、技能和难度相关的缩放系数
"""

# 全局难度系数设置
DIFFICULTY_MULTIPLIERS = {
    "health": {  # 健康值随难度增长的系数
        "easy": 0.8,
        "normal": 1.0,
        "hard": 1.3,
        "nightmare": 1.8
    },
    "damage": {  # 伤害值随难度增长的系数
        "easy": 0.7,
        "normal": 1.0,
        "hard": 1.5,
        "nightmare": 2.0
    },
    "speed": {  # 速度随难度增长的系数
        "easy": 0.9,
        "normal": 1.0,
        "hard": 1.2,
        "nightmare": 1.5
    }
}

# 敌人等级系数 (游戏时间增加时应用)
LEVEL_SCALING = {
    "health_per_level": 0,  # 每级不增加生命值
    "damage_per_level": 0.05,  # 每级增加5%伤害
    "speed_per_level": 0.05,   # 每级增加5%速度
}

# 敌人基础配置
ENEMY_CONFIGS = {
    # 幽灵 - 基础敌人
    "ghost": {
        "health": 80,           # 基础生命值
        "damage": 25,           # 基础伤害（从10提高到25）
        "speed": 100,           # 基础移动速度
        "score_value": 50,      # 击败后获得的分数
        "animation_speed": 0.0333, # 动画速度
        "scale": 1.0,           # 缩放大小
    },
    
    # 萝卜 - 较慢但更健壮的敌人
    "radish": {
        "health": 150,
        "damage": 35,           # 基础伤害（从15提高到35）
        "speed": 70,
        "score_value": 15,
        "animation_speed": 0.0333,
        "scale": 1.0,
    },
    
    # 蝙蝠 - 快速但脆弱的敌人
    "bat": {
        "health": 60,
        "damage": 20,           # 基础伤害（从8提高到20）
        "speed": 200,
        "score_value": 80,
        "animation_speed": 0.0333,
        "scale": 2.0,
    },
    
    # 史莱姆 - 远程攻击敌人
    "slime": {
        "health": 100,
        "damage": 30,           # 基础伤害（从12提高到30）
        "speed": 80,
        "score_value": 150,
        "animation_speed": 0.0333,
        "scale": 1.0,
        "attack_range": 800,    # 攻击范围
        "min_attack_range": 300, # 最小攻击距离
        "attack_cooldown": 2.0,  # 攻击冷却时间(秒)
        "projectile_speed": 180, # 投射物速度
    },
    
    # boss1 - Boss级敌人，每5次生成一次，数值很高
    "boss1": {
        "health": 200,
        "damage": 50,          # 基础伤害（从80提高到150）
        "speed": 150,
        "score_value": 200,
        "animation_speed": 0.0333,
        "scale": 1.5,
    },
    
    # skt - 双形态敌人，idle1远程攻击，idle2近战攻击
    "skt": {
        "health": 120,
        "damage": 40,
        "speed": 90,
        "score_value": 200,
        "animation_speed": 0.0333,
        "scale": 1.0,
        "attack_range": 600,
        "min_attack_range": 200,
        "attack_cooldown": 2.0,
        "projectile_speed": 200,
        "form_switch_interval": 5.0,
    },
    
    # bsl - 隐身敌人，远离玩家时透明，靠近才出现
    "bsl": {
        "health": 150,
        "damage": 35,
        "speed": 120,
        "score_value": 250,
        "animation_speed": 0.0333,
        "scale": 1.0,
        "visibility_range": 100,
        "visibility_fade_range": 33,
    },
    
    # xiniu - 疾跑敌人，靠近玩家时加速奔跑
    "xiniu": {
        "health": 100,
        "damage": 45,
        "speed": 100,
        "score_value": 180,
        "animation_speed": 0.0333,
        "scale": 1.0,
        "charge_range": 200,
        "charge_speed_multiplier": 1.8,
    },
    
    # ap - 愤怒敌人，生命值低于50%时切换愤怒形态
    "ap": {
        "health": 200,
        "damage": 30,
        "speed": 80,
        "score_value": 300,
        "animation_speed": 0.0333,
        "scale": 1.0,
        "enrage_damage_multiplier": 2.0,
        "enrage_speed_multiplier": 1.5,
    },
    
    # plant - 固定炮台敌人，不移动，根据距离发射不同弹幕
    "plant": {
        "health": 180,
        "damage": 0,
        "speed": 0,
        "score_value": 250,
        "animation_speed": 0.0333,
        "scale": 1.0,
        "attack_cooldown": 1.5,
        "attack_cooldown_near": 0.8,
        "near_range": 250,
        "bullet_speed": 200,
        "bullet_damage": 20,
    },
    
    # fly - 飞行敌人，有碰撞伤害，发射减速子弹
    "fly": {
        "health": 90,
        "damage": 30,
        "speed": 140,
        "score_value": 200,
        "animation_speed": 0.0333,
        "scale": 0.35,
        "attack_range": 500,
        "min_attack_range": 150,
        "attack_cooldown": 2.0,
        "bullet_speed": 220,
        "bullet_damage": 25,
        "slow_percent": 0.4,
        "slow_duration": 3.0,
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