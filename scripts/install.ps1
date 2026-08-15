# scripts/install.ps1
# Installs wcrond and registers auto-start with Windows

param(
    [ValidateSet("registry", "startup")]
    [string]$AutoStartMethod = "registry"
)

# 1. Install package
pip install -e .

# 2. Initialize config if needed
wcrond init

# 3. Register auto-start
wcrond install --method $AutoStartMethod

Write-Host ""
Write-Host "Installation completed."
Write-Host "  Config: $env:USERPROFILE\.wcrond\wcrond.toml"
Write-Host "  Jobs:   $env:USERPROFILE\.wcrond\wcrontab.toml"
Write-Host ""
Write-Host "Next: edit wcrontab.toml and run 'wcrond start'"
