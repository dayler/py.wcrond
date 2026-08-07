$ErrorActionPreference = "Stop"

# 1. Install
pip install -e . | Out-Null

# 2. Init
wcrond init

# 3. Start daemon in background
$daemon = Start-Process wcrond -ArgumentList "start","--foreground" -PassThru -NoNewWindow
Start-Sleep 3

# 4. Test CLI commands
wcrond-ctl status
wcrond-ctl list
wcrond-ctl validate

# 5. Create a test job for run test
Add-Content -Path "$HOME\.wcrond\jobs.d\smoke.toml" -Value @"
[jobs.smoke_test]
command = `"echo smoke`"
schedule = `"* * * * *`"
"@
wcrond-ctl reload
Start-Sleep 1

# 5. Force run a test job
wcrond-ctl run smoke_test
Start-Sleep 5
wcrond-ctl history --last 1

# 6. Stop daemon
wcrond-ctl stop
Start-Sleep 2

# Verify daemon stopped
if (-not $daemon.HasExited) {
    $daemon.Kill()
    throw "Daemon did not exit cleanly"
}

Write-Host "[SMOKE TEST PASSED]" -ForegroundColor Green
