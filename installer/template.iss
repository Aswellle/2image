[Setup]
AppName={APP_NAME}
AppVersion={APP_VERSION}
; %LOCALAPPDATA% — 无需 UAC 提权，适合单用户桌面工具
DefaultDirName={localappdata}\{APP_NAME}
DefaultGroupName={APP_NAME}
PrivilegesRequired=lowest
SetupIconFile={ICON_PATH}
OutputBaseFilename={OUTPUT_BASE}
Compression=lzma
SolidCompression=yes

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; 仅包含主程序可执行文件（禁止通配符递归打包，防止 dist/ 中泄露敏感数据）
Source: "{SRC_DIR}\{APP_EXE_NAME}.exe"; DestDir: "{app}"

; 将应用程序图标单独包含并安装到程序目录（以便快捷方式使用该图标）
Source: "{ICON_PATH}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{APP_NAME}"; Filename: "{app}\{APP_EXE_NAME}.exe"; IconFilename: "{app}\{ICON_BASENAME}"

[Run]
; 可选：安装后运行主程序，若没有主程序可移除下一行
Filename: "{app}\{APP_EXE_NAME}.exe"; Description: "Launch {APP_NAME}"; Flags: nowait postinstall skipifsilent
