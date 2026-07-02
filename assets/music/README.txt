游戏音频资源目录说明
======================

本目录包含游戏所有音频资源，您可以自由替换这些文件。

支持的音频格式：
- MP3 (推荐)
- WAV
- OGG
- FLAC

文件夹结构：
------------
music/
├── bgm/          # 背景音乐
│   ├── menu.mp3      # 主菜单背景音乐
│   └── background.mp3 # 游戏内背景音乐
├── sfx/          # 音效
│   ├── hit.wav       # 击中敌人
│   ├── enemy_death.wav  # 敌人死亡
│   ├── player_hurt.wav  # 玩家受伤
│   ├── level_up.wav     # 升级
│   ├── collect_exp.wav  # 收集经验
│   ├── collect_coin.wav # 收集金币
│   ├── heal.wav         # 治疗
│   ├── upgrade.wav      # 升级选择
│   ├── menu_move.wav    # 菜单移动
│   ├── menu_select.wav  # 菜单选择
│   └── menu_show.wav    # 菜单显示
└── sfx/weapons/  # 武器音效
    ├── knife_throw.wav  # 飞刀投掷
    ├── fireball.wav     # 火球攻击
    └── frost_nova.wav   # 冰霜新星

替换方法：
----------
1. 将您自己的音频文件复制到对应文件夹
2. 确保文件名与上述一致（不含扩展名，程序会自动识别格式）
3. 删除旧文件或直接覆盖
4. 运行游戏即可听到新音频

示例：
- 替换主菜单音乐：将您的音乐文件命名为 menu.mp3 放入 bgm/ 文件夹
- 替换击中音效：将您的音效文件命名为 hit.wav 放入 sfx/ 文件夹

注意事项：
----------
- 文件大小建议控制在合理范围内，过大的文件会影响加载速度
- 推荐使用 44100 Hz 采样率的音频
- 如果缺少某个音频文件，游戏会跳过该音效但不会崩溃