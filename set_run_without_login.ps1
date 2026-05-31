# ============================================================================
# Make the Stock Report tasks run WITHOUT you being logged in.
# Run this ONCE as Administrator:
#   - Right-click this file -> "Run with PowerShell"  (accept the admin prompt), OR
#   - Open "Windows Terminal (Admin)" / "PowerShell (Admin)" and run:
#       & "C:\Users\aryan\OneDrive\Desktop\Personal projects\stock_report\set_run_without_login.ps1"
#
# It switches both tasks to S4U logon (runs whether you're logged on or not,
# NO Windows password stored). Outbound internet + Gmail SMTP work under S4U.
# ============================================================================

# Self-elevate if not already running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Re-launching as Administrator..."
    Start-Process powershell -Verb RunAs -ArgumentList `
        "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
    return
}

$me = whoami
$principal = New-ScheduledTaskPrincipal -UserId $me -LogonType S4U -RunLevel Limited

foreach ($t in "StockReport_Weekly", "StockReport_Once_TomorrowAM") {
    try {
        Set-ScheduledTask -TaskName $t -Principal $principal | Out-Null
        Write-Host "OK  $t -> runs whether logged on or not (no password)" -ForegroundColor Green
    } catch {
        Write-Host "ERR $t : $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nCurrent state:"
Get-ScheduledTask -TaskName "StockReport_*" | ForEach-Object {
    "{0,-30} LogonType={1}" -f $_.TaskName, $_.Principal.LogonType
}
Write-Host "`nDone. Keep the PC powered on (sleep is OK - it will wake) at the run times." -ForegroundColor Cyan
Read-Host "Press Enter to close"

# ----------------------------------------------------------------------------
# ALTERNATIVE (only if S4U ever fails to reach the internet when logged off):
# store your Windows password so the task logs in fully. Replace YOURPASSWORD:
#
#   schtasks /Change /TN StockReport_Weekly          /RU "$me" /RP "YOURPASSWORD"
#   schtasks /Change /TN StockReport_Once_TomorrowAM /RU "$me" /RP "YOURPASSWORD"
# ----------------------------------------------------------------------------
