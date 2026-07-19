[Setup]
; アプリケーションの基本情報
AppName=PhotoSDCopy
AppVersion=1.0.0
AppPublisher=tomok

; インストール先フォルダ（PrivilegesRequired=lowest の場合、通常は Local AppData 以下の Programs フォルダになります）
DefaultDirName={autopf}\PhotoSDCopy
DefaultGroupName=PhotoSDCopy

; 出力されるインストーラーのファイル名
OutputBaseFilename=PhotoSDCopy_Installer
Compression=lzma2
SolidCompression=yes

; 64ビット版としてインストール
ArchitecturesInstallIn64BitMode=x64

; 管理者権限を不要にする（現在のユーザーのみにインストール）
PrivilegesRequired=lowest

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; パブリッシュされたすべてのファイルを含める（単一ファイルの場合でもexeを指定）
Source: "bin\Release\net10.0-windows\win-x64\publish\PhotoSDCopy.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; スタートメニューとデスクトップのショートカット
Name: "{group}\PhotoSDCopy"; Filename: "{app}\PhotoSDCopy.exe"
Name: "{autodesktop}\PhotoSDCopy"; Filename: "{app}\PhotoSDCopy.exe"; Tasks: desktopicon
