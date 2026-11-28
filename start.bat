@echo off
chcp 65001 >nul
setlocal
title DnD Master

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

set "RUN_DIR=%ROOT%\.run"
set "BACKEND_PID_FILE=%RUN_DIR%\backend.pid"
set "FRONTEND_PID_FILE=%RUN_DIR%\frontend.pid"

if /i "%~1"=="stop" goto :stop
if /i "%~1"=="--no-browser" set "NO_BROWSER=1"

echo [1/5] Проверка окружения
where docker >nul 2>&1 || goto :missing_docker
where uv >nul 2>&1 || goto :missing_uv
where npm.cmd >nul 2>&1 || goto :missing_npm

docker info >nul 2>&1
if errorlevel 1 goto :docker_off

if not exist "%ROOT%\backend\.env" call :create_env
if not exist "%RUN_DIR%" mkdir "%RUN_DIR%"

echo [2/5] Запуск PostgreSQL
docker compose -f "%ROOT%\backend\docker-compose.yml" up -d db
if errorlevel 1 goto :db_failed

set "DB_READY="
for /l %%i in (1,1,30) do (
    if not defined DB_READY (
        docker compose -f "%ROOT%\backend\docker-compose.yml" exec -T db pg_isready -U dnd -d dnd >nul 2>&1
        if not errorlevel 1 set "DB_READY=1"
        if not defined DB_READY ping -n 3 127.0.0.1 >nul 2>&1
    )
)
if not defined DB_READY goto :db_failed

if not exist "%ROOT%\backend\.venv" (
    echo Установка зависимостей backend
    pushd "%ROOT%\backend"
    call uv sync
    if errorlevel 1 (
        popd
        goto :uv_failed
    )
    popd
)

echo [3/5] Миграции базы данных
pushd "%ROOT%\backend"
call uv run alembic upgrade head
if errorlevel 1 (
    popd
    goto :migrate_failed
)
popd

if not exist "%ROOT%\frontend\node_modules" (
    echo Установка зависимостей frontend, это может занять пару минут
    pushd "%ROOT%\frontend"
    call npm.cmd install
    if errorlevel 1 (
        popd
        goto :npm_failed
    )
    popd
)

echo [4/5] Запуск backend на http://localhost:8000
call :is_running "%BACKEND_PID_FILE%"
if defined RUNNING goto :backend_started
for /f "usebackq delims=" %%p in (`powershell -NoProfile -Command "(Start-Process -FilePath 'cmd.exe' -ArgumentList '/k','title DnD Master: backend && uv run uvicorn app.main:app --reload --port 8000 --loop app.core.loop:selector_loop_factory' -WorkingDirectory '%ROOT%\backend' -PassThru).Id"`) do set "BACKEND_PID=%%p"
if defined BACKEND_PID >"%BACKEND_PID_FILE%" echo %BACKEND_PID%
:backend_started

set "API_READY="
for /l %%i in (1,1,45) do (
    if not defined API_READY (
        curl.exe -s -f -o nul http://localhost:8000/health >nul 2>&1
        if not errorlevel 1 set "API_READY=1"
        if not defined API_READY ping -n 3 127.0.0.1 >nul 2>&1
    )
)
if not defined API_READY echo Внимание: API не ответил за 90 секунд, смотрите окно backend

echo [5/5] Запуск frontend на http://localhost:5173
call :is_running "%FRONTEND_PID_FILE%"
if defined RUNNING goto :frontend_started
for /f "usebackq delims=" %%p in (`powershell -NoProfile -Command "(Start-Process -FilePath 'cmd.exe' -ArgumentList '/k','title DnD Master: frontend && npm run dev' -WorkingDirectory '%ROOT%\frontend' -PassThru).Id"`) do set "FRONTEND_PID=%%p"
if defined FRONTEND_PID >"%FRONTEND_PID_FILE%" echo %FRONTEND_PID%
:frontend_started

powershell -NoProfile -Command "$ok = $false; for ($i = 0; $i -lt 60 -and -not $ok; $i++) { foreach ($h in @('localhost','127.0.0.1','::1')) { try { $tcp = New-Object Net.Sockets.TcpClient; $tcp.Connect($h, 5173); $tcp.Close(); $ok = $true; break } catch { } }; if (-not $ok) { Start-Sleep -Milliseconds 500 } }; if ($ok) { exit 0 } else { exit 1 }"
if not defined NO_BROWSER start "" http://localhost:5173

echo.
echo Проект запущен.
echo   Интерфейс: http://localhost:5173
echo   API:       http://localhost:8000/docs
echo   Остановка: start.bat stop
echo.
pause
exit /b 0

:is_running
set "RUNNING="
if not exist "%~1" exit /b 0
set "PID_VALUE="
for /f "usebackq delims=" %%p in ("%~1") do set "PID_VALUE=%%p"
if not defined PID_VALUE exit /b 0
powershell -NoProfile -Command "if (Get-Process -Id %PID_VALUE% -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 set "RUNNING=1"
exit /b 0

:create_env
set "ENV_FILE=%ROOT%\backend\.env"
copy /y "%ROOT%\backend\.env.example" "%ENV_FILE%" >nul
powershell -NoProfile -Command "$p = $env:ENV_FILE; $t = [System.IO.File]::ReadAllText($p); $t = $t -replace 'postgresql\+psycopg://USER:PASSWORD@localhost:5433/DB_NAME', 'postgresql+psycopg://dnd:dnd@localhost:5433/dnd'; [System.IO.File]::WriteAllText($p, $t)"
echo Внимание: создан backend\.env с локальной базой dnd/dnd
echo Впишите LLM_API_KEY в backend\.env, иначе чат вернёт 503
exit /b 0

:stop
echo Остановка frontend и backend
call :kill_pid_file "%FRONTEND_PID_FILE%"
call :kill_pid_file "%BACKEND_PID_FILE%"
taskkill /FI "WINDOWTITLE eq DnD Master: frontend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq DnD Master: backend*" /T /F >nul 2>&1
echo Остановка PostgreSQL
docker compose -f "%ROOT%\backend\docker-compose.yml" stop db
echo Готово. Данные базы сохранены в docker volume
pause
exit /b 0

:kill_pid_file
if not exist "%~1" exit /b 0
for /f "usebackq delims=" %%p in ("%~1") do taskkill /PID %%p /T /F >nul 2>&1
del /q "%~1" >nul 2>&1
exit /b 0

:missing_docker
echo Ошибка: не найден Docker. Установите Docker Desktop.
goto :fail

:missing_uv
echo Ошибка: не найден uv. Установите: https://docs.astral.sh/uv/
goto :fail

:missing_npm
echo Ошибка: не найден npm. Установите Node.js 22 или новее.
goto :fail

:docker_off
echo Ошибка: Docker Engine недоступен. Запустите Docker Desktop и повторите.
goto :fail

:db_failed
echo Ошибка: не удалось запустить PostgreSQL в Docker.
goto :fail

:uv_failed
echo Ошибка: не удалось установить зависимости backend.
goto :fail

:migrate_failed
echo Ошибка: не удалось применить миграции. Проверьте backend\.env и вывод alembic.
goto :fail

:npm_failed
echo Ошибка: не удалось установить зависимости frontend.
goto :fail

:fail
pause
exit /b 1
