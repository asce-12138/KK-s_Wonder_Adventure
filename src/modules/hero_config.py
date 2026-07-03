"""
英雄配置模块
定义不同英雄的基础属性和能力
"""

# 默认英雄配置（忍者蛙）
DEFAULT_HERO_CONFIG = {
    "name": "忍者蛙",
    "description": "平衡型英雄，适合初学者",
    "animations": {
        "idle": {
            "sprite_sheet": "images/player/Ninja_frog_Idle_32x32.png",
            "frame_count": 11,
            "frame_duration": 0.0333,
            "frame_width": 32,
            "frame_height": 32
        },
        "run": {
            "sprite_sheet": "images/player/Ninja_frog_Run_32x32.png",
            "frame_count": 12,
            "frame_duration": 0.0333,
            "frame_width": 32,
            "frame_height": 32
        },
        "hurt": {
            "sprite_sheet": "images/player/Ninja_frog_Hit_32x32.png",
            "frame_count": 7,
            "frame_duration": 0.0333,
            "frame_width": 32,
            "frame_height": 32
        }
    },
    "base_stats": {
        "max_health": 100,
        "speed": 250,
        "defense": 0,
        "health_regen": 0,
        "exp_multiplier": 1.0,
        "pickup_range": 50,
        "attack_power": 1.0,
        "luck": 1.0
    },
    "starting_weapon": "frost_nova",
    "unlock_condition": None  # 默认解锁
}

# 英雄配置字典
HERO_CONFIGS = {
    "ninja_frog": DEFAULT_HERO_CONFIG,
    
    "kk": {
        "name": "KK ",
        "description": "使用KK_RUN跑步精灵图的敏捷型英雄",
        "animations": {
            "idle": {
                "sprite_sheet": "images/player/KK_Idle_2.png",
                "frame_count": 1,
                "frame_duration": 0.1,
                "frame_width": 145,
                "frame_height": 224
            },
            "run": {
                "sprite_sheet": "images/player/KK_RUN.png",
                "frame_count": 8,
                "frame_duration": 0.1,
                "frame_width": 145,
                "frame_height": 224
            },
            "hurt": {
                "sprite_sheet": "images/player/KK_Idle.png",
                "frame_count": 1,
                "frame_duration": 0.1,
                "frame_width": 145,
                "frame_height": 224
            }
        },
        "base_stats": {
            "max_health": 90,
            "speed": 260,
            "defense": 0,
            "health_regen": 0.2,
            "exp_multiplier": 1.0,
            "pickup_range": 100,
            "attack_power": 1.0,
            "luck": 1.1
        },
        "scale_factor": 0.25,  # 129x224 -> 约 32x56，与其他角色宽度一致
        "starting_weapon": "knife",
        "unlock_condition": None  # 默认解锁
    },
    
    "pink_man": {
        "name": "少萝",
        "description": "精通元素魔法的小萝莉，攻击范围广",
        "scale_factor": 1.5,
        "animations": {
            "idle": {
                "sprite_sheet": "images/player/Loli_Mage_Idle_32x32.png",
                "frame_count": 1,
                "frame_duration": 0.0333,
                "frame_width": 32,
                "frame_height": 32
            },
            "run": {
                "sprite_sheet": "images/player/Loli_Mage_Run_32x32.png",
                "frame_count": 4,
                "frame_duration": 0.15,
                "frame_width": 32,
                "frame_height": 32
            },
            "hurt": {
                "sprite_sheet": "images/player/Pink_Man_Hit_32x32.png",
                "frame_count": 7,
                "frame_duration": 0.0333,
                "frame_width": 32,
                "frame_height": 32  
            }
        },
        "base_stats": {
            "max_health": 100,
            "speed": 200,
            "defense": 0.1,
            "health_regen": 0.6,
            "exp_multiplier": 1.1,
            "pickup_range": 40,
            "attack_power": 1.2,
            "luck": 1.1
        },
        "starting_weapon": "fireball",
        "unlock_condition": "collect_1000_coins"
    }
}

def get_hero_config(hero_type):
    """
    获取指定英雄的配置
    
    Args:
        hero_type: 英雄类型
        
    Returns:
        dict: 英雄配置字典
    """
    return HERO_CONFIGS.get(hero_type, DEFAULT_HERO_CONFIG)

def get_available_heroes():
    """
    获取所有可用英雄类型
    
    Returns:
        list: 英雄类型列表
    """
    return list(HERO_CONFIGS.keys()) 