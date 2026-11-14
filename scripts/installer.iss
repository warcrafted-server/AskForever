; AskForever - instalador de Windows (Inno Setup 6)

#ifndef AppVersion
#define AppVersion "0.0.0"
#endif

#ifndef SourceDir
#define SourceDir "..\dist\AskForever"
#endif

[Setup]
AppId={{022D4D05-1DB9-464D-A4BF-747473B1FC4C}
AppName=AskForever
AppVersion={#AppVersion}
AppPublisher=WarCrafted
AppPublisherURL=https://github.com/warcrafted-server/AskForever
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\AskForever
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=AskForever-Setup-{#AppVersion}
LicenseFile=..\LICENSE
SetupIconFile=..\companion\packaging\askforever.ico
UninstallDisplayIcon={app}\AskForever.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AskForever"; Filename: "{app}\AskForever.exe"
Name: "{autodesktop}\AskForever"; Filename: "{app}\AskForever.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AskForever.exe"; Description: "{cm:LaunchProgram,AskForever}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\AskForever.exe"; Parameters: "uninstall --yes"; RunOnceId: "AskForeverUninstall"; Flags: runhidden waituntilterminated
