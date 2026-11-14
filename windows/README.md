# PointSixPool Zec Miner · Windows x64 beta

Official pool: https://pointsixpool.com · ZEC: https://pointsixpool.com/pools/zec

Use only an official published release from https://github.com/bllangozi-ccc/PointSixPool-Zec-Miner/releases. Unpublished CI artifacts remain development candidates. Windows 11 x64, AVX2 CPU, Python 3 and the official .NET 10 x64 runtime are required. At least 3 GiB free RAM is needed to start. No administrator rights are required. Install prerequisites from python.org and dotnet.microsoft.com only.

The planned portable ZIP runs from its extracted folder: double-click `Start-Miner.cmd`. It opens a local browser UI. Enter your public receiving address or authorised registered ID, and WorkerName. Use the performance slider to select 1–4 available CPU threads, then press Start. Opening the app never starts mining. Stop ends the miner process tree; closing the application terminates its inherited child processes through a Windows Job Object.

Preset: `stratum+tcp://zec4.pointsixpool.com:3034` (MICRO). The UI does not offer an external pool field. This is not protection against modifying source code. Pool fee **0.6%**, MICRO minimum **0.001 ZEC**. Eligible PPLNS rewards require mature pool blocks; CPU electricity can cost more than earnings.

No Windows service, scheduled task, autorun, background updater, administrator elevation, SSH setup, private wallet key or recovery phrase is needed. The download is an unsigned portable beta, not an Authenticode-certified installer. No claim of SmartScreen or antivirus approval is made; do not disable protection.

GitHub-hosted checks build software and exercise non-mining tests only. They do not connect to mining pools or generate proof-of-work. Any solver computation and live-share qualification must run outside Actions on owner-authorised resources.

If Windows says `py is not recognised`, Python 3 may still be installed under `python`. In the extracted miner folder, try `python -B point6miner_ui.py`. The updated launcher checks both commands. If neither works, install Python 3 from the official Python website, reopen the command window, and retry. Do not type these Windows commands into the pool server’s PuTTY session.

The new native desktop executable is under development. Its main screen has Wallet Address, Worker Name, Coin ZEC and Start Mining; all mining requires explicit Start. The self-contained candidate bundles its Python GUI and .NET mining runtime, so users need no Python commands or separate runtime installation. It remains unpublished until Windows executable checks and pool-side qualification pass. No NiceHash code, binaries or personal settings are included.
