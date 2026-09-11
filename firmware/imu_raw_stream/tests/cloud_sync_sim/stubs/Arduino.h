#pragma once
// Host-only type-check stubs mirroring arduino-esp32 2.0.x signatures.
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <time.h>
#include <algorithm>
#include <string>
using std::min; using std::max;
typedef bool boolean;
unsigned long millis(); void yield(); void delay(uint32_t);
class StringSumHelper;
class String {
 public:
  std::string s;
  String() {}
  String(const char* c) : s(c ? c : "") {}
  String(const String& o) : s(o.s) {}
  explicit String(char c) : s(1, c) {}
  explicit String(int v, unsigned char base = 10) : s(std::to_string(v)) { (void)base; }
  explicit String(unsigned int v, unsigned char base = 10) : s(std::to_string(v)) { (void)base; }
  explicit String(long v, unsigned char base = 10) : s(std::to_string(v)) { (void)base; }
  explicit String(unsigned long v, unsigned char base = 10) : s(std::to_string(v)) { (void)base; }
  explicit String(float v, unsigned int dp = 2) : s(std::to_string(v)) { (void)dp; }
  explicit String(double v, unsigned int dp = 2) : s(std::to_string(v)) { (void)dp; }
  String& operator=(const String& o) { s = o.s; return *this; }
  String& operator=(const char* c) { s = c ? c : ""; return *this; }
  bool concat(const String& o) { s += o.s; return true; }
  bool concat(const char* c) { s += c; return true; }
  bool concat(char c) { s += c; return true; }
  bool concat(unsigned char v) { s += std::to_string(v); return true; }
  bool concat(int v) { s += std::to_string(v); return true; }
  bool concat(unsigned int v) { s += std::to_string(v); return true; }
  bool concat(long v) { s += std::to_string(v); return true; }
  bool concat(unsigned long v) { s += std::to_string(v); return true; }
  bool concat(float v) { s += std::to_string(v); return true; }
  bool concat(double v) { s += std::to_string(v); return true; }
  String& operator+=(const String& o) { concat(o); return *this; }
  String& operator+=(const char* c) { concat(c); return *this; }
  String& operator+=(char c) { concat(c); return *this; }
  String& operator+=(unsigned char v) { concat(v); return *this; }
  String& operator+=(int v) { concat(v); return *this; }
  String& operator+=(unsigned int v) { concat(v); return *this; }
  String& operator+=(long v) { concat(v); return *this; }
  String& operator+=(unsigned long v) { concat(v); return *this; }
  String& operator+=(float v) { concat(v); return *this; }
  String& operator+=(double v) { concat(v); return *this; }
  friend StringSumHelper& operator+(const StringSumHelper& lhs, const String& rhs);
  friend StringSumHelper& operator+(const StringSumHelper& lhs, const char* cstr);
  friend StringSumHelper& operator+(const StringSumHelper& lhs, char c);
  friend StringSumHelper& operator+(const StringSumHelper& lhs, int num);
  friend StringSumHelper& operator+(const StringSumHelper& lhs, unsigned int num);
  friend StringSumHelper& operator+(const StringSumHelper& lhs, long num);
  friend StringSumHelper& operator+(const StringSumHelper& lhs, unsigned long num);
  friend StringSumHelper& operator+(const StringSumHelper& lhs, float num);
  bool equals(const String& o) const { return s == o.s; }
  bool equals(const char* c) const { return s == c; }
  bool operator==(const String& o) const { return equals(o); }
  bool operator==(const char* c) const { return equals(c); }
  bool operator!=(const String& o) const { return !equals(o); }
  bool operator!=(const char* c) const { return !equals(c); }
  bool equalsIgnoreCase(const String&) const;
  bool startsWith(const String& p) const { return s.compare(0, p.s.size(), p.s) == 0; }
  bool endsWith(const String& p) const { return s.size() >= p.s.size() && s.compare(s.size() - p.s.size(), p.s.size(), p.s) == 0; }
  int indexOf(char c) const; int indexOf(char c, unsigned int from) const;
  int indexOf(const String& str) const; int indexOf(const String& str, unsigned int from) const;
  String substring(unsigned int from) const; String substring(unsigned int from, unsigned int to) const;
  unsigned int length() const { return s.size(); }
  const char* c_str() const { return s.c_str(); }
  bool isEmpty() const { return s.empty(); }
  void remove(unsigned int index, unsigned int count);
  char operator[](unsigned int i) const { return s[i]; }
  char& operator[](unsigned int i) { return s[i]; }
  void reserve(unsigned int);
  explicit operator bool() const = delete;
};
class StringSumHelper : public String {
 public:
  StringSumHelper(const String& s) : String(s) {}
  StringSumHelper(const char* p) : String(p) {}
  StringSumHelper(char c) : String(c) {}
  StringSumHelper(int n) : String(n) {}
  StringSumHelper(unsigned int n) : String(n) {}
  StringSumHelper(long n) : String(n) {}
  StringSumHelper(unsigned long n) : String(n) {}
};
class Print {
 public:
  size_t print(const String&); size_t print(const char*); size_t println(const char*); size_t println(const String&);
  size_t printf(const char* fmt, ...) __attribute__((format(printf, 2, 3)));
  size_t write(uint8_t); size_t write(const uint8_t*, size_t);
};
class Stream : public Print { public: int available(); int read(); };
class HardwareSerial : public Stream { public: void begin(unsigned long); };
extern HardwareSerial Serial;
#define PROGMEM
void configTime(long gmtOffset_sec, int daylightOffset_sec, const char* server1, const char* server2 = nullptr, const char* server3 = nullptr);
