@echo OFF

(python --version 2>NUL) && (echo Found Python, checking pip installation...) || (.\python-3.11.1-amd64.exe)

(python --version 2>NUL 1>NUL) && (python -m ensurepip --upgrade)

echo Installing MaryTreat requirements...

set thisdir=%~dp0

@REM Make sure that the path to install.bat has no spaces in it. Otherwise an error will occur.

pip install -r %cd%\requirements.txt

echo Creating launcher...
echo ^@echo off > marytreat.bat
echo cd %thisdir% >> marytreat.bat
echo python -m marytreat >> marytreat.bat

echo Creating desktop shortcut...

powershell "$pathToTarget=(Join-Path $pwd 'marytreat.bat');$pathToDesktop=[Environment]::GetFolderPath('Desktop');$pathToShortcut=(Join-Path $pathToDesktop 'MaryTreat-Indigo.lnk');$pathToIcon=(Join-Path $pwd 'marytreat.ico');$s=(New-Object -COM WScript.Shell).CreateShortcut($pathToShortcut);$s.TargetPath=$pathToTarget;$s.IconLocation=$pathToIcon;$s.Save()"

pause
