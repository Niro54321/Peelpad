; Peelpad installer for Inno Setup 6, built by packaging/build.py.
; Installs for the current user only (no admin prompt), into
; %LOCALAPPDATA%\Programs\Peelpad.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{338ED385-CE42-4DD7-93BE-60A5EC501A50}
AppName=Peelpad
AppVersion={#AppVersion}
AppVerName=Peelpad {#AppVersion}
AppPublisher=Niro54321
VersionInfoProductName=Peelpad
VersionInfoProductVersion={#AppVersion}
VersionInfoVersion={#AppVersion}
VersionInfoCompany=Niro54321
VersionInfoDescription=Peelpad Setup
AppPublisherURL=https://github.com/Niro54321/Peelpad
AppSupportURL=https://github.com/Niro54321/Peelpad/issues
AppUpdatesURL=https://github.com/Niro54321/Peelpad/releases
DefaultDirName={autopf}\Peelpad
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=Peelpad-Setup-{#AppVersion}
SetupIconFile=..\build\peelpad.ico
UninstallDisplayIcon={app}\Peelpad.exe
UninstallDisplayName=Peelpad
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"

[Files]
Source: "..\dist\Peelpad\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Peelpad"; Filename: "{app}\Peelpad.exe"; AppUserModelID: "Niro54321.Peelpad"
Name: "{autodesktop}\Peelpad"; Filename: "{app}\Peelpad.exe"; Tasks: desktopicon; AppUserModelID: "Niro54321.Peelpad"

[Run]
Filename: "{app}\Peelpad.exe"; Description: "Start Peelpad now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/IM Peelpad.exe /F"; Flags: runhidden; RunOnceId: "StopPeelpad"

[Registry]
; the "Start with Windows" switch in Settings writes this; remove it on uninstall
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Peelpad"; Flags: uninsdeletevalue dontcreatekey

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
begin
  { An older Peelpad may be open; close it so its files can be replaced. }
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM Peelpad.exe /F', '', SW_HIDE, ewWaitUntilTerminated, Code);
  Result := '';
end;
