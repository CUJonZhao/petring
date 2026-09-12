#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

// Version 1 is little endian, with no compiler-dependent struct serialization.
namespace motion {
constexpr size_t kHeaderBytes = 32;
constexpr size_t kRecordBytes = 24;
constexpr uint32_t kPeriodMs = 50;
constexpr size_t kBatchRecords = 20;
constexpr size_t kReserveBytes = 128 * 1024;
constexpr float kAccelScale = 0.000122f;
constexpr float kGyroScale = 0.0175f;

inline void put16(uint8_t* p, uint16_t n) { p[0] = n; p[1] = n >> 8; }
inline void put32(uint8_t* p, uint32_t n) {
  for (unsigned i = 0; i < 4; ++i) p[i] = n >> (8 * i);
}
inline uint16_t get16(const uint8_t* p) { return p[0] | (uint16_t(p[1]) << 8); }
inline uint32_t get32(const uint8_t* p) {
  return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) |
         (uint32_t(p[3]) << 24);
}
inline int16_t signed16(const uint8_t* p) {
  const uint16_t n = get16(p);
  return n < 32768 ? int16_t(n) : int16_t(int32_t(n) - 65536);
}
// CRC-16/CCITT-FALSE. Check vector "123456789" => 0x29b1.
inline uint16_t crc16(const uint8_t* p, size_t size) {
  uint16_t crc = 0xffff;
  while (size--) {
    crc ^= uint16_t(*p++) << 8;
    for (unsigned bit = 0; bit < 8; ++bit)
      crc = (crc & 0x8000) ? uint16_t((crc << 1) ^ 0x1021) : uint16_t(crc << 1);
  }
  return crc;
}

// trigger: 0 unknown, 'w' left home Wi-Fi, 'm' sustained motion, 'u' user.
inline void makeHeader(uint8_t* p, uint32_t uptime, uint64_t unixMs, uint8_t trigger = 0) {
  memset(p, 0, kHeaderBytes);
  memcpy(p, "DLOG", 4);
  put16(p + 4, 1);
  put16(p + 6, kRecordBytes);
  put32(p + 8, kPeriodMs);
  put32(p + 12, uptime);
  put32(p + 16, uint32_t(unixMs));
  put32(p + 20, uint32_t(unixMs >> 32));
  p[24] = trigger;
  // Bytes 25..29 reserved; version 1 fixes the LSM6DSOX scales above.
  put16(p + 30, crc16(p, 30));
}
inline bool validHeader(const uint8_t* p) {
  return memcmp(p, "DLOG", 4) == 0 && get16(p + 4) == 1 &&
         get16(p + 6) == kRecordBytes && get32(p + 8) == kPeriodMs &&
         get16(p + 30) == crc16(p, 30);
}

struct Sample {
  uint32_t elapsedMs;
  int16_t accel[3];
  int16_t gyro[3];
  int16_t temperature;
  uint16_t batteryMv;
  uint8_t activity;  // Rounded score * 255; raw axes retain sensor precision.
  bool active;
};
inline void encode(uint8_t* p, const Sample& s) {
  put32(p, s.elapsedMs);
  for (unsigned i = 0; i < 3; ++i) {
    put16(p + 4 + i * 2, uint16_t(s.accel[i]));
    put16(p + 10 + i * 2, uint16_t(s.gyro[i]));
  }
  put16(p + 16, uint16_t(s.temperature));
  put16(p + 18, s.batteryMv);
  p[20] = s.activity;
  p[21] = s.active ? 1 : 0;
  put16(p + 22, crc16(p, 22));
}
inline bool decode(const uint8_t* p, Sample& s) {
  if (get16(p + 22) != crc16(p, 22) || (p[21] & ~1)) return false;
  s.elapsedMs = get32(p);
  for (unsigned i = 0; i < 3; ++i) {
    s.accel[i] = signed16(p + 4 + i * 2);
    s.gyro[i] = signed16(p + 10 + i * 2);
  }
  s.temperature = signed16(p + 16);
  s.batteryMv = get16(p + 18);
  s.activity = p[20];
  s.active = p[21] & 1;
  return true;
}

// Sink returns false for a full disk or a short write. Never discard an
// unsuccessful batch or silently append subsequent records after it.
class Buffer {
 public:
  bool add(const Sample& sample) {
    if (count_ == kBatchRecords) return false;
    encode(data_ + count_++ * kRecordBytes, sample);
    return true;
  }
  template <typename Sink> bool flush(Sink sink) {
    if (!count_) return true;
    if (!sink(data_, count_ * kRecordBytes)) return false;
    count_ = 0;
    return true;
  }
  size_t count() const { return count_; }
  void reset() { count_ = 0; }
 private:
  uint8_t data_[kBatchRecords * kRecordBytes] = {};
  size_t count_ = 0;
};
}  // namespace motion
