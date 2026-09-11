// Link-time stubs for the host simulation; no network or flash access.
#include "WebServer.h"
#include "esp_partition.h"
#include "esp_system.h"
const esp_partition_t* esp_partition_find_first(esp_partition_type_t, esp_partition_subtype_t, const char*) { return nullptr; }
esp_err_t esp_partition_read(const esp_partition_t*, size_t, void*, size_t) { return 0; }
uint32_t esp_random(void) { return 0x12345678; }
void WebServer::send(int, const char*, const String&) {} void WebServer::sendHeader(const String&, const String&, bool) {}
String WebServer::arg(const String&) { return String(); } void WebServer::setContentLength(const size_t) {}
void WebServer::sendContent(const String&) {} WiFiClient WebServer::client() { return WiFiClient(); }
bool WiFiClient::connected() { return true; } void WiFiClient::stop() {}
size_t Print::print(const char* s) { return ::printf("%s", s); } size_t Print::println(const char* s) { return ::printf("%s\n", s); }
size_t Print::print(const String& s) { return print(s.c_str()); }
template <> size_t WebServer::streamFile<fs::File>(fs::File&, const String&, const int) { return 0; }
void String::reserve(unsigned int) {}
#include "HTTPClient.h"
#include "Preferences.h"
bool HTTPClient::begin(WiFiClient&, String) { return false; } void HTTPClient::end() {}
void HTTPClient::addHeader(const String&, const String&, bool, bool) {} void HTTPClient::setConnectTimeout(int32_t) {}
void HTTPClient::setTimeout(uint16_t) {} void HTTPClient::setFollowRedirects(followRedirects_t) {}
int HTTPClient::GET() { return -1; } int HTTPClient::POST(uint8_t*, size_t) { return -1; } String HTTPClient::getString() { return String(); }
void WiFiClientSecure::setCACert(const char*) {} void WiFiClientSecure::setHandshakeTimeout(unsigned long) {}
bool Preferences::begin(const char*, bool, const char*) { return false; } void Preferences::end() {}
size_t Preferences::putString(const char*, String) { return 0; } String Preferences::getString(const char*, String d) { return d; }
