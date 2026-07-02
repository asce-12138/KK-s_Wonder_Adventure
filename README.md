# KK的奇妙冒险

```
game_python/
├── assets/          # 游戏资源文件
│   ├── images/     # 图片资源
│   ├── sounds/     # 音效资源
│   └── fonts/      # 字体资源
├── saves/          # 存档文件夹
├── src/            # 源代码
│   ├── main.py     # 游戏入口
│   └── modules/    # 游戏模块
│       ├── components/      # Player组件
│       ├── enemies/         # 敌人相关
│       ├── weapons/         # 武器相关
│       ├── items/           # 物品相关
│       ├── menus/           # 菜单相关
│       ├── game.py          # 游戏主逻辑
│       ├── hero_config.py   # 不同英雄特性
│       ├── player.py        # 玩家类
│       ├── menu.py          # 菜单基类
│       ├── ui.py            # UI系统
│       ├── utils.py         # 工具函数
│       ├── upgrade_system.py # 升级系统
│       ├── save_system.py   # 存档系统
│       └── resource_manager.py # 资源管理器
├── requirements.txt  # 项目依赖
└── README.md        # 项目说明
```
场景一：第一次拉取代码
第 1 步：克隆仓库
PowerShell
`# 队友需要先安装 Git 和 Python 3.11# 然后在本地任意目录执行：git clone https://github.com/asce-12138/KK-s_Wonder_Adventure.gitcd KK-s_Wonder_Adventure`
第 2 步：创建虚拟环境
PowerShell运行
`# 在项目根目录执行python -m venv .venv.\.venv\Scripts\Activate.ps1`
第 3 步：安装依赖
PowerShell运行
`pip install -r requirements.txt`
第 4 步：运行游戏验证
PowerShell运行
`python src/main.py`
如果游戏能正常启动，说明环境配置成功。
