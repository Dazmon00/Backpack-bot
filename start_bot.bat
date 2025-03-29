@echo off
setlocal enabledelayedexpansion

echo ====================================
echo Backpack Grid Bot 启动脚本
echo ====================================
echo.

:: 检查是否已安装 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python未安装，正在检查是否已下载安装程序...
    
    :: 检查是否已下载 Python 安装程序
    if not exist "python-3.11.8-amd64.exe" (
        echo 正在下载Python安装程序...
        powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe' -OutFile 'python-3.11.8-amd64.exe'}"
    )
    
    echo 正在安装Python...
    start /wait python-3.11.8-amd64.exe /quiet InstallAllUsers=1 PrependPath=1
    
    :: 刷新环境变量
    call RefreshEnv.cmd
    
    :: 验证安装
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo Python安装失败，请手动安装Python 3.11.8
        pause
        exit /b 1
    )
)

:: 检查是否已安装虚拟环境
python -m venv --help >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装虚拟环境模块...
    python -m pip install --upgrade pip
    python -m pip install virtualenv
)

:: 检查是否存在虚拟环境
if not exist "venv" (
    echo 正在创建虚拟环境...
    python -m venv venv
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 检查是否已安装依赖
echo 正在检查并安装依赖...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 检查是否存在 .env 文件
if not exist ".env" (
    echo 未找到.env文件，正在创建模板...
    (
        echo # Backpack API配置
        echo BACKPACK_API_KEY=your_api_key_here
        echo BACKPACK_API_SECRET=your_api_secret_here
        echo.
        echo # ETH现货交易配置
        echo ETH_SPOT_ENABLED=true
        echo ETH_SPOT_SYMBOL=ETH_USDC
        echo ETH_SPOT_LOWER_PRICE=1400
        echo ETH_SPOT_UPPER_PRICE=2500
        echo ETH_SPOT_GRID_NUMBER=30
        echo ETH_SPOT_TOTAL_INVESTMENT=1000
        echo ETH_SPOT_CHECK_INTERVAL=10
        echo ETH_SPOT_MIN_PROFIT=0.5
        echo.
        echo # 日志配置
        echo LOG_LEVEL=INFO
    ) > .env
    
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