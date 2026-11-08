// Builds the real src/motion_logger.cpp for the host simulation. Its stdio
// calls are routed to the in-memory filesystem the stubs use, so start(),
// flush() and stop() run unchanged. Every header the source needs is included
// first: <cstdio> would otherwise undo the macros below.
#include <cmath>
#include <cstdio>
#include <map>
#include <math.h>
#include <string>
#include <unistd.h>

#include <esp_partition.h>
#include <esp_system.h>

#include "motion_logger.h"

FILE* sim_fopen(const char* path, const char* mode);
size_t sim_fwrite(const void* bytes, size_t size, size_t count, FILE* file);
int sim_fsync(int fd);
#define fopen sim_fopen
#define fwrite sim_fwrite
#define fsync sim_fsync
#include "../../src/motion_logger.cpp"
#undef fopen
#undef fwrite
#undef fsync

extern std::map<std::string, std::string> g_files;
static std::map<FILE*, std::string> g_open;

// "/motion/<id>.open" -> in-memory "/<id>.open"; a real temporary file keeps
// fflush/fclose/fileno working.
FILE* sim_fopen(const char* path, const char* mode) {
  std::string name(path);
  const std::string base = "/motion";
  if (name.compare(0, base.size(), base) != 0) return fopen(path, mode);
  name = name.substr(base.size());
  FILE* file = tmpfile();
  if (!file) return nullptr;
  g_open[file] = name;
  g_files[name] = "";
  return file;
}

size_t sim_fwrite(const void* bytes, size_t size, size_t count, FILE* file) {
  const auto it = g_open.find(file);
  if (it != g_open.end() && g_files.count(it->second))
    g_files[it->second].append(static_cast<const char*>(bytes), size * count);
  return fwrite(bytes, size, count, file);
}

int sim_fsync(int) { return 0; }
