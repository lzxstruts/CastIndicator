@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "SCRIPT=%~dp0wowAutoCast.py"

set "PY="
call :find_python

set "NEED="
if not defined PY (
    set "NEED=1"
) else (
    for %%m in (cv2 numpy pygetwindow win32gui) do (
        !PY! -c "import %%m" >nul 2>nul
        if errorlevel 1 set "NEED=1"
    )
)

rem everything ready: no output at all, just start
if not defined NEED goto :run

rem ================== only prints when something must be installed ==================
if not defined PY (
    echo Python not found, installing Python 3.12 ...
    call :install_python
    call :refresh_path
    call :find_python
    if not defined PY (
        echo [ERROR] Python install failed.
        echo         Install Python 3.8+ manually: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

echo Installing packages ...
!PY! -m pip --version >nul 2>nul
if errorlevel 1 (
    echo Bootstrapping pip ...
    !PY! -m ensurepip --upgrade
)
!PY! -m pip install --upgrade pip
!PY! -m pip install numpy opencv-python pygetwindow pywin32
if errorlevel 1 (
    echo [ERROR] pip install failed.
    echo         !PY! -m pip install numpy opencv-python pygetwindow pywin32
    pause
    exit /b 1
)
echo Done.

rem ================== run ==================
:run
if not exist "%SCRIPT%" (
    echo [ERROR] wowAutoCast.py not found: %SCRIPT%
    pause
    exit /b 1
)

!PY! "%SCRIPT%"
exit /b

rem ================== sub routines ==================

:find_python
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        set "PY=py -3"
        goto :eof
    )
)
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PY=python"
)
if defined PY goto :eof
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%~d\python.exe" set "PY=%%~d\python.exe"
)
for /d %%d in ("%ProgramFiles%\Python3*") do (
    if exist "%%~d\python.exe" set "PY=%%~d\python.exe"
)
goto :eof

:install_python
where winget >nul 2>nul
if not errorlevel 1 (
    winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
    if not errorlevel 1 goto :eof
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; $u='https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe'; $o=Join-Path $env:TEMP 'python-setup.exe'; Invoke-WebRequest -Uri $u -OutFile $o; Start-Process -FilePath $o -ArgumentList '/quiet','InstallAllUsers=0','PrependPath=1','Include_launcher=1','Include_pip=1' -Wait; Remove-Item $o"
goto :eof

:refresh_path
for /f "tokens=2,*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYSPATH=%%b"
for /f "tokens=2,*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USERPATH=%%b"
if defined SYSPATH set "PATH=!SYSPATH!"
if defined USERPATH set "PATH=!PATH!;!USERPATH!"
goto :eof
