# Bench Static Test - 2026-08-12

## Purpose

Verify that the ESP32 Feather V2, LSM6DSOX, STEMMA QT connection, and USB serial data path remain stable during a ten-minute desk-rest test.

## Setup

- ESP32 Feather V2 powered by USB-C.
- LSM6DSOX connected through the Feather STEMMA QT port.
- `firmware/imu_raw_stream` configured the IMU for 104 Hz at +/-4 g and +/-500 deg/s.
- Firmware emitted CSV samples at 20 Hz.
- Board and sensor remained on a desk without intentional movement.

## Result

The test passed.

| Measurement | Result |
|---|---:|
| Logged duration | 599.95 s |
| Samples | 12,003 |
| Invalid serial lines | 0 |
| Sample rate | 20 Hz |
| Motion magnitude | 0.9828 to 1.0750 g |
| Peak gyroscope magnitude | 80.82 deg/s |

The host terminal could not keep a single ten-minute serial process alive, so data was captured in four 150-second windows. The ESP32 stayed powered throughout. Its device timestamp increased from 863,992 ms to 1,554,642 ms across all windows, confirming that it did not reset. The 27.0-32.4 second gaps are host-side logging gaps between windows, not gaps in ESP32 uptime.

The brief 80.82 deg/s peak in the first window is consistent with an external disturbance; all windows had continuous valid data and no I2C errors.

## Raw Data

- `data/raw/bench_static_10min_part1_2026-08-12.csv`
- `data/raw/bench_static_10min_part2_2026-08-12.csv`
- `data/raw/bench_static_10min_part3_2026-08-12.csv`
- `data/raw/bench_static_10min_part4_2026-08-12.csv`
