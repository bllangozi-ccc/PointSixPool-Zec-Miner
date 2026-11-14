# PointSixPool Zec Miner — next desktop/server update

This is development-source guidance. Existing published beta downloads remain unchanged until the new package is qualified and released.

## Windows desktop

The new self-contained executable is named `PointSixPool-Zec-Miner.exe`. Open it directly: no terminal commands, separate Python install or .NET runtime install. Enter your public **Wallet Address** or registered pool ID, **Worker Name**, choose **ZEC**, then press **Start Mining**. Opening the app does not start mining.

Performance starts in **Auto**: conservative CPU allocation based on available cores, free RAM and battery power. Drag the bar to override, or press Auto again. Stop mining before changing performance. This controls CPU threads, not temperature. The app uses CPU mining; GPU and Android/iOS support are not included.

Press **Stop Mining** or close the app to terminate its child mining processes. Never enter wallet seeds, private keys or payment passphrases.

## Linux server

From the extracted next-version package, run `./Start-Server` as your normal user. The first run asks for your wallet/ID, worker name and optional CPU-thread override. Auto is the default. Saving setup starts MICRO mining. Future runs reuse that setup.

- `./Start-Server --setup`: change the saved setup.
- `./Start-Server --enable-autostart`: enable the saved worker as a supervised user service. It starts after login; reboot-before-login additionally requires administrator-enabled user lingering. The wizard reports whether that is present.
- `./Start-Server --stop`: stop the service.
- `./Start-Server --disable-autostart`: stop and disable automatic startup.
- `./Start-Server --status`: inspect the service.

Foreground mining stops with Ctrl+C. Service control never restarts a session with uncertain share acknowledgements. The normal-user package requires Linux x86_64/AVX2, Python3, .NET10 and taskset; no prerequisite installer is bundled yet.

Official pool: https://pointsixpool.com · MICRO: zec4.pointsixpool.com:3034 · fee0.6% · minimum0.001ZEC. Earnings require actual mature blocks and eligible work; accepted shares alone are not spendable earnings.
