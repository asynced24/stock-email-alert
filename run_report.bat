@echo off
REM Wrapper invoked by Windows Task Scheduler to build + email the stock report.
REM Logs each run (stdout+stderr) to run_log.txt in the project folder.
cd /d "C:\Users\aryan\OneDrive\Desktop\Personal projects\stock_report"
echo ===== Run started %DATE% %TIME% ===== >> run_log.txt
"C:\Python313\python.exe" main.py >> run_log.txt 2>&1
echo ===== Run finished %DATE% %TIME% (exit %ERRORLEVEL%) ===== >> run_log.txt
