@echo off
echo ========================================
echo   Chic Chat Admin - Sales Analytics
echo ========================================
echo.

echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.8 or higher
    pause
    exit /b 1
)
echo ✅ Python found

echo.
echo [2/4] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install Python dependencies
    pause
    exit /b 1
)
echo ✅ Python dependencies installed

echo.
echo [3/4] Checking .env file...
if not exist .env (
    echo ⚠️  .env file not found! Creating from template...
    copy .env.example .env
    echo 📝 Please edit .env file and add your GEMINI_API_KEY
    echo 🔑 Get your free API key from: https://makersuite.google.com/app/apikey
    pause
)
echo ✅ Environment configuration ready

echo.
echo [4/4] Starting backend server...
echo 🚀 Starting Flask server on http://127.0.0.1:8000
echo.
echo ℹ️  Keep this window open while using the application
echo ℹ️  The frontend will run on http://localhost:5173
echo ℹ️  Press Ctrl+C to stop the server
echo.

python flask_server.py
