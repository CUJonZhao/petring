# IMU raw stream

This Stage 1 test firmware configures the LSM6DSOX for a 104 Hz accelerometer (+/-4 g) and gyroscope (+/-500 deg/s) sample rate. It sends a CSV row to USB serial every 50 ms and samples the Feather's battery-voltage divider once per second.

It also runs a password-protected Wi-Fi access point:

- Network: `Delta-Collar`
- Password: `deltacollar`
- Dashboard: `http://192.168.4.1`

Connect a computer to the `Delta-Collar` network, then open the dashboard address in a browser. The dashboard shows live sensor data, a simple Resting/Active state, battery voltage, a short activity chart, and browser-side CSV export. It does not require a home Wi-Fi password or an internet connection.

To also use the dashboard while the computer stays on home Wi-Fi, open `http://192.168.4.1/setup` while connected to `Delta-Collar`. Enter the home network name and password in that page. After the ESP32 connects, the page displays its new local IP address and stops the temporary access point to reduce normal operating power. If the home network becomes unavailable, `Delta-Collar` automatically returns for configuration or recovery.

The CSV columns are:

`ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,temp_c,motion_g,battery_v`

With the board still on a desk, the acceleration magnitude (`motion_g`) should stay near `1.0`. During tilting or hand motion, the axis values and gyroscope values should change.

## Run

1. Keep the LSM6DSOX connected to the Feather STEMMA QT port.
2. From this directory, run `pio run --target upload`.
3. Open serial at 115200 baud and collect the CSV output.

`battery_v` is an approximate voltage from the onboard 1:2 voltage divider. It is useful for tracking charge and discharge, but it is not a calibrated battery gauge.

Every 30 seconds, the firmware also saves `ms,battery_v` to ESP32 internal flash. Send `D` over USB serial to print the saved log, or `C` to clear it immediately before a battery-only run.

The IMU configuration is not persistent: it resets when the board loses power.
