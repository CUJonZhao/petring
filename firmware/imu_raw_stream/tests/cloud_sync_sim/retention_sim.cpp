// Time-driven retention checks: drive CloudSync::away()/home() second by second
// with the real MotionLogger, and check what survives on the 4 MiB partition.
//  - A long away outing keeps its newest ~1.7 h without holes; eviction removes
//    one bounded segment at a time, never the whole walk.
//  - At home, data the website has not confirmed is never deleted, even while
//    the dog keeps moving indoors and the site is unreachable.
//  - Hand-started sessions are split by size only once carried away; a manual
//    start deletes unsent data only once the board is confirmed away.
#include <cassert>
#include <climits>
#include <map>
#include <string>

#include "cloud_sync.h"

extern std::map<std::string, std::string> g_files;
extern unsigned long g_ms;

namespace {
const size_t kSegmentMax = 512 * 1024;   // kSegmentMaxBytes in cloud_sync.cpp
const size_t kPerSecond = 20 * motion::kRecordBytes;

struct Rig {
  MotionLogger logger;
  CloudSync sync;
  Rig() : sync(logger) {
    logger.ready_ = true;
    sync.enabled_ = true;
  }
  // One second of 20 Hz samples, then one sync tick. `home` = on home Wi-Fi.
  void second(bool home, bool active) {
    for (int i = 0; i < 20; ++i) {
      g_ms += motion::kPeriodMs;
      motion::Sample s = {};
      s.active = active;
      logger.sample(s, g_ms);
    }
    logger.tick(g_ms);
    sync.tick(home, true, active, 4.0f);
  }
};

bool ends(const std::string& s, const char* ext) {
  const size_t n = strlen(ext);
  return s.size() >= n && s.compare(s.size() - n, n, ext) == 0;
}

struct Kept {
  size_t records = 0, largestClosed = 0;
  unsigned files = 0, full = 0;
  uint32_t oldestUptime = UINT_MAX;
};
// Data files on the device; names starting with `skip` (pre-loaded) are ignored.
Kept kept(const char* skip = "/-") {
  Kept k;
  for (const auto& kv : g_files) {
    const std::string& name = kv.first;
    if (!ends(name, ".bin") && !ends(name, ".open") && !ends(name, ".full")) continue;
    if (name.compare(0, strlen(skip), skip) == 0) continue;
    const std::string& data = kv.second;
    ++k.files;
    if (ends(name, ".full")) ++k.full;
    if (data.size() < motion::kHeaderBytes) continue;
    k.records += (data.size() - motion::kHeaderBytes) / motion::kRecordBytes;
    const uint32_t uptime = motion::get32(reinterpret_cast<const uint8_t*>(data.data()) + 12);
    if (uptime < k.oldestUptime) k.oldestUptime = uptime;
    if (!ends(name, ".open") && data.size() > k.largestClosed) k.largestClosed = data.size();
  }
  return k;
}

void stored(const char* id, uint64_t startMs, size_t bytes) {
  std::string data(bytes, '\0');
  uint8_t h[motion::kHeaderBytes];
  motion::makeHeader(h, 0, startMs, 'w');
  memcpy(&data[0], h, sizeof(h));
  g_files[std::string("/") + id + ".bin"] = data;
}
bool present(const char* id) { return g_files.count(std::string("/") + id + ".bin") > 0; }

void awayOuting() {
  g_files.clear();
  g_ms = 100000;
  Rig r;
  unsigned firstEviction = 0;
  size_t leastKept = SIZE_MAX;
  for (unsigned s = 1; s <= 200 * 60; ++s) {
    r.second(false, true);
    if (s == 60) assert(r.logger.recording() && r.logger.trigger_ == 'w');
    const Kept k = kept();
    // Segments are bounded (one 30 s maintenance period of overshoot at most).
    assert(k.largestClosed <= kSegmentMax + 31 * kPerSecond);
    if (!r.sync.evicted_) continue;
    if (!firstEviction) firstEviction = s;
    const size_t keptSeconds = k.records / 20;
    if (keptSeconds < leastKept) leastKept = keptSeconds;
    // What remains is the newest data, contiguous up to now.
    const size_t spanSeconds = (g_ms - k.oldestUptime) / 1000;
    assert(spanSeconds >= keptSeconds && spanSeconds - keptSeconds <= 5);
  }
  printf("away 200 min: first eviction at %u min, least kept %zu min, %u segments on device\n",
         firstEviction / 60, leastKept / 60, kept().files);
  assert(firstEviction && leastKept >= 100 * 60);
  assert(r.logger.recording() && r.sync.error_.isEmpty());
}

void homeFullOfUnsent() {
  // A 3.5 MiB outing not yet on the website; site unreachable; dog moving indoors.
  g_files.clear();
  g_ms = 200000;
  stored("0a0a0a0a", 1789000001000ULL, 3500 * 1024);
  Rig r;
  for (unsigned s = 1; s <= 20 * 60; ++s) {
    r.second(true, true);
    assert(present("0a0a0a0a"));
    assert(!r.logger.recording());  // too little room to start at home
  }
  assert(r.sync.evicted_ == 0);
  puts("home, 3.5 MiB unsent: indoor session deferred, outing kept");
}

void homeIndoorSessionEndsFirst() {
  // Enough room for an indoor session, but not for it to run forever.
  g_files.clear();
  g_ms = 300000;
  stored("0b0b0b0b", 1789000001000ULL, 2560 * 1024);
  Rig r;
  bool started = false;
  for (unsigned s = 1; s <= 60 * 60; ++s) {
    r.second(true, true);
    started = started || r.logger.recording();
    assert(present("0b0b0b0b"));
  }
  const Kept k = kept();
  assert(started && k.full == 1 && !r.logger.recording() && r.sync.evicted_ == 0);
  // Once the website confirms the outing, its space is usable again.
  g_files["/0b0b0b0b.ack"] = std::string(64, 'a');
  for (unsigned s = 1; s <= 5 * 60 && !r.logger.recording(); ++s) r.second(true, true);
  assert(r.logger.recording() && !present("0b0b0b0b"));
  puts("home, 2.5 MiB unsent: indoor session ended as storage_full, outing kept until confirmed");
}

void manualSessions() {
  g_files.clear();
  g_ms = 400000;
  stored("0c0c0c0c", 1789000001000ULL, 3500 * 1024);
  Rig r;
  for (unsigned s = 0; s < 20; ++s) r.second(true, false);
  assert(r.sync.atHome_);
  assert(!r.sync.startManual(0) && r.logger.error_ == "storage_full");
  assert(present("0c0c0c0c") && r.sync.evicted_ == 0);
  // With room, a hand-started session at home stays one file past the segment size.
  g_files.clear();
  assert(r.sync.startManual(0));
  for (unsigned s = 0; s < 30 * 60; ++s) r.second(true, false);
  assert(r.logger.recording() && r.logger.bytes() > kSegmentMax && kept().files == 1);
  assert(r.logger.stop());

  // Away with storage full of unsent sessions and automatic recording held.
  g_files.clear();
  g_ms = 500000;
  stored("1d000001", 1789000001000ULL, 1200 * 1024);
  stored("1d000002", 1789000002000ULL, 1200 * 1024);
  stored("1d000003", 1789000003000ULL, 1400 * 1024);
  Rig a;
  a.sync.holdUntilHome_ = true;
  a.second(false, false);
  assert(!a.sync.startManual(0));  // not yet confirmed away: nothing deleted
  assert(present("1d000001") && a.sync.evicted_ == 0);
  for (unsigned s = 0; s < 15; ++s) a.second(false, false);
  assert(a.sync.startManual(0));
  assert(!present("1d000001") && present("1d000002") && present("1d000003"));
  assert(a.sync.evicted_ == 1 && a.logger.trigger_ == 'u');
  // Carried away, the hand-started session is segmented and ages out oldest first.
  for (unsigned s = 0; s < 60 * 60; ++s) {
    a.second(false, true);
    assert(kept("/1d").largestClosed <= kSegmentMax + 31 * kPerSecond);
    assert(present("1d000003") || !present("1d000002"));  // oldest goes first
  }
  assert(a.logger.recording() && a.logger.trigger_ == 'u' && !present("1d000002"));
  puts("manual: refused at home when full, one file at home, segmented and evicted oldest-first away");
}
}  // namespace

void retention_scenarios() {
  awayOuting();
  homeFullOfUnsent();
  homeIndoorSessionEndsFirst();
  manualSessions();
}
