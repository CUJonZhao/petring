#pragma once
#include "WebServer.h"
class WiFiClientSecure : public WiFiClient { public: void setCACert(const char* rootCA); void setHandshakeTimeout(unsigned long handshake_timeout); };
