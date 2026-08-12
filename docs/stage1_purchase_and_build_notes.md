# Stage 1 Purchase And Build Notes

Last updated: 2026-08-12

This file preserves the practical context from the planning conversation so a new Codex task can continue the project without losing the hardware and purchase decisions.

## Project Intent

- Build a real usable prototype first, not only a paper proposal.
- First user is Delta, a 4-month-old Sheltie, about 7.5 kg, long fur, willing to wear a collar, no known health issue at planning time.
- Current priority is sleep/rest and activity recording.
- First experiments should run for a few hours, then the design can be upgraded.
- The collar module must be wireless during use; no cable tethered to a computer.
- Start with a computer/browser dashboard before moving to a phone app.
- Comfort matters more than maximum sensor accuracy in Stage 1.

## Stage 1 Architecture

- Controller: existing Adafruit ESP32 Feather/HUZZAH32 V2, USB-C, LiPo JST connector, STEMMA QT connector.
- Primary sensor: Adafruit LSM6DSOX 6-DoF accelerometer/gyroscope, STEMMA QT/Qwiic.
- Power: Adafruit 3.7 V 500 mAh LiPo battery.
- Switch: JST-PH 2-pin extension cable with on/off switch between battery and Feather.
- Communication: ESP32 connects to home Wi-Fi.
- Computer side: local browser dashboard for live motion score, rest/activity status, battery/status display, and CSV saving.
- Wearable structure: small ABS project box mounted under the collar with foam padding and removable hook-and-loop straps.

## Purchased / Recommended Items

Adafruit:

- Adafruit LSM6DSOX 6 DoF Accelerometer and Gyroscope - STEMMA QT / Qwiic, PID 4438, qty 1.
- Lithium Ion Polymer Battery - 3.7 V 500 mAh, PID 1578, qty 1.
- STEMMA QT / Qwiic JST SH 4-pin Cable - 100 mm Long, PID 4210, qty 2.
- STEMMA QT / Qwiic JST SH 4-pin Cable - 50 mm Long, PID 4399, qty 1.
- JST 2-pin Extension Cable with On/Off Switch - JST PH2, PID 3064, qty 1.

Amazon:

- XHF 3:1 adhesive-lined waterproof heat shrink tubing kit, black.
- SEEKONE 350 W mini heat gun.
- 3M 1/2 inch foam double-sided mounting tape.
- Nettbe 6 inch reusable hook-and-loop cable ties.
- MYFAMIREA 1/8 inch adhesive neoprene foam padding sheets.
- HoHaing ABS project box, 2.76 x 1.65 x 0.91 inch / 70 x 42 x 23 mm.

## Existing Hardware Notes

- The ESP32 Feather/HUZZAH32 V2 has male headers soldered.
- The 128x32 Monochrome OLED FeatherWing also has male headers soldered.
- Because both boards have male headers, the OLED cannot directly stack on the Feather as-is.
- For the wearable Stage 1 build, skip the OLED to reduce height and complexity.
- The OLED can still be used later for bench debugging if connected with jumpers/breadboard or if headers are reworked.
- Existing Adafruit ADXL345 accelerometer can be used for I2C practice and as a backup/comparison sensor, but the LSM6DSOX remains the preferred Stage 1 sensor because it includes a gyroscope.

## Mechanical Notes

- The original 70 x 42 x 23 mm project box is too tight for a safe flat layout containing the ESP32 Feather, LiPo, IMU, and wiring. Do not force or stack parts inside it.
- Use the larger 90 x 70 x 28 mm external-dimension project box selected after the first dry fit. Verify its usable internal dimensions and lid clearance before assembly.
- Place adhesive foam on the box side facing Delta/collar; do not put adhesive directly on fur or skin.
- Use hook-and-loop straps around the collar/module so the assembly is removable and adjustable.
- Keep the hard strap head away from the dog-facing side.
- Avoid permanent glue on the LiPo so the battery can be inspected and replaced.

## LiPo Safety Notes

- The Adafruit 500 mAh LiPo has a JST-PH plug compatible with Adafruit Feather boards.
- It includes protection circuitry, but that does not make it risk-free.
- Charge only through a LiIon/LiPo constant-current/constant-voltage charger, such as the Feather's onboard charger via USB-C.
- Charge current should be 500 mA or less for this 500 mAh battery.
- Do not charge or test unattended.
- Do not bend, crush, puncture, short, or compress the battery.
- In the project box, make sure the battery is not pressed by screw posts, PCB corners, or the box lid.
- Adafruit LiPo polarity matches Adafruit boards; avoid random third-party LiPo packs unless polarity is verified.

## First Build Sequence

1. Confirm ESP32 Feather powers from USB-C.
2. Connect LSM6DSOX to Feather using STEMMA QT/Qwiic.
3. Run an I2C scanner to confirm the sensor appears.
4. Stream raw IMU values over serial.
5. Connect ESP32 to Wi-Fi and expose a minimal browser page or WebSocket endpoint.
6. Build a simple dashboard showing motion score and current rest/activity state.
7. Save CSV logs during short supervised tests.
8. Mount electronics in the project box without OLED for the first wearable trial.
9. Run a short non-wear bench test, then a supervised collar fit test, then a 30+ minute data test.

## Follow-Up Prompt For New Codex Tasks

When starting a new task in this folder, ask Codex:

Please read `D:\petring\README.md`, `D:\petring\docs\stage1_purchase_and_build_notes.md`, and `D:\petring\docs\canine_resting_vitals_smart_collar_proposal_v3_delta_first.md`, then continue the Delta smart collar Stage 1 build.
