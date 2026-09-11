#!/bin/sh
# Host simulation of cloud-sync storage rules (no hardware). -Dprivate=public exposes
# internals to the test harness only.
set -e
cd "$(dirname "$0")"
OUT="${TMPDIR:-/tmp}/delta-cloud-sync-sim"
c++ -std=gnu++11 -Dprivate=public -Wall -Wno-unused-parameter -I stubs -I ../../src \
  sim.cpp support.cpp ../../src/cloud_sync.cpp ../../src/motion_logger.cpp -o "$OUT"
"$OUT"
