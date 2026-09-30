set "projectName=Subtitle Mask"
set "versionNumber=1.3.0"

pyinstaller --clean --noupx -w -D --name "%projectName%" main.py

set "sourceFolder=./dist/%projectName%"
set "zipFile=./dist/%projectName%-%versionNumber%.zip"
7z a -tzip "%zipFile%" "%sourceFolder%"
