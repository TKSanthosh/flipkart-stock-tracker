$workDir = $PSScriptRoot
Set-Location $workDir
python "$workDir\main.py" | Out-File -FilePath "$workDir\tracker_run.log" -Append -Encoding utf8
