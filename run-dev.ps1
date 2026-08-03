#!/usr/bin/env pwsh
# Runs Hatchabit locally against the DEV database (.env.dev).
$envFile = Join-Path $PSScriptRoot ".env.dev"
if (-not (Test-Path $envFile)) {
    Write-Error "Missing .env.dev - create it with DATABASE_URL + SECRET_KEY for your dev Supabase project."
    exit 1
}

Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=\s][^=]*)\s*=\s*(.*)\s*$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim().Trim('"').Trim("'")
        Set-Item -Path ("Env:{0}" -f $name) -Value $value
    }
}

Write-Host "-> Running against DEV database" -ForegroundColor Cyan
python run.py
