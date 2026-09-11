#pragma once
// Host-only stubs for tests/cloud_sync_sim (arduino-esp32 2.0.x signatures, in-memory FS).
#include <Arduino.h>
#include <map>
#include <memory>
#include <vector>
#define FILE_READ "r"
#define FILE_WRITE "w"
#define FILE_APPEND "a"
extern std::map<std::string, std::string> g_files;  // "/name" -> bytes
namespace fs {
enum SeekMode { SeekSet = 0, SeekCur = 1, SeekEnd = 2 };
struct Handle { std::string path; bool dir = false; size_t pos = 0; std::vector<std::string> list; size_t next = 0; bool closed = false; };
class File : public Stream {
 public:
  std::shared_ptr<Handle> h;
  size_t read(uint8_t* buf, size_t n) { auto& c = g_files[h->path]; size_t k = std::min(n, c.size() > h->pos ? c.size() - h->pos : 0); memcpy(buf, c.data() + h->pos, k); h->pos += k; return k; }
  bool seek(uint32_t pos, SeekMode = SeekSet) { h->pos = pos; return pos <= g_files[h->path].size(); }
  size_t size() const { return h->dir ? 0 : g_files[h->path].size(); }
  void close() { if (h) h->closed = true; }
  operator bool() const { return h && !h->closed; }
  const char* name() const { return h->path.c_str() + 1; }
  bool isDirectory() { return h->dir; }
  File openNextFile(const char* = FILE_READ) { File f; if (h->next < h->list.size()) { f.h = std::make_shared<Handle>(); f.h->path = h->list[h->next++]; } return f; }
  size_t print(const String& s) { g_files[h->path] += s.s; return s.length(); }
};
class FS {
 public:
  File open(const String& p, const char* mode = FILE_READ, bool = false) { return open(p.c_str(), mode); }
  File open(const char* p, const char* mode = FILE_READ, bool = false) {
    File f; std::string path(p);
    if (path == "/") { f.h = std::make_shared<Handle>(); f.h->dir = true; f.h->path = "/"; for (auto& kv : g_files) f.h->list.push_back(kv.first); return f; }
    if (mode[0] == 'r' && !g_files.count(path)) return f;
    if (mode[0] == 'w') g_files[path] = "";
    f.h = std::make_shared<Handle>(); f.h->path = path; return f;
  }
  bool exists(const String& p) { return g_files.count(p.s) > 0; }
  bool exists(const char* p) { return g_files.count(p) > 0; }
  bool remove(const String& p) { return g_files.erase(p.s) > 0; }
  bool remove(const char* p) { return g_files.erase(p) > 0; }
  bool rename(const String& a, const String& b) { if (!g_files.count(a.s)) return false; g_files[b.s] = g_files[a.s]; g_files.erase(a.s); return true; }
};
}
using fs::FS; using fs::File; using fs::SeekSet;
