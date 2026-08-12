# ESP32 I2C bring-up

This is the first hardware check for the Stage 1 collar. It scans the ESP32 Feather V2 STEMMA QT I2C bus every three seconds and reports detected addresses through USB serial at 115200 baud.

With the LSM6DSOX connected by a STEMMA QT/Qwiic cable, expect the sensor at `0x6A` or `0x6B`.

## Run

1. Keep the LSM6DSOX connected to the Feather STEMMA QT port.
2. From this directory, run `pio run --target upload`.
3. Run `pio device monitor` to see the scan output.

The firmware only reads the I2C bus. It does not change the IMU configuration.
