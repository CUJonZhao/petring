// Host simulation of CloudSync: pruning only removes cloud-confirmed sessions (oldest first),
// never unconfirmed or in-progress ones; uploads pick the newest unconfirmed session.
// Build/run: sh run.sh (compiles the real src/cloud_sync.cpp and src/motion_logger.cpp).
#include <cassert>
#include <cstdarg>
#include <map>
#include "cloud_sync.h"
#include <mbedtls/sha256.h>
std::map<std::string, std::string> g_files;
unsigned long g_ms = 100000;
unsigned long millis() { return g_ms; }
void yield() {}
HardwareSerial Serial;
size_t Print::printf(const char* f, ...) { va_list a; va_start(a, f); int n = vprintf(f, a); va_end(a); return n; }
void configTime(long, int, const char*, const char*, const char*) {}
int String::indexOf(char c) const { auto p = s.find(c); return p == std::string::npos ? -1 : int(p); }
int String::indexOf(char c, unsigned f) const { auto p = s.find(c, f); return p == std::string::npos ? -1 : int(p); }
int String::indexOf(const String& x) const { auto p = s.find(x.s); return p == std::string::npos ? -1 : int(p); }
int String::indexOf(const String& x, unsigned f) const { auto p = s.find(x.s, f); return p == std::string::npos ? -1 : int(p); }
String String::substring(unsigned f) const { return f >= s.size() ? String() : String(s.substr(f).c_str()); }
String String::substring(unsigned f, unsigned t) const { if (f >= s.size()) return String(); return String(s.substr(f, t - f).c_str()); }
void String::remove(unsigned i, unsigned n) { s.erase(i, n); }
#define SUM(T) StringSumHelper& operator+(const StringSumHelper& l, T r) { auto& a = const_cast<StringSumHelper&>(l); a.concat(r); return a; }
SUM(const String&) SUM(const char*) SUM(unsigned int) SUM(int)
// SHA stub: records length only; the simulation checks selection, not hashing.
void mbedtls_sha256_init(mbedtls_sha256_context*) {} void mbedtls_sha256_free(mbedtls_sha256_context*) {}
int mbedtls_sha256_starts_ret(mbedtls_sha256_context*, int) { return 0; }
int mbedtls_sha256_update_ret(mbedtls_sha256_context*, const unsigned char*, size_t) { return 0; }
int mbedtls_sha256_finish_ret(mbedtls_sha256_context*, unsigned char o[32]) { memset(o, 0xab, 32); return 0; }

static void session(const char* id, const char* ext, uint64_t startMs, size_t bytes, bool ack) {
  std::string data(bytes, '\0');
  uint8_t h[motion::kHeaderBytes];
  motion::makeHeader(h, 0, startMs);
  memcpy(&data[0], h, sizeof(h));
  g_files[std::string("/") + id + ext] = data;
  if (ack) g_files[std::string("/") + id + ".ack"] = std::string(64, 'a');
}
static bool has(const char* p) { return g_files.count(p) > 0; }

int main() {
  MotionLogger logger;
  logger.ready_ = true;
  CloudSync sync(logger);
  const size_t MB = 1000000;
  // Acked: b0000000 (no clock), a1000000, f2000000. Not acked: c3000000, d0000000 (.open).
  session("a1000000", ".bin", 1789000001000ULL, MB, true);
  session("b0000000", ".bin", 0, MB, true);
  session("c3000000", ".bin", 1789000003000ULL, MB, false);
  session("d0000000", ".open", 0, 200000, false);
  session("f2000000", ".bin", 1789000002000ULL, 600000, true);
  g_files["/e9999999.ack"] = std::string(64, 'a');  // orphan marker
  printf("free before=%u\n", unsigned(logger.freeBytes()));
  size_t removed = sync.prune(2300000);
  printf("removed=%u free after=%u\n", unsigned(removed), unsigned(logger.freeBytes()));
  // Oldest acked first: b (unknown time) then a; f (newer) kept once target is met.
  assert(!has("/b0000000.bin") && !has("/b0000000.ack"));
  assert(!has("/a1000000.bin") && !has("/a1000000.ack"));
  assert(has("/f2000000.bin") && has("/f2000000.ack"));
  assert(has("/c3000000.bin") && has("/d0000000.open"));  // never delete unconfirmed data
  assert(!has("/e9999999.ack"));
  assert(logger.freeBytes() >= 2300000);
  // Nothing more to free -> never touches unconfirmed sessions even if target unreachable.
  size_t again = sync.prune(4000000);
  assert(again == 1 && !has("/f2000000.bin") && has("/c3000000.bin") && has("/d0000000.open"));
  // Selection: newest unconfirmed first; .retry skipped; .reject counted, not selected.
  session("aa000001", ".bin", 1789000009000ULL, 40000, false);
  g_files["/aa000001.retry"] = "x";
  session("bb000002", ".bin", 1789000008000ULL, 40000, false);
  g_files["/bb000002.reject"] = "x";
  assert(sync.selectFile());
  printf("selected=%s state=%s pending=%u rejected=%u\n", sync.id_.c_str(), sync.state_.c_str(), sync.pending_, sync.rejected_);
  assert(sync.id_ == "c3000000" && sync.state_ == "complete");
  assert(sync.pending_ == 3 && sync.rejected_ == 1);
  sync.clearTransfer();
  // The active recording is never selected or pruned.
  logger.recording_ = true; logger.id_ = "c3000000";
  assert(sync.selectFile() && sync.id_ == "d0000000" && sync.state_ == "interrupted");
  sync.clearTransfer();
  g_files["/c3000000.ack"] = std::string(64, 'a');
  sync.prune(4000000);
  assert(has("/c3000000.bin"));
  // markDone writes the ack and clears retry/reject markers.
  logger.recording_ = false;
  g_files["/aa000001.retry"] = "x";
  sync.id_ = "aa000001"; sync.sha_ = String(std::string(64, 'f').c_str());
  sync.markDone();
  assert(has("/aa000001.ack") && g_files["/aa000001.ack"].size() == 64 && !has("/aa000001.retry"));
  puts("SIM PASS");
}
