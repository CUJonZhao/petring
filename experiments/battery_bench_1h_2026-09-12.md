# Battery-only bench run — 2026-09-12

## Result

**PASS for one-hour unattended battery runtime.** After the user removed USB
power and later reconnected it, the board's persisted battery log contained one
continuous battery-powered segment lasting **3,781.961 s** (63 min 02 s). It
had 127 voltage samples with no backwards uptime jump, so no reset occurred
during the run.

| Measurement | Result |
|---|---:|
| Duration | 63 min 02 s |
| Battery-log rows | 127 |
| Logged interval, median | 30.020 s |
| Logged interval, range | 29.254–30.050 s |
| Start voltage | 3.914 V |
| End voltage | 3.756 V |
| Lowest observed voltage | 3.732 V |
| Voltage change | -0.158 V |

The board then rejoined the home Wi-Fi. A local status query reported the IMU
ready, 3.7 MiB free recording space, no current recording, and no pending cloud
upload. The private website continued to show the device at home.

## Method

The existing firmware appends its battery-voltage reading to LittleFS every 30
seconds. After USB was reconnected, its read-only `/api/battery-log` endpoint
was retrieved and the segment beginning at 3.914 V was identified by the
monotonic `millis()` timestamps. The next segment begins after USB power was
restored, so it is excluded.

`battery_v` is the Feather's onboard voltage-divider reading. It is useful for
the trend here, but it is not a calibrated state-of-charge estimate.

## Scope and remaining work

This run proves unattended battery supply, voltage logging, and the absence of
a reset for more than one hour. It did **not** trigger a motion recording:
there is no new session in the cloud history. It therefore does not test
full-rate sampling gaps, flash writing during a continuous one-hour record, or
automatic upload of such a record.

The next technical validation is a one-hour **manual recording** on battery
power, followed by reconnecting at home and checking its session, sampling-gap
distribution, voltage trend, and automatic upload. Dog-worn testing remains
deferred until the user resumes it.
