#include "cloud_sync.h"

#include <HTTPClient.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <mbedtls/sha256.h>
#include <sys/time.h>
#include <time.h>

#include <algorithm>

#include "cloud_ca.h"

namespace {
constexpr uint32_t kBootGraceMs = 30000;      // let saved home Wi-Fi connect after power-on
constexpr uint32_t kLeaveDebounceMs = 10000;  // brief Wi-Fi drops at home start nothing
constexpr uint32_t kHomeStableMs = 15000;     // stable home link closes the away session
constexpr uint32_t kStartRetryMs = 30000;
constexpr uint32_t kRetryMs = 30000;
constexpr uint32_t kAuthRetryMs = 300000;
constexpr uint32_t kScanMs = 60000;
constexpr uint32_t kHeartbeatMs = 60000;
constexpr uint32_t kPruneCheckMs = 30000;
constexpr size_t kChunkBytes = 16384;
// About one hour at 20 Hz (1.73 MB) after the recorder's 128 KiB reserve and
// its 15% filesystem allowance. Only cloud-confirmed sessions are removed.
constexpr size_t kPruneTargetBytes = 2300000;
// During a long outing, free more space only when nearly full.
constexpr size_t kPruneLowWaterBytes = 512 * 1024;
constexpr size_t kPruneTopUpBytes = 1024 * 1024;
const char* const kDataExtensions[] = {".bin", ".open", ".full", ".sensor", ".error"};

bool due(uint32_t now, uint32_t at) { return !at || int32_t(now - at) >= 0; }
uint32_t after(uint32_t now, uint32_t delay) {
  const uint32_t at = now + delay;
  return at ? at : 1;
}
bool dataExtension(const String& ext) {
  for (const char* known : kDataExtensions)
    if (ext == known) return true;
  return false;
}
uint64_t headerStart(File& f) {
  uint8_t h[motion::kHeaderBytes];
  if (!f.seek(0) || f.read(h, sizeof(h)) != sizeof(h) || !motion::validHeader(h)) return 0;
  return uint64_t(motion::get32(h + 16)) | (uint64_t(motion::get32(h + 20)) << 32);
}
void removeIfPresent(fs::FS& fs, const String& path) {
  if (fs.exists(path)) fs.remove(path);
}
}  // namespace

void CloudSync::begin() {
  client_.setCACert(kCloudRootCA);
  client_.setHandshakeTimeout(12);
  Preferences p;
  if (p.begin("delta-cloud", true)) {
    url_ = p.getString("url", "");
    bypass_ = p.getString("bypass", "");
    token_ = p.getString("token", "");
    p.end();
  }
  enabled_ = url_.startsWith("https://") && bypass_.length() && token_.length() == 64;
  mode_ = enabled_ ? "starting" : "unconfigured";
  // SNTP runs once the station has an IP; uploads wait for a real clock.
  configTime(0, 0, "time.cloudflare.com", "pool.ntp.org", "time.google.com");
}

uint64_t CloudSync::unixMs() const {
  struct timeval t;
  gettimeofday(&t, nullptr);
  return t.tv_sec > 1700000000 ? uint64_t(t.tv_sec) * 1000 + t.tv_usec / 1000 : 0;
}

bool CloudSync::configure(const String& line) {
  const int a = line.indexOf('|');
  const int b = a < 0 ? -1 : line.indexOf('|', a + 1);
  if (b < 0 || line.length() > 2048) return false;
  const String url = line.substring(0, a), bypass = line.substring(a + 1, b),
               token = line.substring(b + 1);
  // One HTTPS origin only; credentials arrive over local USB and are never echoed.
  if (!url.startsWith("https://") || url.length() < 12 || bypass.length() < 16 ||
      bypass.length() > 512 || token.length() != 64)
    return false;
  for (unsigned i = 8; i < url.length(); ++i) {
    const char c = url[i];
    if (!isalnum(static_cast<unsigned char>(c)) && c != '.' && c != '-' && c != ':') return false;
  }
  for (unsigned i = 0; i < bypass.length(); ++i)
    if (bypass[i] <= ' ' || bypass[i] > '~') return false;
  for (unsigned i = 0; i < token.length(); ++i)
    if (token[i] <= ' ' || token[i] > '~') return false;
  Preferences p;
  if (!p.begin("delta-cloud", false)) return false;
  const bool ok = p.putString("url", url) > 0 && p.putString("bypass", bypass) > 0 &&
                  p.putString("token", token) > 0;
  p.end();
  if (!ok) return false;
  closeConnection();
  url_ = url;
  bypass_ = bypass;
  token_ = token;
  enabled_ = true;
  mode_ = "starting";
  error_ = "";
  atHome_ = false;
  homeSince_ = awaySince_ = lastScan_ = lastHeartbeat_ = retryAt_ = startRetryAt_ = 0;
  clearTransfer();
  return true;
}

String CloudSync::statusJson() const {
  char last[24];
  snprintf(last, sizeof(last), "%llu", (unsigned long long)lastSyncUnixMs_);
  String s = "{\"configured\":";
  s += enabled_ ? "true" : "false";
  s += ",\"mode\":\"";
  s += mode_;
  s += "\",\"error\":\"";
  s += error_;
  s += "\",\"site\":\"";
  s += url_;
  s += "\",\"pending\":";
  s += pending_;
  s += ",\"synced\":";
  s += synced_;
  s += ",\"rejected\":";
  s += rejected_;
  s += ",\"uploaded_this_boot\":";
  s += uploaded_;
  s += ",\"pruned_this_boot\":";
  s += pruned_;
  s += ",\"upload_id\":\"";
  s += id_;
  s += "\",\"offset\":";
  s += unsigned(offset_);
  s += ",\"bytes\":";
  s += unsigned(size_);
  s += ",\"clock_ready\":";
  s += unixMs() ? "true" : "false";
  s += ",\"last_sync_unix_ms\":";
  s += last;
  s += "}";
  return s;
}

void CloudSync::tick(bool connected, bool imuReady, float voltage) {
  if (!enabled_ || !logger_.ready()) return;
  const uint32_t now = millis();
  if (connected) home(now, voltage);
  else away(now, imuReady);
  wasRecording_ = logger_.recording();
}

void CloudSync::away(uint32_t now, bool imuReady) {
  homeSince_ = 0;
  atHome_ = false;
  closeConnection();  // away from home the socket is dead anyway; free the TLS memory
  if (path_.length()) clearTransfer();  // the site keeps received chunks; resume at home
  if (!awaySince_) awaySince_ = now ? now : 1;
  const bool recording = logger_.recording();
  // A manual stop (phone page or serial S) is respected until the next return home.
  if (wasRecording_ && !recording && logger_.lastStop_ == "complete") holdUntilHome_ = true;
  if (recording) {
    mode_ = "recording";
    if (now - lastPruneCheck_ >= kPruneCheckMs) {
      lastPruneCheck_ = now;
      if (logger_.freeBytesCached() < kPruneLowWaterBytes) prune(kPruneTopUpBytes);
    }
    return;
  }
  if (holdUntilHome_) {
    mode_ = "held";
    return;
  }
  if (now < kBootGraceMs || now - awaySince_ < kLeaveDebounceMs) {
    mode_ = "away_pending";
    return;
  }
  if (!imuReady) {
    mode_ = "error";
    error_ = "imu_unavailable";
    return;
  }
  if (!due(now, startRetryAt_)) return;
  prune(kPruneTargetBytes);
  if (logger_.start(unixMs())) {
    mode_ = "recording";
    error_ = "";
    startRetryAt_ = 0;
    lastPruneCheck_ = now;
  } else {
    mode_ = "error";
    error_ = "record_start_failed_" + logger_.error_;
    startRetryAt_ = after(now, kStartRetryMs);
  }
}

void CloudSync::home(uint32_t now, float voltage) {
  awaySince_ = 0;
  if (!homeSince_) homeSince_ = now ? now : 1;
  if (now - homeSince_ < kHomeStableMs) return;
  if (!atHome_) {
    atHome_ = true;
    holdUntilHome_ = false;
    lastScan_ = 0;
    retryAt_ = 0;
    if (logger_.recording() && !logger_.stop()) error_ = "record_finalize_failed";
  }
  // A session started by hand at home stays under manual control; never upload while sampling.
  if (logger_.recording()) {
    mode_ = "home_recording";
    return;
  }
  if (!unixMs()) {
    mode_ = "waiting_clock";
    return;
  }
  if (!due(now, retryAt_)) return;
  if ((!lastHeartbeat_ || now - lastHeartbeat_ >= kHeartbeatMs) && !heartbeat(now, voltage)) return;
  if (path_.isEmpty()) {
    if (lastScan_ && now - lastScan_ < kScanMs) return;
    if (!rejectsCleared_) {  // one fresh attempt per boot for sessions the site refused
      clearMarkers(".reject");
      rejectsCleared_ = true;
    }
    if (!selectFile()) {
      clearMarkers(".retry");  // sessions that failed get another turn on the next scan
      lastScan_ = now;
      closeConnection();  // nothing to send; do not hold TLS memory while idle
      prune(kPruneTargetBytes);
      if (error_.isEmpty()) mode_ = "home";
      return;
    }
  }
  upload(now);
}

bool CloudSync::heartbeat(uint32_t now, float voltage) {
  String body = "{\"mode\":\"";
  body += error_.length() ? "error" : (path_.length() ? "syncing" : "home");
  body += "\",\"battery\":";
  body += String(voltage, 3);
  body += ",\"pending\":";
  body += pending_;
  if (error_.length()) {
    body += ",\"error\":\"";
    body += error_;
    body += "\"";
  }
  body += "}";
  const Result r = request("heartbeat", "", reinterpret_cast<const uint8_t*>(body.c_str()),
                           body.length(), true);
  if (r == Result::ok) {
    lastHeartbeat_ = now;
    return true;
  }
  mode_ = "error";
  retryAt_ = after(now, r == Result::auth ? kAuthRetryMs : kRetryMs);
  return false;
}

void CloudSync::upload(uint32_t now) {
  mode_ = "syncing";
  Result r = Result::ok;
  if (!knownOffset_) {
    r = request("status", query_);
    if (r == Result::ok) {
      if (confirmed()) {
        markDone();
        return;
      }
      const int pos = body_.indexOf("\"offset\":");
      if (pos < 0) {
        error_ = "bad_status_reply";
        r = Result::retry;
      } else {
        offset_ = strtoul(body_.c_str() + pos + 9, nullptr, 10);
        if (offset_ > size_ || (offset_ < size_ && offset_ % kChunkBytes)) {
          error_ = "bad_resume_offset";
          r = Result::retry;
        } else {
          knownOffset_ = true;
          if (offset_) Serial.printf("STATUS,cloud_resume,id=%s,offset=%u\n", id_.c_str(), unsigned(offset_));
        }
      }
    }
  } else if (offset_ < size_) {
    const size_t n = std::min(kChunkBytes, size_ - offset_);
    uint8_t* chunk = static_cast<uint8_t*>(malloc(n));
    if (!chunk) {
      error_ = "upload_memory_low";
      r = Result::retry;
    } else {
      // Keep a file descriptor only during the disk read, never across HTTPS.
      // ESP32/newlib fseek on a retained stream failed after a TLS request in
      // the physical bench. Reopen each immutable chunk at its saved offset.
      File source = logger_.fs_.open(path_, "r");
      const bool seekOk = source && (!offset_ || source.seek(offset_));
      const size_t got = seekOk ? source.read(chunk, n) : 0;
      if (source) source.close();
      if (seekOk && got == n)
        r = request("chunk", query_ + "&offset=" + String(unsigned(offset_)), chunk, n, true);
      else {
        Serial.printf("STATUS,cloud_read_failed,id=%s,seek=%d,offset=%u,wanted=%u,got=%u,file_size=%u\n",
                      id_.c_str(), seekOk, unsigned(offset_), unsigned(n), unsigned(got), unsigned(size_));
        error_ = "file_read_failed";
        r = Result::retry;
      }
      free(chunk);
      if (r == Result::ok) offset_ += n;
    }
  } else {
    r = request("complete", query_ + "&state=" + state_, nullptr, 0, true);
    if (r == Result::ok) {
      if (confirmed()) {
        markDone();
        return;
      }
      error_ = "complete_unconfirmed";
      r = Result::retry;
    }
  }
  if (r != Result::ok) fail(r, now);
}

void CloudSync::fail(Result result, uint32_t now) {
  if (result == Result::reject) {
    markFile(".reject");  // kept locally; retried once after the next reboot
    ++rejected_;
    if (pending_) --pending_;
    Serial.printf("STATUS,cloud_rejected,id=%s,error=%s\n", id_.c_str(), error_.c_str());
  } else if (result == Result::retry) {
    markFile(".retry");  // let other sessions go first
  }
  closeConnection();
  clearTransfer();
  mode_ = "error";
  retryAt_ = after(now, result == Result::auth ? kAuthRetryMs : kRetryMs);
}

int CloudSync::send(const char* action, const String& query, const uint8_t* bytes, size_t size,
                    bool post, String& location) {
  HTTPClient http;
  // Keep the TLS session for the next chunk: the handshake dominated upload time.
  http.setReuse(true);
  http.setConnectTimeout(8000);
  http.setTimeout(15000);
  http.setFollowRedirects(HTTPC_DISABLE_FOLLOW_REDIRECTS);
  setRadioAwake(true);
  if (!http.begin(client_, url_ + "/api/device/" + action + query)) return 0;
  socketOpen_ = true;  // even a failed attempt leaves a socket worth closing
  http.addHeader("OAI-Sites-Authorization", "Bearer " + bypass_);
  http.addHeader("Authorization", "Bearer " + token_);
  http.addHeader("Content-Type",
                 strcmp(action, "heartbeat") == 0 ? "application/json" : "application/octet-stream");
  // HTTPClient omits Content-Length for an empty body; some front ends reject such POSTs.
  if (post && !size) http.addHeader("Content-Length", "0");
  // Redirects are never followed with credentials; log where the host wanted to send us.
  const char* collect[] = {"Location"};
  http.collectHeaders(collect, 1);
  const int code = post ? http.POST(const_cast<uint8_t*>(bytes), size) : http.GET();
  body_ = code > 0 ? http.getString() : "";
  location = code >= 300 && code < 400 ? http.header("Location") : String();
  http.end();  // leaves the socket open for reuse when the site allows it
  return code;
}

void CloudSync::closeConnection() {
  setRadioAwake(false);
  if (!socketOpen_) return;
  client_.stop();
  socketOpen_ = false;
}

void CloudSync::setRadioAwake(bool awake) {
  if (radioAwake_ == awake) return;
  // Station modem sleep parks the radio between beacons, so every round trip
  // waits for the next wake-up: the board needed about 4.2 s per request where
  // the same site answered a laptop in 0.9 s. Stay awake only while syncing at
  // home; recording away keeps the default power saving.
  WiFi.setSleep(!awake);
  radioAwake_ = awake;
}

CloudSync::Result CloudSync::request(const char* action, const String& query,
                                     const uint8_t* bytes, size_t size, bool post) {
  String location;
  int code = 0;
  for (int attempt = 0; attempt < 2; ++attempt) {
    const bool reused = client_.connected();
    code = send(action, query, bytes, size, post, location);
    if (code > 0) break;
    // A kept-open socket may have been closed by the site while idle: drop it and
    // try once more with a fresh handshake before reporting a failure.
    closeConnection();
    if (!reused) break;
  }
  if (code == 200) {
    error_ = "";
    return Result::ok;
  }
  if (!code) {
    error_ = "https_begin_failed";
    return Result::retry;
  }
  error_ = "http_" + String(code);
  Serial.printf("STATUS,cloud_http,action=%s,code=%d,body=%.96s\n", action, code, body_.c_str());
  if (location.length()) Serial.printf("STATUS,cloud_redirect,to=%.120s\n", location.c_str());
  if (code == 401 || code == 403 || (code >= 300 && code < 400)) return Result::auth;
  if (code == 400 || code == 413 || code == 422) return Result::reject;
  return Result::retry;
}

bool CloudSync::confirmed() const {
  return body_.indexOf("\"complete\":true") >= 0 && body_.indexOf(sha_) >= 0;
}

std::vector<CloudSync::Entry> CloudSync::scan() {
  std::vector<Entry> entries;
  File root = logger_.fs_.open("/");
  if (!root) return entries;
  for (File f = root.openNextFile(); f; f = root.openNextFile()) {
    String name = f.name();
    if (name.startsWith("/")) name.remove(0, 1);
    const String id = name.substring(0, 8), ext = name.substring(8);
    if (!f.isDirectory() && name.length() > 9 && name[8] == '.' && logger_.validId(id)) {
      size_t i = 0;
      while (i < entries.size() && entries[i].id != id) ++i;
      if (i == entries.size()) {
        entries.push_back(Entry());
        entries.back().id = id;
      }
      Entry& e = entries[i];
      if (ext == ".ack") e.ack = f.size() == 64;
      else if (ext == ".retry") e.retry = true;
      else if (ext == ".reject") e.reject = true;
      else if (dataExtension(ext)) {
        e.path = "/" + name;
        e.size = f.size();
        e.startMs = headerStart(f);
      }
    }
    f.close();
    yield();
  }
  root.close();
  return entries;
}

bool CloudSync::selectFile() {
  const std::vector<Entry> entries = scan();
  const String current = logger_.recording() ? logger_.id_ : String();
  pending_ = synced_ = rejected_ = 0;
  const Entry* best = nullptr;
  for (const Entry& e : entries) {
    if (e.path.isEmpty() || e.id == current || e.size < motion::kHeaderBytes) continue;
    if (e.ack) {
      ++synced_;
    } else if (e.reject) {
      ++rejected_;
    } else {
      ++pending_;
      // Newest first, so the walk that just ended appears on the site soonest.
      if (!e.retry && (!best || e.startMs > best->startMs)) best = &e;
    }
  }
  if (!best) return false;
  path_ = best->path;
  id_ = best->id;
  size_ = best->size;
  state_ = logger_.stateFor(path_);
  if (!hashFile()) {
    error_ = "file_read_failed";
    markFile(".retry");
    clearTransfer();
    return false;
  }
  query_ = "?id=" + id_ + "&sha=" + sha_ + "&size=" + String(unsigned(size_));
  offset_ = 0;
  knownOffset_ = false;
  Serial.printf("STATUS,cloud_upload,id=%s,state=%s,bytes=%u\n", id_.c_str(), state_.c_str(),
                unsigned(size_));
  return true;
}

bool CloudSync::hashFile() {
  File f = logger_.fs_.open(path_, "r");
  if (!f) return false;
  uint8_t* buf = static_cast<uint8_t*>(malloc(4096));
  if (!buf) {
    f.close();
    return false;
  }
  mbedtls_sha256_context ctx;
  mbedtls_sha256_init(&ctx);
  mbedtls_sha256_starts_ret(&ctx, 0);
  size_t total = 0;
  while (total < size_) {
    const size_t n = f.read(buf, std::min(size_t(4096), size_ - total));
    if (!n) break;
    mbedtls_sha256_update_ret(&ctx, buf, n);
    total += n;
    yield();
  }
  uint8_t hash[32];
  mbedtls_sha256_finish_ret(&ctx, hash);
  mbedtls_sha256_free(&ctx);
  free(buf);
  f.close();
  if (total != size_) return false;
  char hex[65];
  for (int i = 0; i < 32; ++i) snprintf(hex + i * 2, 3, "%02x", hash[i]);
  sha_ = hex;
  return true;
}

size_t CloudSync::prune(size_t targetFree) {
  if (logger_.freeBytes() >= targetFree) return 0;
  const std::vector<Entry> entries = scan();
  const String current = logger_.recording() ? logger_.id_ : String();
  std::vector<const Entry*> candidates;
  for (const Entry& e : entries) {
    if (e.path.isEmpty()) {  // markers whose session is already gone
      removeIfPresent(logger_.fs_, "/" + e.id + ".ack");
      removeIfPresent(logger_.fs_, "/" + e.id + ".retry");
      removeIfPresent(logger_.fs_, "/" + e.id + ".reject");
    } else if (e.ack && e.id != current) {
      candidates.push_back(&e);
    }
  }
  // Oldest first; sessions without a calendar start time count as oldest.
  std::stable_sort(candidates.begin(), candidates.end(),
                   [](const Entry* a, const Entry* b) { return a->startMs < b->startMs; });
  size_t removed = 0;
  for (const Entry* e : candidates) {
    if (logger_.freeBytes() >= targetFree) break;
    if (!logger_.fs_.remove(e->path)) {
      error_ = "prune_failed";
      break;
    }
    removeIfPresent(logger_.fs_, "/" + e->id + ".ack");
    removeIfPresent(logger_.fs_, "/" + e->id + ".retry");
    ++removed;
    ++pruned_;
    if (synced_) --synced_;
    Serial.printf("STATUS,cloud_pruned,id=%s,bytes=%u\n", e->id.c_str(), unsigned(e->size));
  }
  return removed;
}

void CloudSync::clearMarkers(const char* ext) {
  const bool retry = strcmp(ext, ".retry") == 0;
  for (const Entry& e : scan())
    if (retry ? e.retry : e.reject) logger_.fs_.remove("/" + e.id + ext);
}

void CloudSync::markFile(const char* ext) {
  if (id_.isEmpty()) return;
  File f = logger_.fs_.open("/" + id_ + ext, "w");
  if (f) {
    f.print(sha_);
    f.close();
  }
}

void CloudSync::markDone() {
  // Written only after the site confirmed this exact SHA-256. The local copy is
  // kept until its space is needed (see prune()).
  File ack = logger_.fs_.open("/" + id_ + ".ack", "w");
  const bool ok = ack && ack.print(sha_) == sha_.length();
  if (ack) ack.close();
  if (ok) {
    removeIfPresent(logger_.fs_, "/" + id_ + ".retry");
    removeIfPresent(logger_.fs_, "/" + id_ + ".reject");
    ++uploaded_;
    ++synced_;
    if (pending_) --pending_;
    lastSyncUnixMs_ = unixMs();
    Serial.printf("STATUS,cloud_synced,id=%s,bytes=%u\n", id_.c_str(), unsigned(size_));
  } else {
    error_ = "ack_write_failed";
  }
  clearTransfer();
}

void CloudSync::clearTransfer() {
  path_ = "";
  id_ = "";
  sha_ = "";
  query_ = "";
  state_ = "";
  size_ = offset_ = 0;
  knownOffset_ = false;
}
