#pragma once
#include "FS.h"
namespace fs { class LittleFSFS : public FS { public:
  bool begin(bool = false, const char* = "/littlefs", uint8_t = 10, const char* = "spiffs") { return true; }
  bool format() { return true; }
  size_t totalBytes() { return 4194304; }
  size_t usedBytes() { size_t u = 8192; for (auto& kv : g_files) u += (kv.second.size() + 4095) / 4096 * 4096; return u; } }; }
