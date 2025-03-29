# Backpack Grid Trading Bot

这是一个用于 Backpack 交易所的网格交易机器人，支持 ETH/USDC 现货交易。

## 功能特点

- 自动检测并安装 Python 环境
- 自动创建虚拟环境并安装依赖
- 支持自定义价格区间和网格数量
- 支持自定义投资金额
- 自动计算买入和卖出数量
- 详细的日志记录
- 支持 Windows 和 Linux 一键启动

## 快速安装

### Windows 安装

#### 方法一：一键安装（推荐）

1. 打开命令提示符（CMD）
2. 复制并运行以下命令：
```bash
powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Dazmon00/Backpack-bot/main/install.cmd' -OutFile 'install.cmd'}"; .\install.cmd
```

这个命令会自动：
- 下载并安装必要的软件（Python、Git等）
- 创建项目目录
- 下载最新代码
- 设置虚拟环境
- 安装依赖包
- 创建配置文件
- 创建桌面快捷方式

#### 方法二：手动安装

1. 下载项目文件：
   ```bash
   git clone https://github.com/Dazmon00/Backpack-bot.git
   cd Backpack-bot
   ```

2. 运行启动脚本：
   - 双击运行 `start_bot.bat`
   - 首次运行时会自动：
     - 下载并安装 Python（如果需要）
     - 创建虚拟环境
     - 安装必要的包
     - 创建 `.env` 配置文件模板

### Linux 安装

#### 方法一：一键安装（推荐）

1. 打开终端
2. 复制并运行以下命令：
```bash
curl -s https://raw.githubusercontent.com/Dazmon00/Backpack-bot/main/install.sh | bash
```

或者：
```bash
wget -qO- https://raw.githubusercontent.com/Dazmon00/Backpack-bot/main/install.sh | bash
```

这个命令会自动：
- 安装必要的软件（Python、Git等）
- 创建项目目录
- 下载最新代码
- 设置虚拟环境
- 安装依赖包
- 创建配置文件
- 创建桌面快捷方式

#### 方法二：手动安装

1. 下载项目文件：
   ```bash
   git clone https://github.com/Dazmon00/Backpack-bot.git
   cd Backpack-bot
   ```

2. 运行安装脚本：
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. 配置 `.env` 文件：
   - 打开 `.env` 文件
   - 填入你的 Backpack API 密钥
   - 根据需要调整其他参数

4. 启动机器人：
   - 双击桌面上的"Backpack Grid Bot"图标
   - 或者在终端中运行 `./start_bot.sh`
   - 查看控制台输出的日志信息

## 配置文件说明

在 `.env` 文件中配置以下参数：

```env
# Backpack API配置
BACKPACK_API_KEY=你的API密钥
BACKPACK_API_SECRET=你的API密钥

# ETH现货交易配置
ETH_SPOT_ENABLED=true
ETH_SPOT_SYMBOL=ETH_USDC
ETH_SPOT_LOWER_PRICE=1400    # 最低价格
ETH_SPOT_UPPER_PRICE=2500    # 最高价格
ETH_SPOT_GRID_NUMBER=30      # 网格数量
ETH_SPOT_TOTAL_INVESTMENT=1000  # 总投资金额(USDC)
ETH_SPOT_CHECK_INTERVAL=10   # 检查间隔(秒)
ETH_SPOT_MIN_PROFIT=0.5      # 最小利润百分比

# 日志配置
LOG_LEVEL=INFO
```

## 注意事项

1. 首次运行需要管理员权限（用于安装 Python）
2. 确保网络连接正常
3. 请妥善保管 API 密钥
4. 建议先用小额资金测试
5. 定期检查日志文件了解运行状态

## 文件说明

- `main.py`: 主程序入口
- `backpack_exchange.py`: Backpack 交易所接口
- `grid_bot.py`: 网格交易逻辑
- `start_bot.bat`: Windows 启动脚本
- `start_bot.sh`: Linux 启动脚本
- `install.bat`: Windows 安装脚本
- `install.sh`: Linux 安装脚本
- `download.bat`: 下载脚本
- `install.cmd`: 一键安装命令
- `requirements.txt`: Python 包依赖
- `.env`: 配置文件（需要自行创建）
- `logs/`: 日志文件目录

## 更新日志

### v1.0.0
- 初始版本发布
- 支持 ETH/USDC 现货网格交易
- 自动环境配置
- Windows 和 Linux 一键启动
- 支持一键安装功能

## 许可证

MIT License 