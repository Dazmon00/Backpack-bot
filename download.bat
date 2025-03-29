@echo off
setlocal enabledelayedexpansion

echo ====================================
echo Backpack Grid Bot 下载安装程序
echo ====================================
echo.

:: 设置GitHub仓库地址
set "REPO_URL=https://raw.githubusercontent.com/你的用户名/backpack-grid-bot/main"

:: 创建临时目录
set "TEMP_DIR=%TEMP%\backpack-grid-bot-install"
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
cd "%TEMP_DIR%"

:: 下载安装脚本
echo 正在下载安装程序...
powershell -Command "& {Invoke-WebRequest -Uri '%REPO_URL%/install.bat' -OutFile 'install.bat'}"

:: 运行安装脚本
echo 正在运行安装程序...
call install.bat

:: 清理临时文件
cd "%USERPROFILE%"
rmdir /s /q "%TEMP_DIR%"

echo.
echo ====================================
echo 下载安装完成！
echo ====================================
echo. 