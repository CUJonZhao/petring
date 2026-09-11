#pragma once

#include <Arduino.h>
#include <LittleFS.h>
#include <WebServer.h>
#include <stdio.h>
#include "motion_format.h"

// Mount without destructive format-on-failure. Initialize only fully erased
// partitions; a nonempty unreadable partition requires deliberate recovery.
bool mountLogFilesystem(fs::LittleFSFS& fs, const char* label, const char* base);

class MotionLogger {
 public:
  bool begin();
  bool start(uint64_t unixMs = 0);
  bool stop(const char* reason = "complete");
  void sample(motion::Sample value, uint32_t uptime);
  void tick(uint32_t now);
  void readFailure();
  bool recording() const { return recording_; }
  bool ready() const { return ready_; }
  String statusJson();
  void list(WebServer& server);
  void download(WebServer& server);
  void remove(WebServer& server);
 private:
  size_t freeBytes();
  bool flush();
  bool validId(const String& id);
  String pathFor(const String& id);
  const char* stateFor(const String& path);
  fs::LittleFSFS fs_;
  FILE* file_ = nullptr;
  motion::Buffer buffer_;
  bool ready_ = false;
  bool recording_ = false;
  String id_;
  String error_;
  String lastStop_ = "idle";
  uint32_t startedMs_ = 0;
  uint32_t lastFlushMs_ = 0;
  uint32_t saved_ = 0;
  uint32_t readErrors_ = 0;
  uint32_t consecutiveErrors_ = 0;
};
