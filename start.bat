@echo off
echo Starting Backpack Grid Trading Bot...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher
    pause
    exit /b 1
)

REM 检查.env文件是否存在
if not exist .env (
    echo Error: .env file not found
    echo Please copy .env.example to .env and configure your settings
    pause
    exit /b 1
)

REM 检查依赖是否安装
echo Checking dependencies...
pip show ccxt >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM 启动机器人
echo Starting bot...
python grid_trader.py

REM 如果程序异常退出，暂停显示错误信息
if errorlevel 1 (
    echo.
    echo Bot stopped with an error
    pause
)
