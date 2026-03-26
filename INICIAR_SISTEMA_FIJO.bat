@echo off
cd /d "C:\Users\LENOVO\Desktop\SISTEMA_WEB_VASCONIA"
title INGRESOS VASCONIA
color 0A
cls

echo ========================================
echo    INICIANDO SISTEMA - VERSIÓN FIJA
echo ========================================
echo.

REM Verificar que la base de datos está en el lugar correcto
if not exist "base_vasconia.db" (
    echo ⚠️  No hay base de datos, se creará una nueva
) else (
    echo ✅ Base de datos encontrada: %CD%\base_vasconia.db
)

REM Matar procesos anteriores
taskkill /F /IM servidor.exe 2>nul

REM Iniciar servidor
echo Iniciando servidor...
start /B servidor.exe
timeout /t 5 /nobreak >nul

REM Obtener IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do set "IP=%%a"
set "IP=%IP: =%"

cls
echo ========================================
echo    ✅ SISTEMA INICIADO CORRECTAMENTE
echo ========================================
echo.
echo 📁 Carpeta: %CD%
echo 📦 Base de datos: %CD%\base_vasconia.db
echo.
echo 🔐 Usuario: admin
echo 🔐 Contraseña: vasconia2026
echo.
echo 🌐 IP local: %IP%
echo 📡 URL para otros: http://%IP%:5001
echo.
echo ========================================
echo.
echo Esta ventana se cerrará en 20 segundos...
timeout /t 20 /nobreak >nul
exit