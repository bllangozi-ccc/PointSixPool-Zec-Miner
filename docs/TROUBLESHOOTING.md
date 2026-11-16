# Miner troubleshooting

Use **Copy diagnostics** to share the error code without your wallet, account ID or credentials. **Report error** sends only the displayed code, bounded engine reason and mining counters; success includes a receipt reference.

| Code | Meaning | Next step |
| --- | --- | --- |
| P6M-E101 | Engine ended without a complete result | Copy diagnostics. A solver reason identifies a local backend failure; do not repeatedly restart it. |
| P6M-E102 | Engine result was invalid | Stop and report the code. |
| P6M-E103 | A submitted share has an uncertain acknowledgement | The miner stops and never replays that proof. Report the code. |
| P6R-E201 | Report DNS lookup failed | Check DNS or open https://pointsixpool.com/report-error in your browser. |
| P6R-E202 | HTTPS certificate verification failed | Check the device clock and trusted certificates. Never disable HTTPS verification. |
| P6R-E203 | Report connection timed out | Check the connection; delivery is not confirmed. |
| P6R-E204 | Report connection failed | Check firewall/proxy/network settings. Copy diagnostics or use the browser report form. |
| P6R-E205 | Secure connection failed | Check network security/proxy settings. |
| P6R-E206 | Report response could not be read | Copy diagnostics and use the browser report form. |

A `form` report error occurred before submission. A `receipt` error means submission may have arrived; do not repeatedly resend it. The app does not retry reports automatically.

A disconnected pool session can reconnect to fresh work after ten seconds only when its complete result accounts for every submitted share. Genuine solver failures and uncertain shares stay stopped. An intentional Linux stop exits cleanly; stopping does not erase an earlier error or replay work.

CPU temperature and power readings require supported sensors. Missing readings do not mean thermal protection is active. Available RAM, not free disk space, determines the memory limit.


Automatic performance uses up to four CPU threads, constrained by available RAM and CPUs. Battery operation starts at one thread. The Auto button moves the slider and shows the limiting reason. Stop mining before changing speed; manual selection supports up to twelve threads when resources permit.

The desktop event window keeps only the last forty messages in memory. Closing the miner discards that history. Linux retains at most twenty small crash reports, with error codes and a random server ID; routine accepted-share messages are not saved by the miner. Installed Linux services disable core files.

A Linux engine exit of -6 is reported as RuntimeAbort. This identifies an abort rather than proving a memory or connection fault. If delivery is not confirmed, the bounded diagnostic remains local; no submitted proof or uncertain report is automatically replayed.
