#pragma once
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
  void tick(bool connected, bool imuReady, float voltage);
  bool configure(const String& line);
  bool enabled() const { return enabled_; }
  String statusJson() const;
  uint64_t unixMs() const;

 private:
  enum class Result { ok, retry, reject, auth };
  struct Entry {
    String id, path;
    size_t size = 0;
    uint64_t startMs = 0;
    bool ack = false, retry = false, reject = false;
  };
  void away(uint32_t now, bool imuReady);
  void home(uint32_t now, float voltage);
  void upload(uint32_t now);
  bool heartbeat(uint32_t now, float voltage);
  Result request(const char* action, const String& query, const uint8_t* bytes = nullptr,
                 size_t size = 0, bool post = false);
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
  String url_, bypass_, token_, body_;
  String path_, id_, sha_, query_, state_;
  String mode_ = "unconfigured", error_;
  size_t size_ = 0, offset_ = 0;
  bool enabled_ = false, atHome_ = false, knownOffset_ = false;
  bool wasRecording_ = false, holdUntilHome_ = false, rejectsCleared_ = false;
  uint32_t awaySince_ = 0, homeSince_ = 0, startRetryAt_ = 0, retryAt_ = 0;
  uint32_t lastHeartbeat_ = 0, lastScan_ = 0, lastPruneCheck_ = 0;
  uint32_t pending_ = 0, synced_ = 0, rejected_ = 0, uploaded_ = 0, pruned_ = 0;
  uint64_t lastSyncUnixMs_ = 0;
};
