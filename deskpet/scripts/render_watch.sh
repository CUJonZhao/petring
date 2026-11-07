#!/bin/bash
# DeskPet render watcher.
# Start once in your own terminal:  bash deskpet/scripts/render_watch.sh
# It runs ONLY the fixed steps below when deskpet/.work/request appears
# (model | preview | all | app). Stop it with Ctrl-C.
set -u
cd "$(dirname "$0")/.."
Q=.work
mkdir -p "$Q"

find_blender() {
  for p in "${BLENDER:-}" \
           /Applications/Blender.app/Contents/MacOS/Blender \
           "$HOME/Applications/Blender.app/Contents/MacOS/Blender"; do
    if [ -n "$p" ] && [ -x "$p" ]; then echo "$p"; return; fi
  done
  app=$(mdfind "kMDItemCFBundleIdentifier == 'org.blenderfoundation.blender'" 2>/dev/null | head -1)
  if [ -n "$app" ] && [ -x "$app/Contents/MacOS/Blender" ]; then
    echo "$app/Contents/MacOS/Blender"; return
  fi
  command -v blender || true
}

B=$(find_blender)
{ echo "watcher started $(date)"; echo "blender: ${B:-NOT FOUND}"
  [ -n "$B" ] && "$B" --version 2>/dev/null | head -1; } | tee "$Q/watcher.log"

if [ -z "$B" ]; then
  echo "Blender is not installed in /Applications or ~/Applications. Set BLENDER to its executable path and restart this watcher." | tee -a "$Q/watcher.log" >&2
  exit 1
fi

run_blender() { "$B" --background --factory-startup --python "$1"; }

while true; do
  if [ -f "$Q/request" ]; then
    job=$(head -c 32 "$Q/request" | tr -cd 'a-z')
    rm -f "$Q/request"
    start=$(date +%s)
    echo "$(date +%T) running: $job"
    case "$job" in
      model)   run_blender scripts/build_delta_model.py ;;
      preview) run_blender scripts/render_delta_preview.py ;;
      all)     run_blender scripts/build_delta_model.py && run_blender scripts/render_delta_preview.py ;;
      app)     pkill -x DeskPet; ./scripts/build_app.sh && open .build/DeskPet.app ;;
      *)       echo "unknown job: $job"; false ;;
    esac > "$Q/last.log" 2>&1
    rc=$?
    echo "$job exit=$rc secs=$(( $(date +%s) - start )) at $(date)" | tee "$Q/done"
  fi
  sleep 1
done
