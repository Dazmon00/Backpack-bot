# 设置错误操作
$ErrorActionPreference = "Stop"

Write-Host "===================================="
Write-Host "Backpack Grid Bot 安装程序"
Write-Host "===================================="
Write-Host

# 检查是否以管理员权限运行
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "请以管理员权限运行此脚本！"
    Write-Host "右键点击 PowerShell，选择'以管理员身份运行'"
    pause
    exit
}

# 设置项目目录
$PROJECT_DIR = "$env:USERPROFILE\backpack-grid-bot"

# 检查是否安装了 Python
try {
    $pythonVersion = python --version
    Write-Host "已安装 Python: $pythonVersion"
} catch {
    Write-Host "正在下载 Python 安装程序..."
    $pythonUrl = "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe"
    $pythonInstaller = "$env:TEMP\python-3.11.8-amd64.exe"
    
    try {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
        Write-Host "正在安装 Python..."
        Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
        Remove-Item $pythonInstaller
        Write-Host "Python 安装完成"
    } catch {
        Write-Host "Python 安装失败，请手动安装 Python 3.11.8"
        Write-Host "错误信息: $_"
        pause
        exit
    }
}

# 检查是否安装了 Git
try {
    $gitVersion = git --version
    Write-Host "已安装 Git: $gitVersion"
} catch {
    Write-Host "正在下载 Git 安装程序..."
    $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe"
    $gitInstaller = "$env:TEMP\Git-2.44.0-64-bit.exe"
    
    try {
        Invoke-WebRequest -Uri $gitUrl -OutFile $gitInstaller
        Write-Host "正在安装 Git..."
        Start-Process -FilePath $gitInstaller -ArgumentList "/VERYSILENT /NORESTART" -Wait
        Remove-Item $gitInstaller
        Write-Host "Git 安装完成"
    } catch {
        Write-Host "Git 安装失败，请手动安装 Git"
        Write-Host "错误信息: $_"
        pause
        exit
    }
}

# 创建项目目录
if (-not (Test-Path $PROJECT_DIR)) {
    Write-Host "正在创建项目目录..."
    New-Item -ItemType Directory -Path $PROJECT_DIR | Out-Null
}

# 进入项目目录
Set-Location $PROJECT_DIR

# 克隆仓库
if (-not (Test-Path ".git")) {
    Write-Host "正在从GitHub下载代码..."
    try {
        git clone https://github.com/Dazmon00/Backpack-bot.git .
    } catch {
        Write-Host "代码下载失败，请检查网络连接"
        Write-Host "错误信息: $_"
        pause
        exit
    }
}

# 创建虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "正在创建虚拟环境..."
    python -m venv venv
}

# 激活虚拟环境
Write-Host "正在激活虚拟环境..."
& "$PROJECT_DIR\venv\Scripts\Activate.ps1"

# 安装依赖
Write-Host "正在安装依赖..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# 检查是否存在 .env 文件
if (-not (Test-Path ".env")) {
    Write-Host "正在创建.env文件..."
    @"
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
"@ | Out-File -FilePath ".env" -Encoding UTF8
    
    Write-Host "已创建.env文件，请编辑该文件并填入您的API密钥和其他配置"
    notepad .env
}

# 创建桌面快捷方式
Write-Host "正在创建桌面快捷方式..."
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Backpack Grid Bot.lnk")
$Shortcut.TargetPath = "$PROJECT_DIR\start_bot.bat"
$Shortcut.WorkingDirectory = $PROJECT_DIR
$Shortcut.Save()

Write-Host
Write-Host "===================================="
Write-Host "安装完成！"
Write-Host
Write-Host "请按照以下步骤操作："
Write-Host "1. 编辑 .env 文件，填入您的API密钥和配置"
Write-Host "2. 双击桌面上的"Backpack Grid Bot"快捷方式启动机器人"
Write-Host "===================================="
Write-Host

pause 