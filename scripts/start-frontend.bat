@echo off
set ROOT_DIR=%~dp0..
pushd "%ROOT_DIR%"

echo ========================================
echo   Chic Chat Admin - Frontend
echo ========================================
echo.

echo [1/3] Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found! Please install Node.js 18 or higher
    pause
    exit /b 1
)
echo ✅ Node.js found

echo.
echo [2/3] Installing frontend dependencies...
npm --prefix frontend install
if errorlevel 1 (
    echo ❌ Failed to install frontend dependencies
    popd
    pause
    exit /b 1
)
echo ✅ Frontend dependencies installed

echo.
echo [3/3] Starting development server...
echo 🚀 Starting Vite development server
echo.
echo ℹ️  The frontend will be available at: http://localhost:5173
echo ℹ️  Make sure the backend is running on: http://127.0.0.1:8000
echo ℹ️  Press Ctrl+C to stop the server
echo.

npm --prefix frontend run dev

popd
