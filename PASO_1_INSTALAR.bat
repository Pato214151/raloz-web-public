@echo off
echo ============================================
echo    RALOZ WEB - PASO 1: INSTALAR TODO
echo ============================================
echo.

echo [1/3] Verificando Python...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado o no esta en PATH
    echo Descarga Python de https://python.org
    pause
    exit /b 1
)
echo    OK
echo.

echo [2/3] Instalando dependencias del Backend (Flask)...
cd /d "%~dp0backend"
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERROR al instalar dependencias Python
    echo Intenta: pip install flask flask-sqlalchemy flask-cors flask-jwt-extended bcrypt psycopg2-binary python-dotenv bleach flask-migrate flask-limiter google-auth google-auth-oauthlib gunicorn marshmallow
    pause
    exit /b 1
)
echo    OK - Dependencias Python instaladas
echo.

echo [3/3] Verificando Node.js...
node --version
if %errorlevel% neq 0 (
    echo.
    echo Node.js NO esta instalado.
    echo Descargalo de: https://nodejs.org/es
    echo Instala la version LTS y luego ejecuta este script de nuevo.
    echo.
    echo El backend YA esta listo. Solo falta Node.js para el frontend.
    pause
    exit /b 1
)

echo Instalando dependencias del Frontend (React)...
cd /d "%~dp0frontend"
call npm install
if %errorlevel% neq 0 (
    echo ERROR al instalar dependencias del frontend
    pause
    exit /b 1
)
echo    OK - Dependencias Frontend instaladas
echo.

echo ============================================
echo    INSTALACION COMPLETADA
echo ============================================
echo.
echo Ahora ejecuta: PASO_2_CREAR_TABLAS.bat
echo.
pause
