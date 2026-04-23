@echo off
cd /d D:\Smart_Attendance_System

echo Cleaning junk files...

REM Delete duplicate/wrong files
del "cleanup.bat.bat" 2>nul
del "run.bat.bat" 2>nul
del "requirements.txt.txt" 2>nul
del "registration.py" 2>nul
del "settings.json" 2>nul
del "database.db" 2>nul
del "Smart_Attendance_System.spec" 2>nul
del "Smart_Attendance_System_v1.spec" 2>nul
del "Project structure · MD" 2>nul

REM Delete old installer output and rebuild folders
rmdir /s /q installer_output 2>nul

echo Done cleaning!
echo.
echo Remaining files:
dir /b
pause