' Review Room launcher: starts the local server (hidden) if it is not running, then opens the app window.
' Everything is relative to this folder, so the whole ReviewRoom folder can be copied to any PC.
Option Explicit
Dim sh, fso, here, py, url, port, chrome, edge, http, running, i, settings, re, m, profileDir
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)

' port from settings.json (default 8770)
port = "8770"
If fso.FileExists(here & "\settings.json") Then
  settings = fso.OpenTextFile(here & "\settings.json", 1).ReadAll
  Set re = New RegExp
  re.Pattern = """port""\s*:\s*(\d+)"
  Set m = re.Execute(settings)
  If m.Count > 0 Then port = m(0).SubMatches(0)
End If
url = "http://127.0.0.1:" & port & "/"

Function Up()
  Up = False
  On Error Resume Next
  Set http = CreateObject("MSXML2.XMLHTTP")
  http.Open "GET", url & "api/videos", False
  http.Send
  If Err.Number = 0 Then If http.Status = 200 Then Up = True
  Err.Clear
  On Error GoTo 0
End Function

If Not Up() Then
  ' the portable Python shipped in app\python; else one installed on the PC
  py = here & "\app\python\pythonw.exe"
  If Not fso.FileExists(py) Then py = "pythonw.exe"
  sh.CurrentDirectory = here & "\app"
  sh.Run """" & py & """ """ & here & "\app\server.py""", 0, False
  For i = 1 To 60                ' wait up to ~15 s for it to answer
    WScript.Sleep 250
    If Up() Then Exit For
  Next
End If

' open as an app window (no tabs / address bar): Chrome, then Edge, then the default browser
chrome = sh.ExpandEnvironmentStrings("%ProgramFiles%") & "\Google\Chrome\Application\chrome.exe"
If Not fso.FileExists(chrome) Then chrome = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Google\Chrome\Application\chrome.exe"
edge = sh.ExpandEnvironmentStrings("%ProgramFiles(x86)%") & "\Microsoft\Edge\Application\msedge.exe"
If Not fso.FileExists(edge) Then edge = sh.ExpandEnvironmentStrings("%ProgramFiles%") & "\Microsoft\Edge\Application\msedge.exe"
profileDir = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\ReviewRoomApp\window-profile"
If fso.FileExists(chrome) Then
  sh.Run """" & chrome & """ --app=" & url & " --user-data-dir=""" & profileDir & """ --window-size=1680,1000 --autoplay-policy=no-user-gesture-required", 1, False
ElseIf fso.FileExists(edge) Then
  sh.Run """" & edge & """ --app=" & url & " --user-data-dir=""" & profileDir & """ --window-size=1680,1000 --autoplay-policy=no-user-gesture-required", 1, False
Else
  sh.Run url, 1, False
End If
