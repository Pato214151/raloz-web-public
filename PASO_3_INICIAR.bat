@echo off
echo ============================================
echo    RALOZ WEB - INICIANDO SISTEMA
echo ============================================
echo.
echo Abriendo Backend y Frontend...
echo.

:: Iniciar Backend en una ventana
start "RALOZ Backend" cmd /k "cd /d "%~dp0backend" && echo BACKEND INICIANDO... && python run.py"

:: Esperar 3 segundos para que el backend arranque
timeout /t 3 /nobreak >nul

:: Iniciar Frontend en otra ventana
start "RALOZ Frontend" cmd /k "cd /d "%~dp0frontend" && echo FRONTEND INICIANDO... && npm run dev"

:: Esperar 5 segundos y abrir el navegador
timeout /t 5 /nobreak >nul
start http://localhost:5173

echo.
echo ============================================
echo    RALOZ WEB ESTA CORRIENDO
echo ============================================
echo.
echo    Abre: http://localhost:5173
echo.
echo    Login:
echo       Usuario: admin
echo       Password: admin123
echo.
echo    Para detener: cierra las 2 ventanas negras
echo.
pause
