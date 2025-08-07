@echo off
echo ========================================
echo   Chic Chat Admin - Complete Setup
echo ========================================
echo.

echo Starting complete setup and launch...
echo.

REM Check if .env exists, if not create from template
if not exist .env (
    echo 📝 Creating .env file from template...
    copy .env.example .env
    echo.
    echo ⚠️  IMPORTANT: Please edit the .env file and add your GEMINI_API_KEY
    echo 🔑 Get your free API key from: https://makersuite.google.com/app/apikey
    echo.
    echo Press any key to open .env file for editing...
    pause
    notepad .env
    echo.
    echo Press any key after you've added your API key...
    pause
)

echo 🚀 Starting backend server in a new window...
start cmd /k "cd /d %~dp0 && start-backend.bat"

echo ⏱️  Waiting 5 seconds for backend to start...
timeout /t 5 /nobreak >nul

echo 🌐 Starting frontend in a new window...
start cmd /k "cd /d %~dp0 && start-frontend.bat"

echo.
echo ✅ Setup complete!
echo.
echo 📊 Backend API: http://127.0.0.1:8000
echo 🌐 Frontend UI: http://localhost:5173
echo.
echo 💡 Demo Login Credentials:
echo    Username: admin
echo    Password: admin123
echo.
echo 🎯 Both servers will open in separate windows
echo 🔄 Keep both windows open while using the application
echo ❌ Close this window to stop monitoring
echo.

:monitor
timeout /t 10 /nobreak >nul
echo [%time%] Application running...
goto monitor
