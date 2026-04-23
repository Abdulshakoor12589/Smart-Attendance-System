; Smart Attendance System - NSIS Installer Script

;--------------------------------
; General Settings
!define APP_NAME "Smart Attendance System"
!define APP_VERSION "1.0"
!define APP_EXE "SmartAttendance.exe"
!define INSTALL_DIR "$PROGRAMFILES64\SmartAttendanceSystem"
!define PUBLISHER "Smart Attendance"

Name "${APP_NAME}"
OutFile "SmartAttendance_Setup.exe"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "InstallDir"
RequestExecutionLevel admin
SetCompressor lzma

;--------------------------------
; Modern UI
!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "favicon.ico"
!define MUI_UNICON "favicon.ico"

; Welcome page
!define MUI_WELCOMEPAGE_TITLE "Welcome to Smart Attendance System Setup"
!define MUI_WELCOMEPAGE_TEXT "This will install Smart Attendance System v1.0 on your computer.$\n$\nClick Next to continue."
!insertmacro MUI_PAGE_WELCOME

; Directory page
!insertmacro MUI_PAGE_DIRECTORY

; Install files page
!insertmacro MUI_PAGE_INSTFILES

; Finish page
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Smart Attendance System"
!define MUI_FINISHPAGE_TITLE "Installation Complete!"
!define MUI_FINISHPAGE_TEXT "Smart Attendance System has been installed successfully.$\n$\nClick Finish to exit Setup."
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; Installer Section
Section "Install" SecInstall

  SetOutPath "$INSTDIR"

  ; Copy all files from dist\SmartAttendance folder
  File /r "dist\SmartAttendance\*.*"

  ; Create students and attendance_reports folders
  CreateDirectory "$INSTDIR\students"
  CreateDirectory "$INSTDIR\attendance_reports"

  ; Write install path to registry
  WriteRegStr HKLM "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "Software\${APP_NAME}" "Version" "${APP_VERSION}"

  ; Write uninstaller info to registry (for Control Panel)
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
    "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
    "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
    "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
    "Publisher" "${PUBLISHER}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
    "DisplayVersion" "${APP_VERSION}"

  ; Create Desktop shortcut
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" \
    "$INSTDIR\${APP_EXE}" "" \
    "$INSTDIR\${APP_EXE}" 0

  ; Create Start Menu shortcut
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
    "$INSTDIR\${APP_EXE}" "" \
    "$INSTDIR\${APP_EXE}" 0
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" \
    "$INSTDIR\Uninstall.exe"

  ; Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

SectionEnd

;--------------------------------
; Uninstaller Section
Section "Uninstall"

  ; Remove all installed files
  RMDir /r "$INSTDIR\_internal"
  Delete "$INSTDIR\${APP_EXE}"
  Delete "$INSTDIR\Uninstall.exe"

  ; Remove shortcuts
  Delete "$DESKTOP\${APP_NAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APP_NAME}"

  ; Remove registry entries
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
  DeleteRegKey HKLM "Software\${APP_NAME}"

  ; Remove install directory
  RMDir "$INSTDIR"

  MessageBox MB_OK "Smart Attendance System has been uninstalled.$\nYour student data has been kept safe."

SectionEnd
