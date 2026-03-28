#define AppName "CogStash"
#define AppPublisher "CogStash"
#define AppURL "https://github.com/abdul219428/CogStash"
#define AppExeName "CogStash.exe"

#ifndef AppVersion
  #error "AppVersion define is required."
#endif

#ifndef SourceDir
  #error "SourceDir define is required."
#endif

#ifndef VersionInfoVersion
  #define VersionInfoVersion AppVersion
#endif

#ifndef OutputDir
  #define OutputDir SourceDir
#endif

[Setup]
AppId={{A8B61FA0-C1C4-4C8A-8A2E-B9972DB78547}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
VersionInfoVersion={#VersionInfoVersion}
DefaultDirName={localappdata}\Programs\CogStash
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#OutputDir}
OutputBaseFilename=CogStash-v{#AppVersion}-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}
ChangesEnvironment=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startup"; Description: "Launch CogStash when I sign in"; GroupDescription: "Additional tasks:"
Name: "addtopath"; Description: "Add CogStash to PATH (new shells may be required)"; GroupDescription: "Additional tasks:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CogStash"; Filename: "{app}\CogStash.exe"
Name: "{autodesktop}\CogStash"; Filename: "{app}\CogStash.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CogStash.exe"; Description: "Launch CogStash"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{userstartup}\CogStash.bat"

[Code]
const
  UserEnvironmentSubkey = 'Environment';
  UserPathValueName = 'Path';
  PathOwnershipKey = 'AddToPathOwned';
  PathTaskName = 'addtopath';

var
  PathEntryOwned: Boolean;

function StartupBatchContents(): String;
begin
  Result := '@echo off' + #13#10 + 'start "" "' + ExpandConstant('{app}\CogStash.exe') + '"' + #13#10;
end;

function NormalizePathEntry(Value: String): String;
begin
  Result := Trim(Value);
  Result := StringChangeEx(Result, '/', '\', True);
  Result := LowerCase(Result);
  Result := StringChangeEx(Result, '%localappdata%', LowerCase(GetEnv('LOCALAPPDATA')), True);
  Result := StringChangeEx(Result, '%userprofile%', LowerCase(GetEnv('USERPROFILE')), True);
  while (Length(Result) > 0) and (Result[Length(Result)] = '\') do
  begin
    Delete(Result, Length(Result), 1);
  end;
end;

function PathEntriesMatch(Left, Right: String): Boolean;
begin
  Result := NormalizePathEntry(Left) = NormalizePathEntry(Right);
end;

function PathContainsEntry(PathValue, Entry: String): Boolean;
var
  Item: String;
  Remaining: String;
  SeparatorPos: Integer;
begin
  Result := False;
  Remaining := PathValue;

  while Remaining <> '' do
  begin
    SeparatorPos := Pos(';', Remaining);
    if SeparatorPos = 0 then
    begin
      Item := Remaining;
      Remaining := '';
    end
    else
    begin
      Item := Copy(Remaining, 1, SeparatorPos - 1);
      Delete(Remaining, 1, SeparatorPos);
    end;

    if PathEntriesMatch(Item, Entry) then
    begin
      Result := True;
      Exit;
    end;
  end;
end;

function AddPathEntry(PathValue, Entry: String): String;
begin
  if (PathValue = '') or (Trim(PathValue) = '') then
  begin
    Result := Entry;
  end
  else if PathContainsEntry(PathValue, Entry) then
  begin
    Result := PathValue;
  end
  else
  begin
    Result := PathValue + ';' + Entry;
  end;
end;

function RemovePathEntry(PathValue, Entry: String): String;
var
  Item: String;
  Remaining: String;
  ResultValue: String;
  SeparatorPos: Integer;
begin
  Remaining := PathValue;
  ResultValue := '';

  while Remaining <> '' do
  begin
    SeparatorPos := Pos(';', Remaining);
    if SeparatorPos = 0 then
    begin
      Item := Remaining;
      Remaining := '';
    end
    else
    begin
      Item := Copy(Remaining, 1, SeparatorPos - 1);
      Delete(Remaining, 1, SeparatorPos);
    end;

    if (Trim(Item) <> '') and (not PathEntriesMatch(Item, Entry)) then
    begin
      if ResultValue <> '' then
      begin
        ResultValue := ResultValue + ';';
      end;
      ResultValue := ResultValue + Item;
    end;
  end;

  Result := ResultValue;
end;

function EnvAddPath(Entry: String): Boolean;
var
  CurrentPath: String;
  NewPath: String;
  PreviouslyOwned: Boolean;
begin
  PreviouslyOwned := GetPreviousData(PathOwnershipKey, '0') = '1';

  if not RegQueryStringValue(HKEY_CURRENT_USER, UserEnvironmentSubkey, UserPathValueName, CurrentPath) then
  begin
    CurrentPath := '';
  end;

  if PathContainsEntry(CurrentPath, Entry) then
  begin
    Result := PreviouslyOwned;
    Exit;
  end;

  NewPath := AddPathEntry(CurrentPath, Entry);
  if not RegWriteExpandStringValue(HKEY_CURRENT_USER, UserEnvironmentSubkey, UserPathValueName, NewPath) then
  begin
    RaiseException('Could not update the user PATH environment variable.');
  end;

  Result := True;
end;

procedure EnvRemovePath(Entry: String);
var
  CurrentPath: String;
  NewPath: String;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, UserEnvironmentSubkey, UserPathValueName, CurrentPath) then
  begin
    Exit;
  end;

  NewPath := RemovePathEntry(CurrentPath, Entry);
  if NewPath = CurrentPath then
  begin
    Exit;
  end;

  if NewPath = '' then
  begin
    if not RegDeleteValue(HKEY_CURRENT_USER, UserEnvironmentSubkey, UserPathValueName) then
    begin
      Log('Could not remove the installer-managed PATH entry.');
    end;
  end
  else if not RegWriteExpandStringValue(HKEY_CURRENT_USER, UserEnvironmentSubkey, UserPathValueName, NewPath) then
  begin
    Log('Could not remove the installer-managed PATH entry.');
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  AppPath: String;
begin
  if CurStep = ssPostInstall then
  begin
    AppPath := ExpandConstant('{app}');

    if WizardIsTaskSelected('startup') then
    begin
      SaveStringToFile(ExpandConstant('{userstartup}\CogStash.bat'), StartupBatchContents(), False);
    end;

    if WizardIsTaskSelected(PathTaskName) then
    begin
      PathEntryOwned := EnvAddPath(AppPath);
    end
    else
    begin
      PathEntryOwned := GetPreviousData(PathOwnershipKey, '0') = '1';
    end;
  end;
end;

procedure RegisterPreviousData(PreviousDataKey: Integer);
begin
  if PathEntryOwned then
  begin
    SetPreviousData(PreviousDataKey, PathOwnershipKey, '1');
  end
  else
  begin
    SetPreviousData(PreviousDataKey, PathOwnershipKey, '0');
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usUninstall) and (GetPreviousData(PathOwnershipKey, '0') = '1') then
  begin
    EnvRemovePath(ExpandConstant('{app}'));
  end;
end;
