#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
xcrun swift build -c release
APP=".build/DeskPet.app"
# Recreate the bundle: overwriting a launched binary in place breaks its code signature cache.
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
mkdir -p "$APP/Contents/Resources"
cp .build/release/DeskPet "$APP/Contents/MacOS/DeskPet"
cp Resources/Delta.usdz "$APP/Contents/Resources/Delta.usdz"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>com.petring.deskpet</string>
  <key>CFBundleName</key><string>DeskPet</string>
  <key>CFBundleExecutable</key><string>DeskPet</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.1.0</string>
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
codesign --force --sign - "$APP" >/dev/null 2>&1 || true
echo "Built $APP"
