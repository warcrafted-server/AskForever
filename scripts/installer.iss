; AskForever - instalador de Windows (Inno Setup 6)

#ifndef AppVersion
#define AppVersion "0.0.0"
#endif

#ifndef SourceDir
#define SourceDir "..\dist\AskForever"
#endif

[Setup]
AppId={{022D4D05-1DB9-464D-A4BF-747473B1FC4C}
AppName=AskForever App
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
UninstallDisplayIcon={app}\AskForeverApp.exe
CloseApplications=force
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
Type: files; Name: "{app}\AskForever.exe"
Type: files; Name: "{autoprograms}\AskForever.lnk"
Type: files; Name: "{autodesktop}\AskForever.lnk"

[Icons]
Name: "{autoprograms}\AskForever App"; Filename: "{app}\AskForeverApp.exe"
Name: "{autodesktop}\AskForever App"; Filename: "{app}\AskForeverApp.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AskForeverApp.exe"; Description: "{cm:LaunchProgram,AskForever App}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\AskForeverApp.exe"; Check: IsRelaunch; Flags: nowait

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /T /IM AskForever.exe"; RunOnceId: "AskForeverStopOld"; Flags: runhidden waituntilterminated
Filename: "{sys}\taskkill.exe"; Parameters: "/F /T /IM AskForeverApp.exe"; RunOnceId: "AskForeverStop"; Flags: runhidden waituntilterminated
Filename: "{app}\AskForeverApp.exe"; Parameters: "uninstall --yes"; RunOnceId: "AskForeverUninstall"; Flags: runhidden waituntilterminated

[Code]
function IsRelaunch: Boolean;
begin
  Result := Pos('/RELAUNCH', UpperCase(GetCmdTail)) > 0;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM AskForever.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  // The updater may still be a child process of AskForeverApp.exe.
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM AskForeverApp.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;

[UninstallDelete]
; Refuerzo por si algo quedó (archivos creados después de instalar o que no se pudieron borrar).
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{localappdata}\AskForever"
