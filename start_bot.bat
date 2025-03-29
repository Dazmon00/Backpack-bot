@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ====================================
echo Backpack Grid Bot 启动脚本
echo ====================================
echo.

:: 检查是否已安装 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python未安装，请先安装Python 3.8或更高版本
    echo 您可以从 https://www.python.org/downloads/ 下载Python
    pause
    exit /b 1
)

:: 检查是否存在虚拟环境
if not exist "venv" (
    echo 正在创建虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo 创建虚拟环境失败
        pause
        exit /b 1
    )
)

:: 激活虚拟环境
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo 激活虚拟环境失败
    pause
    exit /b 1
)

:: 安装依赖
echo 正在安装依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 安装依赖失败
    pause
    exit /b 1
)

:: 检查是否存在 .env 文件
if not exist ".env" (
    echo 未找到.env文件，正在创建模板...
    echo # Backpack API配置 > .env
    echo BACKPACK_API_KEY=your_api_key_here >> .env
    echo BACKPACK_API_SECRET=your_api_secret_here >> .env
    echo. >> .env
    echo # ETH现货交易配置 >> .env
    echo ETH_SPOT_ENABLED=true >> .env
    echo ETH_SPOT_SYMBOL=ETH_USDC >> .env
    echo ETH_SPOT_LOWER_PRICE=1400 >> .env
    echo ETH_SPOT_UPPER_PRICE=2500 >> .env
    echo ETH_SPOT_GRID_NUMBER=30 >> .env
    echo ETH_SPOT_TOTAL_INVESTMENT=1000 >> .env
    echo ETH_SPOT_CHECK_INTERVAL=10 >> .env
    echo ETH_SPOT_MIN_PROFIT=0.5 >> .env
    echo. >> .env
    echo # 日志配置 >> .env
    echo LOG_LEVEL=INFO >> .env
    
    echo 已创建.env模板文件，请编辑该文件并填入您的API密钥和其他配置
    notepad .env
    pause
)

:: 启动机器人
echo 正在启动网格交易机器人...
python main.py

:: 如果发生错误，暂停显示错误信息
if %errorlevel% neq 0 (
    echo 机器人运行出错，请检查错误信息
    pause
)

:: 退出虚拟环境
deactivate

pause 