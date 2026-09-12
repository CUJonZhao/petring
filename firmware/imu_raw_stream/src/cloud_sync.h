#pragma once
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

#include <vector>

#include "motion_logger.h"

// Home Wi-Fi sync. While the saved home network is out of reach the board
// records by itself; after a stable home connection it closes that session
// and uploads every session the website has not yet confirmed, in resumable
// 16 KiB chunks. Cloud-confirmed sessions are deleted locally only when space
// for about an hour of recording is needed (oldest first).
class CloudSync {
 public:
  explicit CloudSync(MotionLogger& logger) : logger_(logger) {}
  void begin();
  // connected: station link to the saved home Wi-Fi is up.
  // active: the recorder's movement flag for the current sample.
  void tick(bool connected, bool imuReady, bool active, float voltage);
  bool configure(const String& line);
  bool enabled() const { return enabled_; }
  String statusJson() const;
  uint64_t unixMs() const;
  // Read-only probe of the site's status endpoint, for timing only (serial "T").
  void selfTest(uint8_t rounds = 3);

 private:
  enum class Result { ok, retry, reject, auth };
  struct Entry {
    String id, path;
    size_t size = 0;
    uint64_t startMs = 0;
    bool ack = false, retry = false, reject = false;
  };
  void away(uint32_t now, bool imuReady);
  void home(uint32_t now, bool imuReady, float voltage);
  void trackMotion(uint32_t now, bool active);
  bool sustainedMotion(uint32_t now) const;
  bool stillFor(uint32_t now, uint32_t span) const;
  void upload(uint32_t now);
  bool heartbeat(uint32_t now, float voltage);
  Result request(const char* action, const String& query, const uint8_t* bytes = nullptr,
                 size_t size = 0, bool post = false);
  int send(const char* action, const String& query, const uint8_t* bytes, size_t size,
           bool post, String& location);
  void closeConnection();
  bool confirmed() const;
  std::vector<Entry> scan();
  bool selectFile();
  bool hashFile();
  size_t prune(size_t targetFree);
  void clearMarkers(const char* ext);
  void markFile(const char* ext);
  void markDone();
  void clearTransfer();
  void fail(Result result, uint32_t now);

  MotionLogger& logger_;
  // Both must outlive a request: ~HTTPClient() stops its client, so a
  // per-request HTTPClient would close the socket it just kept open.
  WiFiClientSecure client_;
  HTTPClient http_;
  String url_, bypass_, token_, body_;
  String path_, id_, sha_, query_, state_;
  String mode_ = "unconfigured", error_, keepAlive_;
  size_t size_ = 0, offset_ = 0;
  bool enabled_ = false, atHome_ = false, knownOffset_ = false;
  bool wasRecording_ = false, holdUntilHome_ = false, rejectsCleared_ = false;
  bool startedByMotion_ = false;
  bool socketOpen_ = false;
  uint32_t awaySince_ = 0, homeSince_ = 0, startRetryAt_ = 0, retryAt_ = 0;
  uint32_t lastHeartbeat_ = 0, lastScan_ = 0, lastPruneCheck_ = 0;
  uint32_t activeSince_ = 0, lastActiveMs_ = 0, motionSuppressUntil_ = 0;
  uint32_t pending_ = 0, synced_ = 0, rejected_ = 0, uploaded_ = 0, pruned_ = 0;
  uint64_t lastSyncUnixMs_ = 0;
};
