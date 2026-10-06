[Setup]
; Fixed install identity.  All shipped releases (v<=2.6.x) derived their
; AppId from the old AppName "text2image_pro"; the product now renames
; to "2image", so the AppId is pinned to that legacy value to keep every
; past and future installer treating this as ONE application — a new
; version upgrades the existing install in place (same directory, same
; uninstaller) instead of creating a parallel instance.
; NEVER change this value and NEVER embed the version number in it.
AppId=text2image_pro
AppName={APP_NAME}
AppVersion={APP_VERSION}
AppVerName={APP_NAME} v{APP_VERSION}
DefaultDirName={localappdata}\{APP_NAME}
DefaultGroupName={APP_NAME}
PrivilegesRequired=lowest
SetupIconFile={ICON_PATH}
UninstallDisplayIcon={app}\{APP_EXE_NAME}.exe
OutputDir="{OUTPUT_DIR}"
OutputBaseFilename={OUTPUT_BASE}
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{SRC_DIR}\{APP_EXE_NAME}.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{SRC_DIR}\2image_updater.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{ICON_PATH}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{APP_NAME}"; Filename: "{app}\{APP_EXE_NAME}.exe"; IconFilename: "{app}\{ICON_BASENAME}"
Name: "{userdesktop}\{APP_NAME}"; Filename: "{app}\{APP_EXE_NAME}.exe"; IconFilename: "{app}\{ICON_BASENAME}"; Tasks: desktopicon

[Run]
Filename: "{app}\{APP_EXE_NAME}.exe"; Description: "Launch {APP_NAME}"; Flags: nowait postinstall skipifsilent
