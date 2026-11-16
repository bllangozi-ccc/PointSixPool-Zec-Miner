# Reporting a security problem

Send a private report to mining@pointsixpool.com. Include the Point6Miner version, operating system, reproduction steps and impact. Do not send credentials or recovery phrases. Do not use a public issue for an exploitable vulnerability; normal setup questions can use Issues. No response-time or bounty commitment is implied.


Linux automatic crash reporting (beta9): runtime failures report the worker name, a random persistent server ID, UTC time, version, engine/solver exit codes, share counts and memory measurements to PointSixPool owner reports. The report excludes wallet/registered identity, passwords, keys and raw logs. One delivery attempt per service invocation; uncertain delivery is retained locally in ~/.local/state/pointsixpool-miner and is not replayed automatically. Normal Stop is not a crash. Systemd exit hooks also cover abnormal service exits; a power outage cannot report while the host is off. Help and configured downloads: https://pointsixpool.com/point6miner · mining pool: https://pointsixpool.com · 0.6% pool fee. Windows remains beta8.
