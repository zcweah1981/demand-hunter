@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
set "FRONTEND_PORT=%~1"
set "BACKEND_PORT=%~2"

if "%FRONTEND_PORT%"=="" set "FRONTEND_PORT=3100"
if "%BACKEND_PORT%"=="" set "BACKEND_PORT=8100"

set "API_URL=http://localhost:%BACKEND_PORT%"
set "DATA_DIR=%ROOT%local-data\vps-20260611-024644"
if not exist "%DATA_DIR%\demand_hunter.sqlite" set "DATA_DIR=%ROOT%data"

echo Demand Hunter local source deploy
echo Frontend: http://localhost:%FRONTEND_PORT%
echo Backend : %API_URL%
echo Data dir: %DATA_DIR%
echo.

call :kill_port %FRONTEND_PORT%
call :kill_port %BACKEND_PORT%

if not exist "%ROOT%backend\.venv\Scripts\python.exe" (
  echo Creating backend virtual environment...
  py -3 -m venv "%ROOT%backend\.venv"
)

echo Installing backend dependencies...
pushd "%ROOT%backend"
".venv\Scripts\python.exe" -m pip install -r requirements.txt
popd

if not exist "%ROOT%frontend\node_modules" (
  echo Installing frontend dependencies...
  pushd "%ROOT%frontend"
  npm install
  popd
)

echo Starting backend...
start "Demand Hunter Backend" /D "%ROOT%backend" cmd /k "set DEMAND_HUNTER_DATA_DIR=%DATA_DIR%&& set DEMAND_HUNTER_AUTO_WORKER=false&& .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port %BACKEND_PORT%"

timeout /t 2 /nobreak >nul

echo Starting frontend...
start "Demand Hunter Frontend" /D "%ROOT%frontend" cmd /k "set NEXT_PUBLIC_API_URL=%API_URL%&& set INTERNAL_API_URL=%API_URL%&& npx next dev -H 0.0.0.0 -p %FRONTEND_PORT%"

echo.
echo Local deploy started:
echo   http://localhost:%FRONTEND_PORT%
echo.
exit /b 0

:kill_port
set "PORT=%~1"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  echo Killing process %%P on port %PORT%...
  taskkill /PID %%P /F >nul 2>nul
)
exit /b 0
