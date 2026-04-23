[Setup]
AppName=Smart Attendance System
AppVersion=1.0
AppPublisher=Your College
DefaultDirName={autopf}\SmartAttendance
DefaultGroupName=SmartAttendance
OutputDir=D:\Smart_Attendance_System\installer_output
OutputBaseFilename=SmartAttendance_Setup
SetupIconFile=D:\Smart_Attendance_System\favicon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: checkedonce

[Files]
Source: "D:\Smart_Attendance_System\dist\SmartAttendance\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\students"
Name: "{app}\attendance_reports"

[Icons]
Name: "{userdesktop}\Smart Attendance System"; Filename: "{app}\SmartAttendance.exe"; IconFilename: "{app}\favicon.ico"; Tasks: desktopicon
Name: "{group}\Smart Attendance System"; Filename: "{app}\SmartAttendance.exe"

[Run]
Filename: "{app}\SmartAttendance.exe"; Description: "Launch app"; Flags: nowait postinstall skipifsilent
