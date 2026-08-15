# scripts/uninstall.ps1
# Stops daemon, removes auto-start, uninstalls package

# 1. Stop daemon if running
try { wcrond stop } catch {}

# 2. Remove auto-start (both methods)
try { wcrond uninstall } catch {}

# 3. Uninstall package
pip uninstall -y wcrond

Write-Host "[OK] wcrond uninstalled."
Write-Host "Data in ~/.wcrond/ was NOT deleted."
Write-Host "To remove: Remove-Item -Recurse ~\.wcrond"
