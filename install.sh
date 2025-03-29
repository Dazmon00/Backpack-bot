#!/bin/bash

echo "===================================="
echo "Backpack Grid Bot 安装程序"
echo "===================================="
echo

# 检查是否安装了 Python
if ! command -v python3 &> /dev/null; then
    echo "正在安装 Python..."
    if command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y python3 python3-pip python3-venv
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3 python3-pip python3-venv
    else
        echo "无法确定包管理器，请手动安装 Python 3"
        exit 1
    fi
fi

# 检查是否安装了 Git
if ! command -v git &> /dev/null; then
    echo "正在安装 Git..."
    if command -v apt &> /dev/null; then
        sudo apt install -y git
    elif command -v yum &> /dev/null; then
        sudo yum install -y git
    else
        echo "无法确定包管理器，请手动安装 Git"
        exit 1
    fi
fi

# 创建项目目录
PROJECT_DIR="$HOME/backpack-grid-bot"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "正在创建项目目录..."
    mkdir -p "$PROJECT_DIR"
fi

# 进入项目目录
cd "$PROJECT_DIR"

# 克隆仓库
if [ ! -d ".git" ]; then
    echo "正在从GitHub下载代码..."
    git clone https://github.com/Dazmon00/Backpack-bot.git .
fi

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "正在创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "正在安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 检查是否存在 .env 文件
if [ ! -f ".env" ]; then
    echo "正在创建.env文件..."
    cat > .env << EOL
# Backpack API配置
BACKPACK_API_KEY=your_api_key_here
BACKPACK_API_SECRET=your_api_secret_here

# ETH现货交易配置
ETH_SPOT_ENABLED=true
ETH_SPOT_SYMBOL=ETH_USDC
ETH_SPOT_LOWER_PRICE=1400
ETH_SPOT_UPPER_PRICE=2500
ETH_SPOT_GRID_NUMBER=30
ETH_SPOT_TOTAL_INVESTMENT=1000
ETH_SPOT_CHECK_INTERVAL=10
ETH_SPOT_MIN_PROFIT=0.5

# 日志配置
LOG_LEVEL=INFO
EOL
    
    echo "已创建.env文件，请编辑该文件并填入您的API密钥和其他配置"
    if command -v nano &> /dev/null; then
        nano .env
    elif command -v vim &> /dev/null; then
        vim .env
    else
        echo "请使用您喜欢的编辑器编辑 .env 文件"
    fi
fi

# 创建启动脚本
cat > start_bot.sh << EOL
#!/bin/bash
cd "$PROJECT_DIR"
source venv/bin/activate
python main.py
EOL

chmod +x start_bot.sh

# 创建桌面快捷方式
if [ -d "$HOME/Desktop" ]; then
    cat > "$HOME/Desktop/Backpack Grid Bot.desktop" << EOL
[Desktop Entry]
Version=1.0
Type=Application
Name=Backpack Grid Bot
Exec="$PROJECT_DIR/start_bot.sh"
Icon=terminal
Terminal=true
Categories=Utility;
EOL
    chmod +x "$HOME/Desktop/Backpack Grid Bot.desktop"
fi

echo
echo "===================================="
echo "安装完成！"
echo
echo "请按照以下步骤操作："
echo "1. 编辑 .env 文件，填入您的API密钥和配置"
echo "2. 双击桌面上的"Backpack Grid Bot"图标或运行 ./start_bot.sh 启动机器人"
echo "===================================="
echo 