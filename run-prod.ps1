#!/usr/bin/env pwsh
# Runs Hatchabit locally against the PROD database (.env). Be careful - this
# is the real Supabase data behind the live deployment.
$envFile = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Error "Missing .env - create it with the prod DATABASE_URL + SECRET_KEY."
    exit 1
}

Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=\s][^=]*)\s*=\s*(.*)\s*$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim().Trim('"').Trim("'")
        Set-Item -Path ("Env:{0}" -f $name) -Value $value
    }
}

Write-Host "-> Running against PROD database - changes are LIVE" -ForegroundColor Red
python run.py
