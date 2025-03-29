@echo off
setlocal enabledelayedexpansion

echo ====================================
echo Backpack Grid Bot 安装程序
echo ====================================
echo.

:: 检查是否已安装 Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Git未安装，正在下载Git安装程序...
    
    :: 检查是否已下载 Git 安装程序
    if not exist "Git-2.44.0-64-bit.exe" (
        echo 正在下载Git安装程序...
        powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe' -OutFile 'Git-2.44.0-64-bit.exe'}"
    )
    
    echo 正在安装Git...
    start /wait Git-2.44.0-64-bit.exe /VERYSILENT /NORESTART
    
    :: 刷新环境变量
    call RefreshEnv.cmd
    
    :: 验证安装
    git --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo Git安装失败，请手动安装Git
        pause
        exit /b 1
    )
)

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

:: 创建项目目录
set "PROJECT_DIR=backpack-grid-bot"
if not exist "%PROJECT_DIR%" (
    echo 正在创建项目目录...
    mkdir "%PROJECT_DIR%"
)

:: 进入项目目录
cd "%PROJECT_DIR%"

:: 检查是否已克隆仓库
if not exist ".git" (
    echo 正在从GitHub下载代码...
    git clone https://github.com/你的用户名/backpack-grid-bot.git .
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

:: 创建桌面快捷方式
echo 正在创建桌面快捷方式...
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT=%DESKTOP%\Backpack Grid Bot.lnk"

powershell -Command "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut('%SHORTCUT%'); $SC.TargetPath = '%~dp0start_bot.bat'; $SC.WorkingDirectory = '%~dp0'; $SC.Save()"

echo.
echo ====================================
echo 安装完成！
echo.
echo 请按照以下步骤操作：
echo 1. 编辑 .env 文件，填入您的API密钥和配置
echo 2. 双击桌面上的"Backpack Grid Bot"快捷方式启动机器人
echo ====================================
echo.

pause 