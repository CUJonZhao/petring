# Stage 1 Handoff - 2026-08-12

This note records the completed work and the next safe steps for the Delta collar prototype. Read this file at the start of the next working session.

## Completed Today

- Cloned and prepared the `CUJonZhao/petring` repository.
- Confirmed the Adafruit ESP32 Feather V2 is detected over USB at 115200 baud and identified it as an ESP32-PICO-V3-02 with 8 MB flash.
- Connected the Adafruit LSM6DSOX to the Feather through the STEMMA QT cable.
- Verified I2C address `0x6A` and `WHO_AM_I` value `0x6C`.
- Added and uploaded two PlatformIO firmware projects:
  - `firmware/bringup_i2c_scanner`: I2C connection check.
  - `firmware/imu_raw_stream`: IMU streaming, battery-voltage trend logging, browser dashboard, and Wi-Fi configuration.
- Completed a 10-minute static USB bench test: 12,003 valid IMU samples over 599.95 seconds, with no reset during the test.
- Completed a 10-minute battery-only bench test: 599.31 seconds, with battery-voltage trend from 3.936 V to 3.908 V. This is a short bench test, not a full-runtime test.
- Configured the ESP32 to join the apartment Wi-Fi through its local setup page. The address obtained on 2026-08-12 was `http://172.24.23.76`; it is DHCP-assigned and may change after a router or device restart.
- Verified the dashboard and `/api/latest` work over apartment Wi-Fi.
- Changed the firmware so the `Delta-Collar` recovery AP turns off after joining apartment Wi-Fi. It automatically comes back if the apartment Wi-Fi connection is unavailable.
- Measured the ESP32 module shield at about 35 C using an IR thermometer while the board was operating. The battery, JST connection, and other board areas were not noticeably warm.
- Connected the LiPo through the inline JST switch with USB attached. With the switch set to `ON`, the Feather `CHG` LED illuminated, confirming charging had started. Do not assume charging completed unless the `CHG` LED later turns off.
- Committed and pushed the above firmware, test records, and the correct enclosure-space reference image as Git commit `feb8ff6`.

## Current Hardware State

- Feather, LSM6DSOX, LiPo, inline switch, and USB were connected at the end of the session.
- The LiPo charge process was in progress, indicated by the orange `CHG` LED.
- The original 70 x 42 x 23 mm enclosure is too tight for a safe flat layout containing the Feather, LiPo, IMU, and cable. Do not force parts into it or stack/compress the LiPo.
- A larger Zulkit enclosure was ordered: 90 x 70 x 28 mm external dimensions. Verify its actual internal dimensions and lid clearance when it arrives.

## Tomorrow: Enclosure Arrival Plan

1. Before handling or arranging components, unplug USB and set the inline battery switch to `OFF`. Keep the LiPo on a non-conductive surface.
2. Inspect the new box for internal screw posts, sharp plastic, and its usable internal length, width, and height. Do not assume the advertised external dimensions equal its internal space.
3. Do a powerless dry fit first: Feather, IMU, JST switch, and cables only. Confirm the USB port, switch, and STEMMA QT cable can exit without a sharp bend or pinch.
4. Add the LiPo only after the board layout is settled. It must lie flat, remain removable for inspection, and have no contact with screw posts, PCB corners, or the lid. Do not glue, tape over, bend, puncture, or compress the battery.
5. Close the lid gently without fastening it. If any force is needed, stop and change the layout. The assembly needs visible clearance, not a press-fit.
6. With the battery switch still `OFF`, run the Feather from USB in the closed box for 15 minutes while supervised. Use the IR thermometer on the outer box near the ESP32 position. Stop for fast temperature rise, odor, discoloration, reset, or a hot connector.
7. If the enclosed USB test is normal, repeat a 15-minute supervised test on battery power with USB removed. Keep the box on a desk; do not attach it to Delta yet.
8. Only after both enclosure bench tests pass, perform the planned motion calibration: 2 minutes still, 1 minute normal hand movement, and 1 minute gentle turning/stopping. Download the Dashboard browser CSV for threshold review.
9. A first short collar-fit test must be supervised, with the enclosure mounted so it cannot shift, press into Delta, or expose any cable/battery. Do not charge while worn or while the enclosure is closed.

## Safety Limits

- Charge only while attended, on a hard non-flammable surface, with the battery not enclosed or compressed.
- Stop immediately for battery swelling, heat at the battery or JST connector, odor, discoloration, smoke, unexpected resets, or a board/enclosure temperature that rises rapidly.
- The dashboard `battery_v` reading is an approximate voltage trend, not a precise remaining-capacity indicator.
- This is an engineering prototype, not a veterinary diagnostic device.

## Resume Prompt

Use this in the next Codex task:

> Continue the Delta collar Stage 1 build from `docs/2026-08-12_stage1_handoff.md`. The larger enclosure has arrived. Guide the safe powerless dry fit first, then the enclosed USB and battery bench tests. Do not recommend wearing it on Delta until those checks pass.
