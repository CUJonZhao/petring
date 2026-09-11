#pragma once
#include <Arduino.h>
class Preferences { public: bool begin(const char* name, bool readOnly = false, const char* partition_label = NULL); void end();
  bool clear(); size_t putString(const char* key, String value); String getString(const char* key, String defaultValue = String()); };
