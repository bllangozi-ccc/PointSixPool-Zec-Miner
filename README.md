> Development update: [simple configured desktop downloads and two-step Linux installation](docs/SIMPLE-SETUP.md) are being qualified on `windows-beta`. [Setup FAQ](docs/FAQ.md). Windows and Linux candidate build checks passed; website delivery and public download replacement await exact release approval. Existing released downloads remain unchanged until approval.

# PointSixPool Zec Miner

**Official pool: [pointsixpool.com](https://pointsixpool.com)** · [ZEC pool](https://pointsixpool.com/pools/zec) · [Start mining](https://pointsixpool.com/start-mining?coin=zec)

Previously published as Point6Miner (.6Miner). The current beta retains its original package and executable names.

CPU mining with a local browser interface for Linux desktops and servers. Connect to PointSixPool’s Zcash mainnet MICRO mode with your public wallet address and a unique worker name. **Pool fee: 0.6%.**

[Download the Linux beta](https://github.com/bllangozi-ccc/PointSixPool-Zec-Miner/releases/tag/v0.6.0-beta1) · [Pool setup](https://pointsixpool.com/start-mining?coin=zec) · [Live pool statistics](https://pointsixpool.com/pools/zec) · [Public stats API](https://pointsixpool.com/developers/pool-api)

## Choose your platform

| Platform | Availability | How it runs |
| --- | --- | --- |
| Linux desktop · x86_64 AVX2 | 0.6.0 beta1 | Local browser UI |
| Linux server · x86_64 AVX2 | Same Linux package | Headless launch, local-only control UI |
| Windows desktop | Not released | Native build and runtime qualification pending |
| macOS, GPU and other coins | Not released | Future work |

Desktop and server are two launch modes of the same Linux build. Do not run the Linux download as a Windows application.

## Quick start · Linux desktop

Install Python 3, the official [.NET 10 runtime](https://learn.microsoft.com/dotnet/core/install/linux), and `taskset` (util-linux). You need an AVX2-capable x86_64 CPU and at least 3 GiB of free memory.

1. Download the `.tar.gz` and `SHA256SUMS` from Releases.
2. Run `sha256sum -c SHA256SUMS` alongside the downloaded archive.
3. Extract the archive and open a terminal in its directory.
4. Run as your normal user:

```bash
python3 point6miner_ui.py
```

Enter a public ZEC receiving address, choose a unique WorkerName such as `Point6-Rig`, and press Start. The mining identity is **WalletAddress.WorkerName**. Registered PointSixPool IDs are also supported subject to server authorization.

MICRO preset: `stratum+tcp://zec4.pointsixpool.com:3034`. The public UI uses this fixed preset. This is not a claim that source code cannot be modified.

## Linux server

Use the same package on the server:

```bash
python3 point6miner_ui.py --no-browser
```

The control interface listens on `127.0.0.1` only. Use it on the same host. It is not a public web service. No server login or remote access credentials are part of miner configuration.

## Performance and controls

Choose 1–4 available CPU threads; the default is one. This release uses a thread selector, not a percentage performance slider. Choose a session of 1–24 hours. Mining starts only after Start; Stop ends the child process group. There is no installation-time mining or automatic startup service. An uncertain share acknowledgement stops the session rather than replaying a share.

## Rewards, fees and expectations

MICRO contributes eligible work to the shared PPLNS pool. **Accepted shares are not an immediately payable balance.** Rewards require actual pool blocks, maturity and eligible work. The pool fee is **0.6%** and the MICRO payout minimum is **0.001 ZEC**. See the [current reward rules](https://pointsixpool.com/payout-models) before mining.

CPU mining is much slower than Zcash ASIC mining. Electricity can exceed rewards; no earnings or block-finding rate is guaranteed. This beta does not include GPU mining, temperature telemetry or Windows binaries. Public PPS+ is coming soon, not available in this release.

## Integrity, source and support

The release archive is the existing website package, with unchanged executable bytes. SHA-256 checksums detect file changes; they are not an independent audit or operating-system code-signing certificate. `PACKAGE-MANIFEST.PUBLIC.json` describes the complete downloadable package; binaries are attached to Releases rather than committed here.

Source and upstream notices are included under `source/` and `licenses/`. Third-party components retain their respective terms. See [NOTICE.md](NOTICE.md). Do not infer a blanket open-source licence for files without an explicit licence notice.

Ask setup questions through [GitHub Issues](https://github.com/bllangozi-ccc/PointSixPool-Zec-Miner/issues) or [pool help](https://pointsixpool.com/getting-started). Never post a private key, recovery phrase, password or authentication token.
