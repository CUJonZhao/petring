# Battery Bench Test - 2026-08-12

## Purpose

Verify that the ESP32 Feather V2 and LSM6DSOX can run from the 3.7 V 500 mAh LiPo battery for ten minutes after USB power is removed.

## Setup

- LiPo connected to the Feather through the JST-PH inline switch.
- Switch set to ON.
- LSM6DSOX connected through STEMMA QT.
- Board and battery kept on a desk with no enclosure.
- `firmware/imu_raw_stream` recorded battery voltage to internal flash every 30 seconds.

## Result

The test passed.

| Measurement | Result |
|---|---:|
| Battery-only logged duration | 599.31 s |
| Battery-only voltage range | 3.936 to 3.908 V |
| Voltage change during test | -0.028 V |
| Battery-only log records | 21 |

The device started a new uptime sequence at 759 ms when USB was removed. This is a power-source transition boundary, not a reset during the battery-only run. The following records continued without another reset through 600,068 ms.

The `battery_v` value is an approximate voltage from the Feather's onboard divider. It supports trend checking but is not a calibrated state-of-charge measurement. The 4.196 V record before the battery-only sequence was taken while USB was attached and is excluded from the battery-only comparison.

## Conclusion

The LiPo, JST switch, Feather, IMU, and internal voltage logging operated normally over the monitored ten-minute battery run. This is a short bench-supply test, not yet a full runtime or wearable validation.
