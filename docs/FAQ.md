# PointSixPool Miner setup FAQ — development candidate

These instructions describe the configured-download update on `windows-beta`.
They do not change the availability or requirements of older public releases.
Pool: https://pointsixpool.com · Miner page: https://pointsixpool.com/point6miner

## Do I need an account?
No. Use a public ZEC receiving wallet and a unique machine name. Signed-in users can
select their own verified saved mining ID; a verified saved wallet is the fallback.
The settings file contains public mining details only, never a login token or private key.

## How do I start on Windows?
Download your configured Windows ZIP, extract every file together, then open
**PointSixPool Miner.exe**. Check the details and press **Start Mining**.
Python and .NET are bundled. Opening the application does not start mining.

## How do I start on a Linux server?
Choose Linux server on the miner page. In your root terminal run the generated
installation command. After it finishes, type `/start-mining`.
Root installs the service; the actual miner runs as the dedicated `pointsix-miner` user.
Use `/stop-mining` to stop. Reboot autostart is optional and is printed by the installer.
Installation never starts or enables mining by itself.

## How do I start on a Linux desktop?
Extract the configured ZIP and open **Start-Desktop**. Check the settings in the local
browser and press Start Mining. Python3 and taskset are required; .NET is bundled.
If your file manager does not preserve executable permissions, follow its Run as program
setting for Start-Desktop. The advanced editable archive remains available.

## Which hardware and modes are supported?
This build uses an x86_64 AVX2 CPU with at least 3 GiB free memory. It does not use GPUs
or phones. It selects ZEC MICRO on port 3034. ASIC PPLNS and SOLO configurations are
separate on the pool website. PPS+ is coming soon.

## What do regions change?
EU, USA and ASIA choose the corresponding mining hostname. All currently route to the
same server in Europe and share one accounting system. They are not separate regional
facilities. Regional earnings rankings remain unavailable until attribution is verified.

## Can I reduce performance?
Auto starts conservatively. Stop before changing the performance slider. Measured
presets require at least 30 minutes, 20 accepted shares and complete energy samples.
Supported sensors trigger reduced speed at 75°C and a stop at 85°C. Missing readings
remain unavailable. Windows sensor support uses an already-running compatible
LibreHardwareMonitor provider; no sensor driver is installed by this miner.

## Is the efficiency figure my profit?
No. It measures acknowledged, difficulty-weighted work per CPU-package energy.
It excludes other machine power and is not a guaranteed profit or income forecast.
CPU electricity can cost more than rewards.

## Where do I see earnings?
Use **View my stats & earnings** in the miner. Wallet miners open their public worker
group; registered miners open their account dashboard. Accepted shares are work,
not an instantly payable balance. Rewards require actual blocks and maturity.
Pool fee: **0.6%**. MICRO minimum payout: **0.001 ZEC**. Network fees are separate.
Rules: https://pointsixpool.com/payout-models

## Can I study or modify the miner?
Yes, the editable Linux package and source remain available. Respect the component
licence notices. The normal interface uses PointSixPool MICRO; source availability
is not a claim that modified software cannot connect elsewhere.
