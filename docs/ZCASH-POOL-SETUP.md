# Zcash mining on PointSixPool

[PointSixPool](https://pointsixpool.com) is a Zcash mainnet pool with a **0.6% pool fee**. Connect a compatible Equihash (200,9) ASIC with your own ZEC receiving address and a worker name. Wallet-based mining does not require a website account.

## Connect an ASIC

Choose the mode you want in the miner's pool settings:

| Mode | Stratum URL | How rewards work |
| --- | --- | --- |
| PPLNS | `stratum+tcp://zec1.pointsixpool.com:3031` | Eligible work shares rewards from actual pool blocks. |
| SOLO | `stratum+tcp://zec3.pointsixpool.com:3033` | The eligible finder receives the mining reward, subject to pool rules and maturity. |
| MICRO | `stratum+tcp://zec4.pointsixpool.com:3034` | Lower-speed work contributes to the shared pool. |

Use **YOUR_ZEC_WALLET.WorkerName** as the username and **x** as the password. Give each machine a different worker name so you can inspect its work separately. Never enter a private key, seed or website password in these fields.

**PPS+ is coming soon and remains closed.** Check the [live status](https://pointsixpool.com/status) before changing hardware settings. The [connection page](https://pointsixpool.com/connections#configuration-zec) is the canonical source for EU, USA, ASIA and NiceHash configuration. Regional aliases currently reach the same European service, rather than separate regional facilities.

## Follow workers and earnings

Open [Workers](https://pointsixpool.com/status#mining=workers) to inspect accepted work, sampled hashrate and history. A pool hashrate is an estimate over a sampling window; it can differ from the miner's local reading. Check the last-share timestamp and feed freshness when investigating a stopped machine.

Use [Income](https://pointsixpool.com/status#mining=income) to distinguish estimated revenue, actual block credits and settled payments. A credit is not an on-chain transfer. Settled transactions have mainnet links; unpaid credit does not have a payout transaction yet. USD values are conversions or estimates, not an additional USD payment.

The **0.6% fee** means an illustrative 1 ZEC gross eligible reward leaves 0.994 ZEC before separate network transaction charges. Rewards require actual blocks, maturity and eligible work. Account-free mining does not hide transparent blockchain transactions. Read the [payout rules](https://pointsixpool.com/payout-models) and check your own electricity costs.

## Try the Windows or Linux CPU miner

The optional [PointSixPool Miner](https://pointsixpool.com/point6miner) runs ZEC MICRO on supported x86_64 AVX2 CPUs. It does not use your GPU or phone to mine. Choose a wallet or your verified registered mining ID, a machine name and a region before downloading.

Windows and Linux desktop users open the extracted launcher and choose Start Mining. Linux server users run the generated installation command, then `/start-mining`. Installation does not start mining automatically. The server service runs as a dedicated miner user rather than root.

Auto is conservative and capped at four threads. Manual selection supports up to twelve, subject to actual CPU and available RAM checks. Stop before adjusting speed. CPU electricity can cost more than the mining revenue.

[Download and configure](https://pointsixpool.com/point6miner) · [Pool statistics](https://pointsixpool.com/profits) · [Pool API](https://pointsixpool.com/developers/pool-api) · [Forum](https://pointsixpool.com/forum)

Questions or equipment-shop setup partnerships: **mining@pointsixpool.com**.
