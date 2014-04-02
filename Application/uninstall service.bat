@ECHO OFF

net stop MP3 Service

REM The following directory is for .NET 4.0
set DOTNETFX2=%SystemRoot%\Microsoft.NET\Framework\v4.0.30319
set PATH=%PATH%;%DOTNETFX2%

C:\Windows\Microsoft.NET\Framework\v4.0.30319\installutil.exe /u "c:\Program Files\mp3Service\mp3Service.exe"


echo Done
