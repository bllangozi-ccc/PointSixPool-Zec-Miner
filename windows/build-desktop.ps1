$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$source = Join-Path $PSScriptRoot 'desktop'
$payload = Join-Path $PSScriptRoot 'desktop-payload'
$backend = Join-Path $payload 'backend'
New-Item -ItemType Directory -Force $backend | Out-Null
& dotnet publish (Join-Path $root 'source/Point6Miner.Cli/Point6Miner.Cli.csproj') -c Release -r win-x64 --self-contained true -p:UseAppHost=true -p:IncludeSourceRevisionInInformationalVersion=false -p:DebugType=None -p:ContinuousIntegrationBuild=true -o $backend
if ($LASTEXITCODE -ne 0) { throw 'Bundled miner runtime build failed' }
Copy-Item (Join-Path $PSScriptRoot 'package/point6miner-equihash.exe') $payload
Copy-Item (Join-Path $PSScriptRoot 'windows_resources.py') $source
$pins = [ordered]@{}
Get-ChildItem $payload -Recurse -File | Sort-Object FullName | ForEach-Object {
 $relative = [System.IO.Path]::GetRelativePath($payload, $_.FullName).Replace('\','/')
 $pins[$relative] = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
}
$pins | ConvertTo-Json | Set-Content -Encoding utf8NoBOM (Join-Path $payload 'WINDOWS-PINS.json')
& python -m pip install --disable-pip-version-check pyinstaller==6.22.3
if ($LASTEXITCODE -ne 0) { throw 'Desktop packager installation failed' }
& python -m PyInstaller --noconfirm --clean --onefile --windowed --noupx --name 'PointSixPool Miner' --icon (Join-Path $root 'assets/pointsixpool.ico') --add-data ((Join-Path $root 'assets') + ':assets') --distpath (Join-Path $PSScriptRoot 'desktop-dist') --workpath (Join-Path $PSScriptRoot 'desktop-work') --specpath (Join-Path $PSScriptRoot 'desktop-work') --paths $source --add-data ($payload + ':miner') (Join-Path $source 'native_desktop.py')
if ($LASTEXITCODE -ne 0) { throw 'Desktop executable build failed' }
$exe = Join-Path $PSScriptRoot 'desktop-dist/PointSixPool Miner.exe'
$env:POINTSIX_SMOKE_RESULT = Join-Path $PSScriptRoot 'DESKTOP-SMOKE.PUBLIC.json'
$setupPath = Join-Path (Split-Path -Parent $exe) 'point6miner-settings.json'
@{schema=1;coin='ZEC';mode='MICRO';kind='wallet';identity='t1VL5XNfTPehmSxrszsSJC1hJUrYGUHbAFg';worker='Desktop-CI';region='ASIA'} | ConvertTo-Json | Set-Content -Encoding utf8NoBOM $setupPath
$env:POINTSIX_SMOKE_EXPECT_SETUP = '1'
$process = Start-Process -FilePath $exe -ArgumentList '--smoke-test' -PassThru
if (-not $process.WaitForExit(30000)) { Stop-Process -Id $process.Id -Force; throw 'Desktop non-mining GUI smoke test timed out' }
if ($process.ExitCode -ne 0 -or -not (Test-Path $env:POINTSIX_SMOKE_RESULT)) { throw 'Desktop GUI smoke test failed' }
$result = Get-Content $env:POINTSIX_SMOKE_RESULT -Raw | ConvertFrom-Json
if (-not $result.passed -or $result.mining_started -or -not $result.bundled_executable) { throw 'Desktop smoke evidence invalid' }
(Get-FileHash $exe -Algorithm SHA256).Hash.ToLowerInvariant() | Set-Content (Join-Path $PSScriptRoot 'DESKTOP-SHA256.txt')

Remove-Item $setupPath
Remove-Item Env:POINTSIX_SMOKE_EXPECT_SETUP
