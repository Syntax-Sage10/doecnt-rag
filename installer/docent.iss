; Inno Setup script. Build:  ISCC /DAppVersion=1.0.0 installer\docent.iss
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppName=Docent
AppVersion={#AppVersion}
DefaultDirName={autopf}\Docent
DefaultGroupName=Docent
OutputDir=..\release
OutputBaseFilename=Docent-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\Docent.exe

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"

[Files]
Source: "..\dist\Docent\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Docent"; Filename: "{app}\Docent.exe"
Name: "{autodesktop}\Docent"; Filename: "{app}\Docent.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Docent.exe"; Description: "Launch Docent"; Flags: nowait postinstall skipifsilent
