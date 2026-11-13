# PointSixPool · facts for mining-pool directories

Operator-provided information, checked 13 November 2026. Inclusion is subject to each directory’s independent review. Live statistics change: use the API freshness fields rather than copying a fixed hashrate.

| Field | Published information |
| --- | --- |
| Name | PointSixPool |
| Coin | Zcash (ZEC), mainnet |
| Algorithm | Equihash 200,9 |
| Pool fee | **0.6%** |
| Open modes | PPLNS, SOLO, MICRO |
| MICRO accounting | Eligible joined PPLNS work; lower share difficulty |
| PPS+ | Coming soon; not open |
| Guest identity | WalletAddress.WorkerName |
| PPLNS endpoint | stratum+tcp://zec1.pointsixpool.com:3031 |
| SOLO endpoint | stratum+tcp://zec3.pointsixpool.com:3033 |
| MICRO endpoint | stratum+tcp://zec4.pointsixpool.com:3034 |
| Published payout minima | PPLNS/SOLO: 0.01 ZEC; MICRO: 0.001 ZEC |
| Verification contact | mining@pointsixpool.com |

## Primary sources

- [Current ZEC pool and activity](https://pointsixpool.com/pools/zec)
- [Current setup](https://pointsixpool.com/start-mining?coin=zec)
- [Reward, fee and payment rules](https://pointsixpool.com/payout-models)
- [Directory adapter JSON](https://pointsixpool.com/api/listing/stats)
- [Aggregate real-work JSON](https://pointsixpool.com/api/mining/stats)
- [API documentation and freshness semantics](https://pointsixpool.com/developers/pool-api)
- [Point6Miner Linux beta download](https://github.com/bllangozi-ccc/PointSixPool-Zec-Miner/releases/tag/v0.6.0-beta1)

A new, small pool can have long periods without a block. PPLNS/MICRO rewards require eligible work and actual mature pool blocks. SOLO rewards depend on finding a qualifying block. Accepted shares, deposits and operator payment tests must not be presented as mined income. No guaranteed returns, third-party endorsement, shielded-payout support or lowest-fee claim is made.

Wallet-based mining means no account signup is needed for that connection route. A transparent wallet address, network traffic and public blockchain activity are not anonymous merely because registration is optional.
