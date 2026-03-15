@echo off
echo ============================================
echo    RALOZ WEB - PASO 2: CREAR TABLAS
echo ============================================
echo.

cd /d "%~dp0backend"

echo [1/2] Creando tablas en Supabase...
set FLASK_APP=run.py
flask init-db
if %errorlevel% neq 0 (
    echo.
    echo ERROR al crear tablas.
    echo Verifica que el archivo .env tenga la URL correcta de Supabase.
    pause
    exit /b 1
)
echo    OK
echo.

echo [2/2] Insertando datos iniciales...
flask seed
echo    OK
echo.

echo ============================================
echo    TABLAS CREADAS EXITOSAMENTE
echo ============================================
echo.
echo Usuario admin creado:
echo    Usuario: admin
echo    Password: admin123
echo    (CAMBIALO despues del primer login)
echo.
echo Ahora ejecuta: PASO_3_INICIAR.bat
echo.
pause
