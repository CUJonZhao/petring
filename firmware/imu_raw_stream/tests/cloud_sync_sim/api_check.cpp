// Compiled WITHOUT -Dprivate=public, unlike sim.cpp: this fails if anything
// main.cpp calls stops being public (a private selfTest() broke a build once).
#include "cloud_sync.h"

void api_check(CloudSync& sync, const String& provisioning) {
  sync.begin();
  sync.tick(true, true, 4.0f);
  (void)sync.configure(provisioning);
  (void)sync.enabled();
  (void)sync.statusJson();
  (void)sync.unixMs();
  sync.selfTest();
}

void logger_api_check(MotionLogger& logger, WebServer& server) {
  (void)logger.begin();
  (void)logger.start(0);
  (void)logger.stop();
  (void)logger.recording();
  (void)logger.ready();
  (void)logger.statusJson();
  (void)logger.freeBytesCached();
  logger.tick(0);
  logger.readFailure();
  logger.list(server);
  logger.download(server);
  logger.remove(server);
}
