# ============================================================================
# Repoint the one-time "test run" task to TOMORROW 8:00 AM (local/ET).
# Run ONCE as Administrator: right-click -> "Run with PowerShell" (accept UAC),
# or from an elevated terminal:
#   & "C:\Users\aryan\OneDrive\Desktop\Personal projects\stock_report\set_tomorrow_testrun.ps1"
# The recurring Wed 8PM / Sat 8AM job (StockReport_Weekly) is left untouched.
# ============================================================================
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Re-launching as Administrator..."
    Start-Process powershell -Verb RunAs -ArgumentList `
        "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
    return
}

$tomorrow8 = (Get-Date).Date.AddDays(1).AddHours(8)
$trig = New-ScheduledTaskTrigger -Once -At $tomorrow8
try {
    Set-ScheduledTask -TaskName "StockReport_Once_TomorrowAM" -Trigger $trig | Out-Null
    $i = Get-ScheduledTask -TaskName "StockReport_Once_TomorrowAM" | Get-ScheduledTaskInfo
    Write-Host ("OK  Test run set for: {0}" -f $i.NextRunTime) -ForegroundColor Green
} catch {
    Write-Host "ERR $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nAll StockReport tasks:"
Get-ScheduledTask -TaskName "StockReport_*" | ForEach-Object {
    $info = $_ | Get-ScheduledTaskInfo
    "{0,-30} Next: {1}" -f $_.TaskName, $info.NextRunTime
}
Read-Host "Press Enter to close"
