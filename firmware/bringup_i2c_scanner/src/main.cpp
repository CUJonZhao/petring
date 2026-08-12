#include <Arduino.h>
#include <Wire.h>

namespace {

constexpr unsigned long kScanIntervalMs = 3000;
constexpr uint8_t kLsm6dsoxAddress = 0x6A;
constexpr uint8_t kWhoAmIRegister = 0x0F;

bool readRegister(uint8_t address, uint8_t reg, uint8_t& value) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  if (Wire.requestFrom(static_cast<int>(address), 1) != 1) {
    return false;
  }

  value = Wire.read();
  return true;
}

void scanI2cBus() {
  uint8_t foundDevices = 0;

  Serial.println("I2C scan started");
  for (uint8_t address = 0x08; address < 0x78; ++address) {
    Wire.beginTransmission(address);
    const uint8_t error = Wire.endTransmission();

    if (error == 0) {
      Serial.printf("  Found device at 0x%02X", address);
      if (address == 0x6A || address == 0x6B) {
        Serial.print(" (possible LSM6DSOX)");
      }
      Serial.println();
      ++foundDevices;
    }
  }

  if (foundDevices == 0) {
    Serial.println("  No I2C devices found");
  }

  uint8_t whoAmI = 0;
  if (readRegister(kLsm6dsoxAddress, kWhoAmIRegister, whoAmI)) {
    Serial.printf("  Device 0x6A WHO_AM_I: 0x%02X", whoAmI);
    if (whoAmI == 0x6C) {
      Serial.print(" (LSM6DSOX confirmed)");
    } else {
      Serial.print(" (unexpected value)");
    }
    Serial.println();
  }
  Serial.println();
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);
  Wire.begin();
  Serial.println("Delta collar: ESP32 I2C bring-up");
  scanI2cBus();
}

void loop() {
  static unsigned long lastScanMs = 0;
  const unsigned long now = millis();

  if (now - lastScanMs >= kScanIntervalMs) {
    lastScanMs = now;
    scanI2cBus();
  }
}
