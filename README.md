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

### 🎯 场景一：队友第一次拉取代码
#### 第 1 步：克隆仓库
```
# 队友需要先安装 Git 和 Python 3.11
# 安装 Git
winget install Git.Git
# 进入你想存放项目的目录（比如桌面）
cd C:\Users\DELL\Desktop

# 克隆项目

git clone https://github.com/asce-12138/KK-s_Wonder_Adventure.git
cd KK-s_Wonder_Adventure
```
#### 第 2 步：创建虚拟环境
```
# 在项目根目录执行
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
#### 第 3 步：安装依赖
PowerShell运行

`pip install -r requirements.txt`


#### 第 4 步：运行游戏验证
PowerShell运行

`python src/main.py`
如果游戏能正常启动，说明环境配置成功。

### 🎯 场景二：队友修改代码
修改前：先同步最新代码
PowerShell



运行
git checkout maingit pull origin main

### 🎯 场景三：多个队友同时修改（出现冲突）
如果你们同时修改了同一个文件，推送时会报错：

```
# 先拉取最新代码
git pull origin main

# 如果有冲突，Git 会提示哪些文件冲突
# 打开冲突文件，手动解决冲突（删除 <<<<<<<  ======= >>>>>>> 标记）

# 解决后
git add .
git commit -m "merge: 解决冲突"
git push origin main
```
### 🔧 队友的 Git 基础配置（首次使用必做）
```
git config --global user.name "队友的名字"
git config --global user.email "队友的邮箱"

# 推荐用 SSH（避免每次输密码）：
ssh-keygen -t rsa -b 4096
# 然后把 ~/.ssh/id_rsa.pub 内容添加到 GitHub Settings > SSH Keys

# 修改远程 URL 为 SSH
git remote set-url origin git@github.com:asce-12138/KK-s_Wonder_Adventure.git
```
