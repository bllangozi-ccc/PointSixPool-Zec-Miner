For simple instructions, open **HELP.txt** first.

# PointSixPool Zec Miner — desktop/server beta4

These instructions cover the beta4 release archive. Configured website downloads are updated separately; check the release notes for their deployment status.

## Windows desktop

The new self-contained executable is named `PointSixPool Miner.exe`. Open it directly: no terminal commands, separate Python install or .NET runtime install. Enter your public **Wallet Address** or registered pool ID, **Worker Name**, choose **ZEC**, then press **Start Mining**. Opening the app does not start mining.

Performance starts in **Auto**: conservative CPU allocation based on available cores, free RAM and battery power. Drag the bar to override, or press Auto again. Stop mining before changing performance. This controls CPU threads, not temperature. The app uses CPU mining; GPU and Android/iOS support are not included.

Press **Stop Mining** or close the app to terminate its child mining processes. Never enter wallet seeds, private keys or payment passphrases.

## Linux server

From the extracted Linux package, run `./Start-Server` as your normal user. The first run asks for your wallet/ID, worker name and optional CPU-thread override. Auto is the default. Saving setup starts MICRO mining. Future runs reuse that setup.

- `./Start-Server --setup`: change the saved setup.
- `./Start-Server --enable-autostart`: enable the saved worker as a supervised user service. It starts after login; reboot-before-login additionally requires administrator-enabled user lingering. The wizard reports whether that is present.
- `./Start-Server --stop`: stop the service.
- `./Start-Server --disable-autostart`: stop and disable automatic startup.
- `./Start-Server --status`: inspect the service.

Foreground mining stops with Ctrl+C. Service control never restarts a session with uncertain share acknowledgements. The normal-user package requires Linux x86_64/AVX2, Python3 and taskset; the .NET runtime is bundled.

Official pool: https://pointsixpool.com · MICRO: zec4.pointsixpool.com:3034 · fee0.6% · minimum0.001ZEC. Earnings require actual mature blocks and eligible work; accepted shares alone are not spendable earnings.

## Hardware, heat and efficiency

Devices shows detected CPU availability. This release still mines with the CPU only.
Linux reads supported CPU hwmon temperatures and readable Intel RAPL package-energy
counters. No root privileges or sensor driver installation is requested. Windows reads supported CPU sensors through an already-running LibreHardwareMonitor WMI provider. It does not install or elevate a driver. The app cannot provide thermal protection without a supported sensor. Firmware cooling and thermal limits must remain enabled.

At 75°C, a supported CPU sensor triggers a one-CPU affinity limit for the miner
and its descendants. At 85°C, mining stops. Lost sensors after throttling also stop mining.
Cooling never automatically increases speed or restarts a stopped session. Press Stop,
let the host cool, then Start manually. These are conservative software thresholds,
not guarantees against overheating or replacements for the manufacturer's limits.

Efficiency uses acknowledged shares weighted by their actual assigned 256-bit target.
The displayed accepted-work/J measure is a statistical work estimate, not measured solver
hashrate or earnings. Power covers CPU packages only, excluding GPU, memory, fans and PSU.
Missing readings, counter discontinuities, or long sampling gaps keep results unavailable.
Measured Auto presets need at least 30 minutes and 20 accepted shares with complete energy
coverage. Results remain local, contain no wallet details, and are never fabricated.
Until qualified measurements exist, Auto keeps the conservative initial recommendation.

## Region selection

Choose EU, USA or ASIA. The miner selects the matching MICRO endpoint automatically:
`zec4.pointsixpool.com:3034`, `usa.zec4.pointsixpool.com:3034`, or
`asia.zec4.pointsixpool.com:3034`. All three currently use the same EU server.
The miner remains MICRO-only; the website separately explains PPLNS and SOLO.

Windows optional sensors: use the official [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) application. Some sensors require that separate application to run with administrator permission; our miner stays unelevated. Sampled CPU-package watts are integrated over time and exclude the rest of the machine. Sensor support and readings must be checked on the actual PC.

Performance: Auto remains conservative, with a maximum of 4 CPU threads. Stop mining to select up to 12 threads manually; the miner checks available CPU threads and free RAM before starting. Twelve threads require at least 6.5 GiB available RAM. Start low and increase gradually. Thermal protection requires a detected supported sensor.
