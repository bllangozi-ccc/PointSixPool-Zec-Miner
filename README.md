# PointSixPool Zec Miner

**[PointSixPool](https://pointsixpool.com)** · [Configured downloads](https://pointsixpool.com/point6miner) · [ZEC pool](https://pointsixpool.com/pools/zec) · [Live statistics](https://pointsixpool.com/profits) · [Public API](https://pointsixpool.com/developers/pool-api)

Windows and Linux CPU mining for PointSixPool's Zcash mainnet MICRO mode. **Pool fee: 0.6%.** Previously called Point6Miner (.6Miner).

## Choose your setup

| Platform | Start here |
| --- | --- |
| Windows desktop | Download your configured ZIP, extract all files, open **PointSixPool Miner.exe**, press **Start Mining**. Python and .NET are bundled. |
| Linux desktop | Download your configured ZIP, extract all files, open **Start-Desktop**, press **Start Mining**. Python3 and taskset are needed; .NET is bundled. |
| Linux server | Choose Linux server on the miner page. In your root terminal run its generated install command, then `/start-mining`. |

Use **[the miner page](https://pointsixpool.com/point6miner)** to choose your public ZEC wallet or your own verified saved mining ID, machine name and region. Settings are included as a separate public configuration file. No account password, session token, payment key or seed is downloaded.

Opening or installing the application does not start mining. Root installs the Linux server service; actual mining runs as the dedicated `pointsix-miner` user. Stop with `/stop-mining`. Reboot autostart is optional, with instructions printed by the installer.

[Zcash pool and ASIC setup guide](docs/ZCASH-POOL-SETUP.md) · [Full setup instructions](docs/SIMPLE-SETUP.md) · [Setup FAQ](docs/FAQ.md) · [Pool help](https://pointsixpool.com/getting-started)

## Performance and hardware

This beta needs an x86_64 AVX2 CPU and **1 GiB available RAM for one CPU thread, plus 0.5 GiB per extra thread**. It does not mine with GPUs or phones. Auto starts conservatively; stop before changing the speed control. Measured presets require at least 30 minutes, 20 accepted shares and complete energy readings.

### Server use and manual controls

The two-step server setup offers **Shared server** (default) or **Mining Server**. Auto chooses an initial CPU allocation from the server's actual CPU affinity and available RAM. Shared leaves more headroom; Mining Server uses more of the supported capacity while retaining system headroom. Auto remains capped at four threads; manual selection supports up to twelve, subject to CPU and available RAM checks. This is resource selection, not continuous benchmark tuning.

You can instead choose 1–12 CPU threads and optionally enter available RAM in GB. The installer rejects choices exceeding measured capacity; an entered RAM figure can only lower the measured budget. Stop mining before rerunning setup to change server choices. Windows and Linux desktop keep their manual performance slider: stop, adjust, restart.

To check memory on Windows, press **Ctrl+Shift+Esc → Performance → Memory → Available**. Use More details if needed. On the Linux server, run `free -h` and read **Available**. Use free system RAM, not drive space or GPU memory. Save work and close unused apps if RAM is low. The miner checks available RAM again when starting.

Supported temperature sensors trigger reduced speed at 75°C and stopping at 85°C. Missing readings remain unavailable. Windows can read an already-running compatible LibreHardwareMonitor provider; the miner installs no sensor driver. Efficiency uses acknowledged difficulty-weighted work and sampled CPU-package energy, excluding the rest of the computer. It is not a profit forecast.

The Linux runtime is bundled and does not require system ICU. Windows opens a native interface; Linux opens a local browser interface. Uncertain share acknowledgements stop rather than replaying the share. Mining is never run in GitHub Actions; build checks use help, settings import and non-mining lifecycle tests.

## Pool and rewards

The normal interface selects **ZEC MICRO**, port **3034**. The mining identity is **WalletAddress.WorkerName**, or an authorized registered mining ID. Use a unique name for each machine. **View my stats & earnings** opens your public worker group or signed-in dashboard.

EU, USA and ASIA choose matching hostnames. All currently route to one European server with shared accounting; they are not separate regional facilities. Regional rankings remain unavailable until connection attribution is verified.

MICRO contributes eligible work to the shared PPLNS pool. Accepted shares are not an instantly payable balance: rewards require actual blocks, maturity and eligible work. **0.6% pool fee; MICRO minimum payout 0.001 ZEC.** Network fees are separate. CPU electricity can cost more than rewards. [Reward rules](https://pointsixpool.com/payout-models). Public PPS+ is coming soon; ASIC PPLNS and SOLO setup is separate.

## Advanced downloads, integrity and support

The editable Linux archive and an unconfigured Windows executable are available in [Releases](https://github.com/bllangozi-ccc/PointSixPool-Zec-Miner/releases). The website's configured download is the easiest route. Check SHA256SUMS against downloaded files. Checksums detect changes; they are not an independent audit or an operating-system signing certificate.

Source availability is not a claim that modified software cannot connect elsewhere. Third-party components retain their own terms; see [NOTICE.md](NOTICE.md) and `licenses/`. Do not infer a blanket open-source licence for files without an explicit licence notice.

[GitHub support](https://github.com/bllangozi-ccc/PointSixPool-Zec-Miner/issues) · [Forum guides](https://pointsixpool.com/forum). Never post private keys, recovery words, passwords or login tokens.


## Miner error codes

Choose **Report error** on the dashboard or **Send error to PointSixPool** in Help. This explicit click sends the error code and basic counters through our existing support form to Owner Reports. A saved report returns a reference. No wallet, mining ID, credentials or full logs are included. The dashboard includes a compact dark dashboard and recorded accepted-share graph. Windows and Linux beta10 passed native build checks; a separate 16-minute Linux mining test recorded 1,284 accepted shares, zero rejects and zero uncertain acknowledgements.

| Code | Meaning | Next step |
|---|---|---|
| P6M-E101 | The engine ended without its complete result. The UI shows its exit status and any reported error type. | Copy the code, exit status, CPU thread setting and approximate run time. Report these; the cause is not inferred from this code alone. |
| P6M-E102 | The engine returned an invalid result. | Keep mining stopped and report the code. |
| P6M-E103 | A share acknowledgement or final share accounting is uncertain. | Keep mining stopped and report the code. The submitted proof is never replayed. |

A green fan shows an authorized connection; accepted shares confirm work. A stopped engine requires attention. This diagnostic update does not establish the cause of the reported five-minute Windows stops.

Performance: Auto remains conservative, with a maximum of 4 CPU threads. Stop mining to select up to 12 threads manually; the miner checks available CPU threads and free RAM before starting. Twelve threads require at least 6.5 GiB available RAM. Start low and increase gradually. Thermal protection requires a detected supported sensor.


Linux automatic crash reporting: runtime failures report the worker name, a random persistent server ID, UTC time, version, engine/solver exit codes, share counts and memory measurements to PointSixPool owner reports. The report excludes wallet/registered identity, passwords, keys and raw logs. One delivery attempt per service invocation; uncertain delivery is retained locally in ~/.local/state/pointsixpool-miner and is not replayed automatically. Normal Stop is not a crash. Systemd exit hooks also cover abnormal service exits; a power outage cannot report while the host is off. Help and configured downloads: https://pointsixpool.com/point6miner · mining pool: https://pointsixpool.com · 0.6% pool fee. Both downloads are beta10. Auto is capped at four resource-checked threads; manual selection allows up to twelve. Unknown battery status no longer forces one thread; detected battery power retains its lower limit. Cancellation cleanup contains operating-system process errors, and Linux runtime aborts retain a diagnostic label without routine disk logs or core files.
