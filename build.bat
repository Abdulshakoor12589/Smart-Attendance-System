@echo off
cd /d D:\Smart_Attendance_System
call .venv\Scripts\activate

echo Step 1: Creating favicon.ico...
python -c "from PIL import Image; Image.open('favicon.png').save('favicon.ico')"
echo Done.

echo.
echo Step 2: Building exe with PyInstaller...
echo This will take 5-15 minutes. Please wait...
echo.

pyinstaller --onedir --windowed --name="SmartAttendance" --icon="favicon.ico" --add-data "favicon.png;." --add-data "14722.jpg;." --add-data "tb.jpg;." --add-data "app_settings.json;." --hidden-import=face_recognition --hidden-import=dlib --hidden-import=cv2 --hidden-import=PIL --hidden-import=werkzeug --hidden-import=openpyxl --hidden-import=tkinter main.py

echo.
if exist "dist\SmartAttendance\SmartAttendance.exe" (
    echo SUCCESS! File created at:
    echo D:\Smart_Attendance_System\dist\SmartAttendance\SmartAttendance.exe
    echo.
    echo Testing the exe now...
    start dist\SmartAttendance\SmartAttendance.exe
) else (
    echo FAILED - exe not created. Check errors above.
)

pause