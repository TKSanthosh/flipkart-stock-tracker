$workDir = "C:\Users\u1224576\.gemini\antigravity\scratch\flipkart-stock-tracker"
Set-Location $workDir
& "C:\Program Files\Python312\python.exe" "$workDir\main.py" | Out-File -FilePath "$workDir\tracker_run.log" -Append -Encoding utf8
