@echo off
setlocal
rem Executa o script PowerShell tambem pelo Prompt de Comando (cmd).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0executar.ps1" %*
exit /b %errorlevel%
