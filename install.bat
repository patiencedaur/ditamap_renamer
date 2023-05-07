@echo OFF

(python --version 2>NUL) && (echo Found Python, checking pip installation...) || (.\python-3.11.1-amd64.exe)

(python --version 2>NUL 1>NUL) && (python -m ensurepip --upgrade)

echo Installing MaryTreat requirements...

set thisdir=%~dp0

@REM Make sure that the path to install.bat has no spaces in it. Otherwise an error will occur.

pip install -r %thisdir%\requirements.txt

echo Creating launcher...
echo ^@echo off > marytreat.bat
echo cd %thisdir% >> marytreat.bat
echo python -m marytreat >> marytreat.bat

echo Creating desktop shortcut...

echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%OneDrive%\Desktop\MaryTreat.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%thisdir%\marytreat.bat" >> CreateShortcut.vbs
echo oLink.IconLocation = "%SystemRoot%\SystemResources\shell32.dll.mun, 91"
echo oLink.Save >> CreateShortcut.vbs
cscript CreateShortcut.vbs
del CreateShortcut.vbs

pause
