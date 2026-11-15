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

[Full setup instructions](docs/SIMPLE-SETUP.md) · [Setup FAQ](docs/FAQ.md) · [Pool help](https://pointsixpool.com/getting-started)

## Performance and hardware

This beta needs an x86_64 AVX2 CPU and at least **3 GiB free RAM**. It does not mine with GPUs or phones. Auto starts conservatively; stop before changing the speed control. Measured presets require at least 30 minutes, 20 accepted shares and complete energy readings.

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


Development RAM update: total installed RAM and currently available RAM are different. The revised low-speed setting requires1GiB available, with an additional0.5GiB for each extra CPU thread (maximum4). Close unused applications/tabs or choose a lower speed if the check refuses startup. Drive free space is separate. Windows CI and the refreshed downloadable build must pass before this change is advertised as released.
