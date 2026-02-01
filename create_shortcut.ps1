$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$Desktop\ReadIn AI.lnk")
$Shortcut.TargetPath = "pythonw.exe"
$Shortcut.Arguments = "`"C:\Users\Derick Joseph\OneDrive\Brider LLC\Projects\readin-ai\main.py`""
$Shortcut.WorkingDirectory = "C:\Users\Derick Joseph\OneDrive\Brider LLC\Projects\readin-ai"
$Shortcut.Description = "ReadIn AI Meeting Assistant"
$Shortcut.Save()
Write-Host "Desktop shortcut created: ReadIn AI.lnk"
