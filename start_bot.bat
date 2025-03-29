@echo off
setlocal enabledelayedexpansion

echo ====================================
echo Backpack Grid Bot Startup Script
echo ====================================
echo.

:: Check Python installation
echo Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python 3.8 or higher
    echo You can download Python from https://www.python.org/downloads/
    pause
    exit /b 1
)
echo Python check completed
pause

:: Check virtual environment
echo Checking virtual environment...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
)
echo Virtual environment check completed
pause

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated successfully
pause

:: Check requirements.txt
echo Checking dependencies file...
if not exist "requirements.txt" (
    echo requirements.txt not found
    echo Please make sure you are running this script in the correct directory
    pause
    exit /b 1
)
echo Dependencies file check completed
pause

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installation completed
pause

:: Check .env file
echo Checking configuration file...
if not exist ".env" (
    echo .env file not found, creating template...
    echo # Backpack API Configuration > .env
    echo BACKPACK_API_KEY=your_api_key_here >> .env
    echo BACKPACK_API_SECRET=your_api_secret_here >> .env
    echo. >> .env
    echo # ETH Spot Trading Configuration >> .env
    echo ETH_SPOT_ENABLED=true >> .env
    echo ETH_SPOT_SYMBOL=ETH_USDC >> .env
    echo ETH_SPOT_LOWER_PRICE=1400 >> .env
    echo ETH_SPOT_UPPER_PRICE=2500 >> .env
    echo ETH_SPOT_GRID_NUMBER=30 >> .env
    echo ETH_SPOT_TOTAL_INVESTMENT=1000 >> .env
    echo ETH_SPOT_CHECK_INTERVAL=10 >> .env
    echo ETH_SPOT_MIN_PROFIT=0.5 >> .env
    echo. >> .env
    echo # Logging Configuration >> .env
    echo LOG_LEVEL=INFO >> .env
    
    echo .env template file created. Please edit the file and fill in your API keys and configuration
    notepad .env
    pause
)
echo Configuration file check completed
pause

:: Check main.py
echo Checking main program file...
if not exist "main.py" (
    echo main.py not found
    echo Please make sure you are running this script in the correct directory
    pause
    exit /b 1
)
echo Main program file check completed
pause

:: Start the bot
echo Starting grid trading bot...
python main.py

:: If error occurs, pause to show error message
if %errorlevel% neq 0 (
    echo Bot encountered an error. Please check the error message
    pause
)

:: Deactivate virtual environment
deactivate

echo Program execution completed
pause 