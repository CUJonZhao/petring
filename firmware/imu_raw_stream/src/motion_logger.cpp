#include "motion_logger.h"

#include <esp_partition.h>
#include <esp_system.h>
#include <math.h>
#include <unistd.h>

namespace {
const char* const kExtensions[] = {".open", ".bin", ".full", ".error", ".sensor"};
void json(WebServer& s, int code, const String& body) {
  s.sendHeader("Cache-Control", "no-store");
  s.send(code, "application/json", body);
}
void fail(WebServer& s, int code, const char* message) {
  json(s, code, String("{\"error\":\"") + message + "\"}");
}
bool headerFrom(File& f, uint8_t* header) {
  return f.seek(0) && f.read(header, motion::kHeaderBytes) == motion::kHeaderBytes &&
         motion::validHeader(header);
}
bool syncFile(FILE* file) {
  // Arduino File::flush() discards these return codes. A sample is counted as
  // saved only after both the stdio buffer and LittleFS sync report success.
  return fflush(file) == 0 && fsync(fileno(file)) == 0;
}
}  // namespace

bool mountLogFilesystem(fs::LittleFSFS& fs, const char* label, const char* base) {
  if (fs.begin(false, base, 6, label)) return true;
  const esp_partition_t* partition = esp_partition_find_first(
      ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_DATA_SPIFFS, label);
  if (!partition) return false;
  uint8_t block[1024];
  for (size_t offset = 0; offset < partition->size; offset += sizeof(block)) {
    const size_t n = min(sizeof(block), size_t(partition->size - offset));
    if (esp_partition_read(partition, offset, block, n) != ESP_OK) return false;
    for (size_t i = 0; i < n; ++i) if (block[i] != 0xff) return false;
    yield();
  }
  Serial.printf("STATUS,initializing_blank_partition,%s\n", label);
  return fs.format() && fs.begin(false, base, 6, label);
}

bool MotionLogger::begin() {
  ready_ = mountLogFilesystem(fs_, "motion", "/motion");
  if (!ready_) error_ = "storage_unavailable_no_autoformat";
  return ready_;
}

size_t MotionLogger::freeBytes() {
  if (!ready_) return 0;
  const size_t total = fs_.totalBytes(), used = fs_.usedBytes();
  return total > used ? total - used : 0;
}

bool MotionLogger::validId(const String& id) {
  if (id.length() != 8) return false;
  for (size_t i = 0; i < id.length(); ++i)
    if (!((id[i] >= '0' && id[i] <= '9') || (id[i] >= 'a' && id[i] <= 'f'))) return false;
  return true;
}
String MotionLogger::pathFor(const String& id) {
  if (!validId(id)) return "";
  for (const char* ext : kExtensions) {
    String path = "/" + id + ext;
    if (fs_.exists(path)) return path;
  }
  return "";
}
const char* MotionLogger::stateFor(const String& path) {
  if (path.endsWith(".bin")) return "complete";
  if (path.endsWith(".full")) return "storage_full";
  if (path.endsWith(".error")) return "io_error";
  if (path.endsWith(".sensor")) return "sensor_error";
  return recording_ && path == "/" + id_ + ".open" ? "recording" : "interrupted";
}

bool MotionLogger::start(uint64_t unixMs) {
  if (recording_) return true;
  if (!ready_) return false;
  if (freeBytes() < motion::kReserveBytes + 4096) {
    error_ = "storage_full";
    return false;
  }
  bool unique = false;
  for (int attempt = 0; attempt < 16; ++attempt) {
    char id[9];
    snprintf(id, sizeof(id), "%08lx", (unsigned long)esp_random());
    id_ = id;
    if (pathFor(id_).isEmpty()) { unique = true; break; }
  }
  if (!unique) { error_ = "id_allocation_failed"; return false; }
  file_ = fopen(("/motion/" + id_ + ".open").c_str(), "wb");
  if (!file_) { error_ = "file_open_failed"; return false; }
  startedMs_ = millis();
  uint8_t header[motion::kHeaderBytes];
  motion::makeHeader(header, startedMs_, unixMs);
  if (fwrite(header, 1, sizeof(header), file_) != sizeof(header) || !syncFile(file_)) {
    fclose(file_);
    file_ = nullptr;
    error_ = "header_write_failed";
    return false;
  }
  saved_ = 0;
  readErrors_ = consecutiveErrors_ = 0;
  buffer_.reset();
  lastFlushMs_ = startedMs_;
  lastStop_ = "recording";
  error_ = "";
  recording_ = true;
  Serial.printf("STATUS,motion_started,id=%s\n", id_.c_str());
  return true;
}

bool MotionLogger::flush() {
  return buffer_.flush([this](const uint8_t* bytes, size_t size) {
    if (freeBytes() < motion::kReserveBytes + size + 4096) {
      error_ = "storage_full";
      return false;
    }
    if (fwrite(bytes, 1, size, file_) != size || !syncFile(file_)) {
      error_ = "write_failed";
      return false;
    }
    saved_ += size / motion::kRecordBytes;
    lastFlushMs_ = millis();
    return true;
  });
}

bool MotionLogger::stop(const char* reason) {
  if (!recording_) return true;
  // Failed partial writes must never be retried into the same stream.
  bool ok = true;
  if (error_.isEmpty()) ok = flush();
  else ok = false;
  String result = ok ? reason : (error_ == "storage_full" ? "storage_full" : "io_error");
  if (fclose(file_) != 0) {
    error_ = "close_failed";
    result = "io_error";
    ok = false;
  }
  file_ = nullptr;
  recording_ = false;
  buffer_.reset();
  const char* ext = result == "complete" ? ".bin" :
                    result == "storage_full" ? ".full" :
                    result == "sensor_error" ? ".sensor" : ".error";
  if (!fs_.rename("/" + id_ + ".open", "/" + id_ + ext)) {
    error_ = "finalize_failed";
    ok = false;  // The .open file is retained and shown as interrupted.
  }
  lastStop_ = result;
  Serial.printf("STATUS,motion_stopped,id=%s,reason=%s,saved=%lu\n",
                id_.c_str(), result.c_str(), (unsigned long)saved_);
  return ok;
}

void MotionLogger::sample(motion::Sample value, uint32_t uptime) {
  if (!recording_) return;
  consecutiveErrors_ = 0;
  value.elapsedMs = uptime - startedMs_;
  if (!buffer_.add(value)) { error_ = "buffer_overflow"; stop(); return; }
  if (buffer_.count() == motion::kBatchRecords && !flush()) stop();
}
void MotionLogger::tick(uint32_t now) {
  if (recording_ && buffer_.count() && now - lastFlushMs_ >= 1000 && !flush()) stop();
}
void MotionLogger::readFailure() {
  if (!recording_) return;
  ++readErrors_;
  if (++consecutiveErrors_ >= 20) stop("sensor_error");
}

String MotionLogger::statusJson() {
  const size_t free = freeBytes();
  // Conservative estimate with 15% filesystem allowance, not measured runtime.
  const uint32_t seconds = free > motion::kReserveBytes ?
      ((free - motion::kReserveBytes) * 85 / 100) / (motion::kRecordBytes * 20) : 0;
  char body[512];
  snprintf(body, sizeof(body),
      "{\"ready\":%s,\"recording\":%s,\"id\":\"%s\",\"saved_samples\":%lu,"
      "\"buffered_samples\":%u,\"elapsed_ms\":%lu,\"read_errors\":%lu,"
      "\"free_bytes\":%u,\"estimated_seconds\":%lu,\"last_stop\":\"%s\",\"error\":\"%s\"}",
      ready_ ? "true" : "false", recording_ ? "true" : "false", id_.c_str(),
      (unsigned long)saved_, unsigned(buffer_.count()),
      (unsigned long)(recording_ ? millis() - startedMs_ : 0),
      (unsigned long)readErrors_, unsigned(free), (unsigned long)seconds,
      lastStop_.c_str(), error_.c_str());
  return body;
}

void MotionLogger::list(WebServer& server) {
  if (!ready_) { fail(server, 503, "storage_unavailable"); return; }
  // Enumerating many files can block the single-threaded sampler. Return just
  // status while recording; the client enables history after stopping.
  if (recording_) { fail(server, 409, "stop_recording_first"); return; }
  server.sendHeader("Cache-Control", "no-store");
  server.setContentLength(CONTENT_LENGTH_UNKNOWN);
  server.send(200, "application/json", "");
  server.sendContent("{\"sessions\":[");
  File root = fs_.open("/");
  bool first = true;
  for (File f = root.openNextFile(); f; f = root.openNextFile()) {
    String name = f.name();
    if (name.startsWith("/")) name.remove(0, 1);
    const int dot = name.indexOf('.');
    const String id = name.substring(0, dot < 0 ? 0 : dot);
    bool known = false;
    for (const char* ext : kExtensions) if (name == id + ext) known = true;
    if (!f.isDirectory() && validId(id) && known) {
      uint8_t h[motion::kHeaderBytes];
      const bool valid = headerFrom(f, h);
      const size_t payload = valid ? f.size() - motion::kHeaderBytes : 0;
      uint64_t unixMs = valid ? uint64_t(motion::get32(h + 16)) |
                                  (uint64_t(motion::get32(h + 20)) << 32) : 0;
      char row[320];
      snprintf(row, sizeof(row),
          "%s{\"id\":\"%s\",\"state\":\"%s\",\"bytes\":%u,\"records\":%u,"
          "\"trailing_bytes\":%u,\"header_valid\":%s,\"start_unix_ms\":%llu}",
          first ? "" : ",", id.c_str(), stateFor("/" + name), unsigned(f.size()),
          unsigned(payload / motion::kRecordBytes), unsigned(payload % motion::kRecordBytes),
          valid ? "true" : "false", (unsigned long long)unixMs);
      server.sendContent(row);
      first = false;
    }
    f.close();
    if (!server.client().connected()) break;
    yield();
  }
  root.close();
  server.sendContent("]}");
  server.sendContent("");
}

void MotionLogger::download(WebServer& server) {
  if (!ready_) { fail(server, 503, "storage_unavailable"); return; }
  if (recording_) { fail(server, 409, "stop_recording_first"); return; }
  const String id = server.arg("id");
  const String path = pathFor(id);
  if (path.isEmpty()) { fail(server, 404, "session_not_found"); return; }
  File f = fs_.open(path);
  if (!f) { fail(server, 500, "file_open_failed"); return; }
  server.sendHeader("Cache-Control", "no-store");
  if (server.arg("format") == "bin") {
    server.sendHeader("Content-Disposition", "attachment; filename=delta-" + id + ".bin");
    server.streamFile(f, "application/octet-stream");
    f.close();
    return;
  }
  uint8_t h[motion::kHeaderBytes], bytes[motion::kRecordBytes];
  motion::Sample s = {};
  if (!headerFrom(f, h)) { f.close(); fail(server, 422, "invalid_header_download_binary_for_recovery"); return; }
  const size_t records = (f.size() - motion::kHeaderBytes) / motion::kRecordBytes;
  const size_t trailing = (f.size() - motion::kHeaderBytes) % motion::kRecordBytes;
  // Validate before returning 200. A truncated tail is recoverable; corrupt
  // complete records are never exported as apparently valid measurements.
  uint32_t previousMs = 0;
  for (size_t i = 0; i < records; ++i) {
    if (f.read(bytes, sizeof(bytes)) != sizeof(bytes) || !motion::decode(bytes, s) ||
        (i && s.elapsedMs <= previousMs)) {
      f.close(); fail(server, 422, "corrupt_record_download_binary_for_recovery"); return;
    }
    previousMs = s.elapsedMs;
    if ((i % 200) == 0) yield();
  }
  if (!f.seek(motion::kHeaderBytes)) { f.close(); fail(server, 500, "file_seek_failed"); return; }
  server.sendHeader("Content-Disposition", "attachment; filename=delta-" + id + ".csv");
  server.sendHeader("X-Delta-Trailing-Bytes", String(trailing));
  server.sendHeader("X-Delta-Records", String(records));
  server.setContentLength(CONTENT_LENGTH_UNKNOWN);
  server.send(200, "text/csv; charset=utf-8", "");
  server.sendContent("elapsed_ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,temp_c,motion_g,activity_score,battery_v,state\n");
  String chunk;
  chunk.reserve(2100);
  for (size_t i = 0; i < records; ++i) {
    if (f.read(bytes, sizeof(bytes)) != sizeof(bytes) || !motion::decode(bytes, s)) {
      // Abort chunked transfer without a terminating chunk so the browser treats
      // this as a failed download, not a successful shorter session.
      f.close();
      server.client().stop();
      return;
    }
    float a[3], g[3];
    for (unsigned j = 0; j < 3; ++j) { a[j] = s.accel[j] * motion::kAccelScale; g[j] = s.gyro[j] * motion::kGyroScale; }
    char row[200];
    snprintf(row, sizeof(row), "%lu,%.6f,%.6f,%.6f,%.4f,%.4f,%.4f,%.4f,%.6f,%.6f,%.3f,%s\n",
        (unsigned long)s.elapsedMs, a[0], a[1], a[2], g[0], g[1], g[2],
        25.0f + s.temperature / 256.0f, sqrtf(a[0]*a[0] + a[1]*a[1] + a[2]*a[2]),
        s.activity / 255.0f, s.batteryMv / 1000.0f, s.active ? "Active" : "Resting");
    chunk += row;
    if (chunk.length() >= 1800) {
      server.sendContent(chunk);
      chunk = "";
      if (!server.client().connected()) { f.close(); return; }
      yield();
    }
  }
  if (chunk.length()) server.sendContent(chunk);
  server.sendContent("");
  f.close();
}

void MotionLogger::remove(WebServer& server) {
  if (!ready_) { fail(server, 503, "storage_unavailable"); return; }
  if (recording_) { fail(server, 409, "stop_recording_first"); return; }
  const String id = server.arg("id"), path = pathFor(id);
  if (path.isEmpty()) { fail(server, 404, "session_not_found"); return; }
  if (server.arg("confirm") != id) { fail(server, 400, "confirmation_required"); return; }
  if (!fs_.remove(path)) { fail(server, 500, "delete_failed"); return; }
  json(server, 200, "{\"deleted\":true}");
}
