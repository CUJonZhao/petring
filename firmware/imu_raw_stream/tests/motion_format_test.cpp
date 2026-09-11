#include "motion_format.h"
#include <assert.h>
#include <stdio.h>

int main(int argc, char** argv) {
  assert(argc == 2);
  using namespace motion;
  assert(crc16(reinterpret_cast<const uint8_t*>("123456789"), 9) == 0x29b1);
  uint8_t header[kHeaderBytes];
  makeHeader(header, 1234, 1788969600000ULL);
  assert(validHeader(header));
  for (size_t byte = 0; byte < sizeof(header); ++byte) {
    header[byte] ^= 1; assert(!validHeader(header)); header[byte] ^= 1;
  }

  // Generate an hour through the firmware's actual buffer/codec, without
  // pretending this is a one-hour physical battery/flash test.
  static uint8_t disk[kHeaderBytes + 72000 * kRecordBytes];
  memcpy(disk, header, kHeaderBytes);
  size_t diskSize = kHeaderBytes;
  size_t writes = 0;
  auto sink = [&](const uint8_t* bytes, size_t n) {
    assert(n <= kBatchRecords * kRecordBytes);
    assert(diskSize + n <= sizeof(disk));
    memcpy(disk + diskSize, bytes, n); diskSize += n; ++writes; return true;
  };
  Buffer buffer;
  Sample sample = {};
  sample.accel[0] = -32768; sample.accel[1] = 32767; sample.accel[2] = 8197;
  sample.gyro[0] = -100; sample.gyro[1] = 100; sample.gyro[2] = 0;
  sample.temperature = -256; sample.batteryMv = 4000;
  for (uint32_t i = 1; i <= 72000; ++i) {
    sample.elapsedMs = i * kPeriodMs;
    sample.activity = i % 256; sample.active = (i > 36000);
    assert(buffer.add(sample));
    if (buffer.count() == kBatchRecords) assert(buffer.flush(sink));
  }
  assert(buffer.flush(sink));
  assert(writes == 3600);
  assert(diskSize == 1728032);
  assert(diskSize + kReserveBytes < 4 * 1024 * 1024);
  Sample decoded = {};
  for (size_t i = 0; i < 72000; ++i) {
    assert(decode(disk+kHeaderBytes+i*kRecordBytes, decoded));
    assert(decoded.elapsedMs == (i+1)*50);
    assert(decoded.accel[0] == -32768 && decoded.accel[1] == 32767);
    assert(decoded.temperature == -256);
    assert(decoded.active == (i >= 36000));
  }
  uint8_t encoded[kRecordBytes]; encode(encoded, sample);
  for (size_t byte = 0; byte < sizeof(encoded); ++byte) {
    encoded[byte] ^= 1; assert(!decode(encoded, decoded)); encoded[byte] ^= 1;
  }

  // A stop flushes a partial batch; a failed sink retains it for the caller
  // to terminate, never reporting it as saved or accepting overflowing data.
  for (unsigned i = 0; i < 7; ++i) assert(buffer.add(sample));
  assert(!buffer.flush([](const uint8_t*, size_t) { return false; }));
  assert(buffer.count() == 7);
  size_t partialBytes = 0;
  assert(buffer.flush([&](const uint8_t*, size_t n) { partialBytes = n; return true; }));
  assert(partialBytes == 7 * kRecordBytes && buffer.count() == 0);
  for (size_t i = 0; i < kBatchRecords; ++i) assert(buffer.add(sample));
  assert(!buffer.add(sample));
  buffer.reset(); assert(buffer.count() == 0);

  FILE* out = fopen(argv[1], "wb"); assert(out);
  assert(fwrite(disk, 1, diskSize, out) == diskSize);
  fclose(out);
  puts("PASS: 72,000 samples, 3,600 batches, signed axes, CRC damage, partial stop, failed sink, overflow");
}
