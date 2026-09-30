@echo off
setlocal
pushd "%~dp0" || exit /b 1

set "projectName=Subtitle Mask"
set "versionNumber=1.3.0"
set "pythonExe=.venv\Scripts\python.exe"
set "builtExe=build\release\%projectName%.exe"
set "releaseExe=dist\%projectName%-%versionNumber%.exe"

if not exist "%pythonExe%" (
    echo ERROR: Project Python environment is missing.
    echo Run: python -m venv .venv
    echo Then: .venv\Scripts\python.exe -m pip install -r requirements-build.txt
    goto failed
)

"%pythonExe%" -c "import PyInstaller, tkinter, win32gui; from BlurWindow.blurWindow import GlobalBlur"
if errorlevel 1 (
    echo ERROR: Build dependencies are missing or cannot be imported.
    echo Run: .venv\Scripts\python.exe -m pip install -r requirements-build.txt
    goto failed
)

echo Building %projectName% %versionNumber%...
"%pythonExe%" -m PyInstaller --noconfirm --clean --noupx -w --onefile --distpath "build\release" --name "%projectName%" main.py
if errorlevel 1 goto failed

if not exist "%builtExe%" (
    echo ERROR: PyInstaller did not produce the expected executable.
    goto failed
)

echo Publishing standalone executable...
rem Replace the previous release only after the new executable builds successfully.
"%pythonExe%" -c "import os, sys; os.makedirs('dist', exist_ok=True); os.replace(sys.argv[1], sys.argv[2])" "%builtExe%" "%releaseExe%"
if errorlevel 1 goto failed

echo SUCCESS: "%CD%\%releaseExe%"
popd
exit /b 0

:failed
echo ERROR: Packaging failed. No new release EXE was published.
popd
exit /b 1
