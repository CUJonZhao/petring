#pragma once
#include "FS.h"
#define CONTENT_LENGTH_UNKNOWN ((size_t)-1)
class WiFiClient { public: bool connected(); void stop(); };
class WebServer { public:
  void send(int code, const char* type, const String& content); void send(int code, const String& type, const String& content);
  void sendHeader(const String& name, const String& value, bool first = false); String arg(const String& name);
  void setContentLength(const size_t len); void sendContent(const String& content); WiFiClient client();
  template <typename T> size_t streamFile(T& file, const String& contentType, const int code = 200); };
