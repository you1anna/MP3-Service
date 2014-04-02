@ECHO OFF

if not exist "C:\Program Files\MP3Service" mkdir "C:\Program Files\MP3Service"

copy "%~dp0*.*" "C:\Program Files\MP3Service"

REM The following directory is for .NET 4.0
set DOTNETFX2=%SystemRoot%\Microsoft.NET\Framework\v4.0.30319
set PATH=%PATH%;%DOTNETFX2%

C:\Windows\Microsoft.NET\Framework\v4.0.30319\installutil.exe "C:\Program Files\MP3Service\mp3Service.exe"

echo Done

net start Service1

pause