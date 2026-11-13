$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$package = Join-Path $PSScriptRoot 'package'
New-Item -ItemType Directory -Force $package | Out-Null
& dotnet publish (Join-Path $root 'source/Point6Miner.Cli/Point6Miner.Cli.csproj') -c Release -r win-x64 --self-contained false -p:UseAppHost=false -p:DebugType=None -p:ContinuousIntegrationBuild=true -o $package
if ($LASTEXITCODE -ne 0) { throw 'Windows managed client build failed' }
Copy-Item (Join-Path $PSScriptRoot 'point6miner_ui.py') $package
Copy-Item (Join-Path $PSScriptRoot 'windows_resources.py') $package
Copy-Item (Join-Path $PSScriptRoot 'Start-Miner.cmd') $package
Copy-Item (Join-Path $PSScriptRoot 'README.md') $package
Copy-Item (Join-Path $root 'licenses') $package -Recurse
Get-ChildItem (Join-Path $root 'source') -Recurse -File | Where-Object { $_.FullName -notmatch '[\\/](bin|obj)[\\/]' } | ForEach-Object {
  $relative = [System.IO.Path]::GetRelativePath($root, $_.FullName)
  $destination = Join-Path $package $relative
  New-Item -ItemType Directory -Force (Split-Path -Parent $destination) | Out-Null
  Copy-Item $_.FullName $destination
}
$pins = [ordered]@{}
foreach ($name in @('Point6Miner.Cli.dll','Point6Miner.Core.dll','Point6Miner.Cli.runtimeconfig.json','Point6Miner.Cli.deps.json','point6miner-equihash.exe','windows_resources.py')) {
  $pins[$name] = (Get-FileHash (Join-Path $package $name) -Algorithm SHA256).Hash.ToLowerInvariant()
}
$pins | ConvertTo-Json | Set-Content -Encoding utf8NoBOM (Join-Path $package 'WINDOWS-PINS.json')
