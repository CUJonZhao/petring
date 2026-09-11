# IMU stream and offline activity recorder

**2026-09-09:** offline logging and the phone-friendly `/records` page are now
uploaded to the board. The first USB bench passed actual Wi-Fi-off recording,
CSV/binary comparison and restart persistence: 2,279 samples over 120.093 seconds,
18.97 Hz average. Synchronous flash writes caused 54 intervals over 100 ms;
timestamps preserve these gaps. One-hour battery runtime, direct power-cut
recovery and on-device full-disk behavior remain untested. See the
[physical bench report](../../experiments/offline_usb_bench_2026-09-09.md).

This Stage 1 test firmware configures the LSM6DSOX for a 104 Hz accelerometer (+/-4 g) and gyroscope (+/-500 deg/s) sample rate. It sends a CSV row to USB serial every 50 ms and samples the Feather's battery-voltage divider once per second.

It also runs a password-protected Wi-Fi access point:

- Network: `Delta-Collar`
- Password: `deltacollar`
- Dashboard: `http://192.168.4.1`

Connect a phone or computer to the `Delta-Collar` network, then open the dashboard
address in a browser. The dashboard shows live sensor data, a simple Resting/Active
state, battery voltage, a short activity chart, and browser-side CSV export.
The live chart/export still covers only about 45 seconds; use **离线记录 / 完整历史**
(`/records`) for recordings saved on the device. Neither page needs internet.

## Offline recording workflow

1. Power on. If the IMU and storage initialize successfully, a **new recording
   starts automatically**, even without a phone, router or internet connection.
2. In `/records`, check that the saved sample count increases. Closing the page
   or leaving home Wi-Fi does not stop recording.
3. Reconnect directly to `Delta-Collar`, or visit the device's local IP on home
   Wi-Fi. Press **停止并保存** before switching power off or downloading data.
4. View an entire recording, download CSV, or download the original binary file.
   The CSV has every validated saved sample, not just the browser chart window.
   Confirm the download in the phone's Files/downloads before deleting anything.
5. Press **开始新记录** to record again without rebooting. This attaches the phone's
   current date/time to the new session. Automatic boot/serial starts have relative
   time only, explicitly shown as `未设置日历时间`; no offline clock is invented.

The recorder targets 20 samples/second and preserves raw accelerometer/gyroscope
counts, sensor temperature, battery voltage, a quantized activity score and the
heuristic state. Data is buffered for at most about one second during normal
operation and flushed using checked `fflush`/`fsync`; a normal stop flushes the
remaining partial batch. Each record has a CRC. Unexpected power loss can lose
the pending batch/in-flight write; the actual power-loss behavior needs a board
test. This is not a hard real-time or lossless acquisition guarantee: flash and
network servicing may add timing gaps. The recorded timestamps preserve them.

An unclosed `.open` file is retained as **interrupted** after reboot; a new file
is created without resuming or overwriting it. Normal stops use `.bin`; full disk,
write errors and repeated IMU failures use `.full`, `.error`, `.sensor`.
Twenty consecutive IMU read failures stop recording. Previous recordings are
never automatically deleted. Full storage stops capture and is reported in the UI.

Large transfers, directory listings and deletions are rejected with HTTP 409
while recording, so a CSV download cannot pause an active session. Small status
and live dashboard requests remain available. Wi-Fi remains enabled for access
and reconnection by default. Serial `O` temporarily disables Wi-Fi without stopping
the recording; `W` restores Wi-Fi and the saved network; `N` prints network status.
These controls allow a bench test with the radio actually disabled. They do not
erase credentials and are not persistent across reboot. Cloud upload/Bluetooth
sync and a phone-page radio control are not implemented.

## Storage and migration

`partitions.csv` preserves the offsets and sizes of **all existing partitions**,
including NVS/Wi-Fi credentials and the old `spiffs` battery-log partition. The
formerly unused upper 4 MiB at `0x400000` becomes a separate `motion` LittleFS
filesystem. This partition layout is for the **8 MB Feather ESP32 V2 only**.
The build pins Espressif32 7.0.1 / Arduino 2.0.17, whose LittleFS configuration
supports three partitions; this firmware mounts two.

- New record payload: 24 bytes/sample, 32-byte session header.
- One hour at 20 Hz: **1,728,032 bytes** (~1.73 MB / 1.65 MiB), before filesystem overhead.
- A 128 KiB reserve is maintained; displayed remaining time also allows 15% for
  overhead. It estimates storage capacity, **not battery life**.
- Existing battery logs remain in their original partition.
- Mounting never uses destructive format-on-failure. A partition is initialized
  only after a full scan proves that every byte is erased (`0xff`). An unreadable
  nonempty partition is left intact, reported unavailable, and requires recovery.
- Use a normal firmware upload, which includes the new partition table. **Do not
  use `erase_flash` or `uploadfs` for this upgrade.** Back up the board's existing
  data before an upgrade. The first physical upgrade has been backed up and
  performed; all 560 pre-existing battery rows were preserved.

## Saved format and recovery

All numbers use explicit little endian encoding in `src/motion_format.h`.
Header: `DLOG`, uint16 version 1, uint16 record size 24, uint32 period 50 ms,
uint32 start uptime, uint64 optional start Unix milliseconds (0 = unknown), six
reserved bytes, CRC-16/CCITT-FALSE over the first 30 bytes.

Record: uint32 elapsed ms; three int16 acceleration counts; three int16 gyro
counts; int16 temperature count; uint16 battery mV; uint8 rounded activity score
times 255; uint8 flags (bit 0 Active); CRC-16/CCITT-FALSE over the first 22 bytes.
CRC parameters: polynomial 0x1021, init 0xffff, no reflection/final xor.
Acceleration scale is 0.000122 g/LSB, gyro 0.0175 deg/s/LSB, temperature
`25 + count/256` C. It is IMU chip temperature, not animal body temperature.

The device validates all full records before CSV export. The page also compares
the received CSV row count with `X-Delta-Records` before reporting success, and a
read failure during streaming aborts the transfer. An incomplete final
record is omitted (and its byte count shown); corrupt full records cause HTTP
422 instead of silently exporting bad measurements. Download the original binary
for independent inspection/recovery:

```sh
python3 experiments/decode_motion_log.py data/raw/delta-ID.bin data/processed/delta-ID.csv
# Only if corruption was reported: explicitly recover the intact prefix.
python3 experiments/decode_motion_log.py data/raw/delta-ID.bin data/processed/delta-ID.csv --recover-prefix
```

Run those commands from the repository root. The decoder reports record count,
last timestamp, optional start time and any recovery warnings as JSON. It writes
the CSV atomically, preserving an existing output if validation fails. CRC damage
ends recovery at the first bad record; it does not guess missing values.

Saved CSV columns:

`elapsed_ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,temp_c,motion_g,activity_score,battery_v,state`

The history page reads the full CSV and plots time-binned averages. Activity/low
activity durations use successive valid intervals <=100 ms; larger gaps and the
time before the first sample are marked uncovered. This is an exploratory
threshold summary, not a validated behavior classifier.

## Tests

```sh
# From the repository root; Python 3 + a C++11 compiler.
python3 firmware/imu_raw_stream/tests/test_offline_log.py
# With Playwright available to Node:
node firmware/imu_raw_stream/tests/records_page_test.cjs
# From this firmware directory:
pio run
```

The host test exercises the actual C++ buffer/codec with 72,000 synthetic samples,
an independent Python CSV decoder, bit corruption, every possible truncated tail,
timestamp regression, failed writes/partial buffers, and partition compatibility.
The browser test uses mocked device APIs, checks full-hour chart/download, state
controls, interrupted sessions, errors, disconnect/reconnect, deletion cancellation
and mobile overflow. These do not substitute for LittleFS/power-loss/battery tests
on the ESP32. Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to use an installed Chrome and
`DELTA_UI_TEST_OUTPUT` to choose the screenshot/download output directory.

For an attached board with this firmware already uploaded, the physical USB
bench script records 120 seconds, temporarily disables the board's Wi-Fi for
about 60 seconds, downloads and compares CSV/binary data, and uses an EN reset to
check completed/interrupted records. It creates sessions but never deletes them:

```sh
python3 experiments/validate_offline_recorder.py --port /dev/cu.usbserial-59680111041 \
  --url http://DEVICE_IP --output data/raw/offline_bench_RUN
```

Run from the repository root with `requests` and `pyserial` installed. The script
restores Wi-Fi and stops recording on exit. An EN reset is not a physical power
cut and this USB-powered run does not measure battery endurance.

To also use the dashboard while the computer stays on home Wi-Fi, open `http://192.168.4.1/setup` while connected to `Delta-Collar`. Enter the home network name and password in that page. After the ESP32 connects, the page displays its new local IP address and stops the temporary access point to reduce normal operating power. If the home network becomes unavailable, `Delta-Collar` automatically returns for configuration or recovery.

The existing USB serial CSV columns remain:

`ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,temp_c,motion_g,battery_v`

With the board still on a desk, the acceleration magnitude (`motion_g`) should stay near `1.0`. During tilting or hand motion, the axis values and gyroscope values should change.

## Run

1. Keep the LSM6DSOX connected to the Feather STEMMA QT port.
2. From this directory, run `pio run --target upload`.
3. Open serial at 115200 baud and collect the CSV output.

`battery_v` is an approximate voltage from the onboard 1:2 voltage divider. It is useful for tracking charge and discharge, but it is not a calibrated battery gauge.

Every 30 seconds, the firmware also saves `ms,battery_v` to its original internal
flash partition. Serial commands: `S` stops/saves motion recording; `R` starts a
new recording; `L` prints recording status; `D` prints the old battery log (only
when motion recording is stopped); `C` clears only the battery log. None of these
commands delete motion sessions. Stop before unplugging USB to end a session cleanly.

The IMU configuration is not persistent: it resets when the board loses power.
