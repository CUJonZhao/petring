#pragma once
#include <Arduino.h>
#include "WiFiClientSecure.h"
typedef enum { HTTPC_DISABLE_FOLLOW_REDIRECTS, HTTPC_STRICT_FOLLOW_REDIRECTS, HTTPC_FORCE_FOLLOW_REDIRECTS } followRedirects_t;
class HTTPClient { public:
  bool begin(WiFiClient& client, String url); void end(void);
  void addHeader(const String& name, const String& value, bool first = false, bool replace = true);
  void setConnectTimeout(int32_t connectTimeout); void setTimeout(uint16_t timeout); void setFollowRedirects(followRedirects_t follow); void setReuse(bool reuse);
  void collectHeaders(const char* headerKeys[], const size_t headerKeysCount); String header(const char* name);
  int GET(); int POST(uint8_t* payload, size_t size); int POST(String payload); String getString(void); };
