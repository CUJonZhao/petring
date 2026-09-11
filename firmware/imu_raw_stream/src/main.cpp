#include <Arduino.h>
#include <LittleFS.h>
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>
#include <Wire.h>

#include <math.h>
#include "motion_logger.h"
#include "cloud_sync.h"
#include "records_page.h"

namespace {

constexpr uint8_t kImuAddress = 0x6A;
constexpr uint8_t kWhoAmIRegister = 0x0F;
constexpr uint8_t kCtrl1XlRegister = 0x10;
constexpr uint8_t kCtrl2GRegister = 0x11;
constexpr uint8_t kCtrl3CRegister = 0x12;
constexpr uint8_t kOutputStartRegister = 0x20;
constexpr uint8_t kExpectedWhoAmI = 0x6C;
constexpr unsigned long kSampleIntervalMs = 50;
constexpr unsigned long kBatterySampleIntervalMs = 1000;
constexpr unsigned long kBatteryLogIntervalMs = 30000;
constexpr int kBatteryMonitorPin = 35;
constexpr char kBatteryLogPath[] = "/battery_voltage.csv";
constexpr char kAccessPointSsid[] = "Delta-Collar";
constexpr char kAccessPointPassword[] = "deltacollar";

constexpr float kAccelGPerLsb = 0.000122f;  // +/-4 g range
constexpr float kGyroDpsPerLsb = 0.0175f;  // +/-500 deg/s range

bool batteryLogReady = false;
bool imuReady = false;
MotionLogger motionLogger;
CloudSync cloudSync(motionLogger);
float batteryVoltage = 0.0f;
WebServer server(80);
Preferences preferences;
String stationSsid;
String stationPassword;
bool stationCredentialsNeedSaving = false;
bool accessPointRunning = false;
bool radioEnabled = true;

void startAccessPoint();
void connectToStation(const String& ssid, const String& password, bool saveOnSuccess);

struct ImuSample {
  unsigned long timestampMs = 0;
  float accelX = 0.0f;
  float accelY = 0.0f;
  float accelZ = 0.0f;
  float gyroX = 0.0f;
  float gyroY = 0.0f;
  float gyroZ = 0.0f;
  float temperatureC = 0.0f;
  float motionG = 0.0f;
  float activityScore = 0.0f;
  bool active = false;
  bool valid = false;
};

ImuSample latestSample;

const char kDashboardHtml[] PROGMEM = R"HTML(
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Delta Collar</title>
  <style>
    :root { color-scheme: light; font-family: Arial, sans-serif; color: #1d2a2c; background: #edf1ee; }
    * { box-sizing: border-box; }
    body { margin: 0; }
    header { background: #1e3733; color: #ffffff; padding: 16px max(20px, calc((100vw - 900px) / 2)); }
    h1 { margin: 0; font-size: 22px; font-weight: 700; }
    header p { margin: 4px 0 0; color: #d8e4d9; font-size: 14px; }
    main { max-width: 900px; margin: 0 auto; padding: 18px; }
    .summary { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
    .metric, .panel { background: #ffffff; border: 1px solid #d4dcda; border-radius: 6px; }
    .metric { min-height: 84px; padding: 12px; }
    .metric dt { color: #5a6a69; font-size: 12px; }
    .metric dd { margin: 6px 0 0; font-size: 22px; font-variant-numeric: tabular-nums; }
    .metric dd.small { font-size: 16px; line-height: 1.3; }
    .panel { margin-top: 14px; padding: 14px; }
    .panel-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
    h2 { margin: 0; font-size: 16px; }
    canvas { width: 100%; height: 220px; display: block; background: #fbfcfb; border: 1px solid #e1e7e4; }
    .values { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; font-variant-numeric: tabular-nums; }
    .value { padding: 8px 0; border-top: 1px solid #edf1ee; }
    .label { display: block; color: #5a6a69; font-size: 12px; margin-bottom: 3px; }
    .controls { display: flex; gap: 8px; flex-wrap: wrap; }
    button, a.button { appearance: none; border: 1px solid #2d685a; border-radius: 4px; background: #2d685a; color: #ffffff; cursor: pointer; padding: 8px 10px; font: inherit; font-size: 13px; text-decoration: none; }
    button:hover, a.button:hover { background: #245448; }
    #connection { color: #5a6a69; font-size: 13px; }
    @media (max-width: 620px) {
      .summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .values { grid-template-columns: 1fr; }
      header { padding: 14px 18px; }
      main { padding: 12px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Delta Collar</h1>
    <p>Live IMU and battery monitor · <a href="/records" style="color:white">离线记录 / 完整历史</a></p>
  </header>
  <main>
    <section class="summary" aria-label="Current status">
      <dl class="metric"><dt>State</dt><dd id="state">Starting</dd></dl>
      <dl class="metric"><dt>Activity score</dt><dd id="activity">--</dd></dl>
      <dl class="metric"><dt>Battery</dt><dd id="battery">--</dd></dl>
      <dl class="metric"><dt>Wi-Fi clients</dt><dd id="clients">--</dd></dl>
      <dl class="metric"><dt>Apartment Wi-Fi</dt><dd id="network" class="small">Not configured</dd></dl>
    </section>
    <section class="panel">
      <div class="panel-header"><h2>Motion activity · recent ~45 seconds</h2><span id="connection">Connecting</span></div>
      <canvas id="chart" width="820" height="220" aria-label="Activity history"></canvas>
    </section>
    <section class="panel">
      <div class="panel-header"><h2>Current reading</h2><div class="controls"><a class="button" href="/setup">Wi-Fi setup</a><button id="download">Download browser CSV</button><a class="button" href="/api/battery-log">Download battery log</a></div></div>
      <div class="values">
        <div class="value"><span class="label">Acceleration (g)</span><span id="accel">--</span></div>
        <div class="value"><span class="label">Gyroscope (deg/s)</span><span id="gyro">--</span></div>
        <div class="value"><span class="label">Temperature</span><span id="temp">--</span></div>
      </div>
    </section>
  </main>
  <script>
    const history = [];
    let lastTimestamp = -1;
    const fmt = (value, digits = 2) => Number(value).toFixed(digits);
    const setText = (id, value) => document.getElementById(id).textContent = value;

    function drawChart() {
      const canvas = document.getElementById('chart');
      const context = canvas.getContext('2d');
      const width = canvas.width;
      const height = canvas.height;
      context.clearRect(0, 0, width, height);
      context.strokeStyle = '#dce5e0';
      context.lineWidth = 1;
      [0.25, 0.5, 0.75].forEach(fraction => {
        const y = height * fraction;
        context.beginPath(); context.moveTo(0, y); context.lineTo(width, y); context.stroke();
      });
      if (history.length < 2) return;
      context.strokeStyle = '#c4582b';
      context.lineWidth = 2;
      context.beginPath();
      history.forEach((sample, index) => {
        const x = (index / (history.length - 1)) * width;
        const y = height - Math.min(1, sample.activity) * (height - 6) - 3;
        index ? context.lineTo(x, y) : context.moveTo(x, y);
      });
      context.stroke();
    }

    function update(sample) {
      setText('state', sample.state);
      setText('activity', fmt(sample.activity, 3));
      setText('battery', fmt(sample.battery_v, 3) + ' V');
      setText('clients', sample.clients);
      setText('network', sample.wifi_connected ? sample.wifi_ip : 'Not connected');
      setText('accel', `${fmt(sample.ax_g, 3)}, ${fmt(sample.ay_g, 3)}, ${fmt(sample.az_g, 3)}`);
      setText('gyro', `${fmt(sample.gx_dps, 1)}, ${fmt(sample.gy_dps, 1)}, ${fmt(sample.gz_dps, 1)}`);
      setText('temp', fmt(sample.temp_c, 1) + ' C');
      if (sample.ms !== lastTimestamp) {
        lastTimestamp = sample.ms;
        history.push(sample);
        if (history.length > 180) history.shift();
        drawChart();
      }
    }

    async function poll() {
      try {
        const response = await fetch('/api/latest', { cache: 'no-store' });
        if (!response.ok) throw new Error('request failed');
        update(await response.json());
        setText('connection', 'Live');
      } catch (error) {
        setText('connection', 'Reconnecting');
      }
    }

    document.getElementById('download').addEventListener('click', () => {
      const header = 'ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,temp_c,motion_g,activity_score,battery_v,state';
      const rows = history.map(sample => [sample.ms, sample.ax_g, sample.ay_g, sample.az_g, sample.gx_dps, sample.gy_dps, sample.gz_dps, sample.temp_c, sample.motion_g, sample.activity, sample.battery_v, sample.state].join(','));
      const blob = new Blob([[header, ...rows].join('\n') + '\n'], { type: 'text/csv' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = 'delta-collar-browser-log.csv';
      link.click();
      URL.revokeObjectURL(link.href);
    });

    poll();
    setInterval(poll, 250);
  </script>
</body>
</html>
)HTML";

const char kNetworkSetupHtml[] PROGMEM = R"HTML(
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Delta Collar Network</title>
  <style>
    :root { font-family: Arial, sans-serif; color: #1d2a2c; background: #edf1ee; }
    * { box-sizing: border-box; } body { margin: 0; }
    main { max-width: 560px; margin: 36px auto; padding: 18px; }
    .panel { background: #fff; border: 1px solid #d4dcda; border-radius: 6px; padding: 18px; }
    h1 { font-size: 22px; margin: 0 0 6px; } p { color: #5a6a69; line-height: 1.45; }
    label { display: block; margin-top: 14px; font-size: 14px; font-weight: 700; }
    input { width: 100%; margin-top: 6px; padding: 10px; border: 1px solid #b9c7c2; border-radius: 4px; font: inherit; }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 18px; }
    button, a { border: 1px solid #2d685a; border-radius: 4px; background: #2d685a; color: #fff; cursor: pointer; padding: 9px 11px; font: inherit; text-decoration: none; }
    button.secondary, a.secondary { background: #fff; color: #2d685a; } #status { min-height: 22px; margin-top: 14px; font-size: 14px; }
  </style>
</head>
<body>
  <main><section class="panel">
    <h1>Apartment Wi-Fi</h1>
    <p id="current">Checking connection...</p>
    <form id="network-form">
      <label for="ssid">Network name</label><input id="ssid" name="ssid" maxlength="32" required autocomplete="off">
      <label for="password">Password</label><input id="password" name="password" type="password" maxlength="63" autocomplete="current-password">
      <div class="actions"><button type="submit">Connect</button><button class="secondary" id="forget" type="button">Forget saved network</button><a class="secondary" href="/">Back to dashboard</a></div>
    </form>
    <div id="status"></div>
  </section></main>
  <script>
    const status = document.getElementById('status');
    const current = document.getElementById('current');
    async function refresh() {
      try {
        const response = await fetch('/api/network', { cache: 'no-store' });
        const network = await response.json();
        current.textContent = network.connected ? `Connected. Dashboard address: http://${network.ip}` : 'Not connected to apartment Wi-Fi yet.';
      } catch { current.textContent = 'Connection status unavailable.'; }
    }
    document.getElementById('network-form').addEventListener('submit', async event => {
      event.preventDefault();
      status.textContent = 'Connecting...';
      const response = await fetch('/api/wifi', { method: 'POST', body: new URLSearchParams(new FormData(event.target)) });
      status.textContent = response.ok ? 'Connection request sent. Wait a few seconds for the dashboard address above.' : await response.text();
      setTimeout(refresh, 5000);
    });
    document.getElementById('forget').addEventListener('click', async () => {
      await fetch('/api/wifi', { method: 'DELETE' });
      status.textContent = 'Saved network removed.';
      refresh();
    });
    refresh();
  </script>
</body>
</html>
)HTML";

bool writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(kImuAddress);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readRegisters(uint8_t startRegister, uint8_t* values, size_t length) {
  Wire.beginTransmission(kImuAddress);
  Wire.write(startRegister);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  if (Wire.requestFrom(static_cast<int>(kImuAddress), static_cast<int>(length)) !=
      length) {
    return false;
  }

  for (size_t index = 0; index < length; ++index) {
    values[index] = Wire.read();
  }
  return true;
}

int16_t toInt16(uint8_t lowByte, uint8_t highByte) {
  return static_cast<int16_t>((static_cast<uint16_t>(highByte) << 8) | lowByte);
}

bool configureImu() {
  uint8_t whoAmI = 0;
  if (!readRegisters(kWhoAmIRegister, &whoAmI, 1) || whoAmI != kExpectedWhoAmI) {
    return false;
  }

  // Enable block-data update and multi-byte address increment.
  if (!writeRegister(kCtrl3CRegister, 0x44)) {
    return false;
  }

  // 104 Hz, +/-4 g accelerometer; 104 Hz, +/-500 deg/s gyroscope.
  return writeRegister(kCtrl1XlRegister, 0x48) &&
         writeRegister(kCtrl2GRegister, 0x44);
}

float readBatteryVoltage() {
  // GPIO35 reads the Feather's onboard 1:2 LiPo voltage divider.
  return analogReadMilliVolts(kBatteryMonitorPin) * 2.0f / 1000.0f;
}

void appendBatteryLog() {
  if (!batteryLogReady) {
    return;
  }

  File log = LittleFS.open(kBatteryLogPath, FILE_APPEND);
  if (!log) {
    Serial.println("ERROR,battery_log_open_failed");
    return;
  }

  log.printf("%lu,%.3f\n", millis(), batteryVoltage);
  log.close();
}

void dumpBatteryLog() {
  if (!batteryLogReady) {
    Serial.println("ERROR,battery_log_unavailable");
    return;
  }

  File log = LittleFS.open(kBatteryLogPath, FILE_READ);
  if (!log) {
    Serial.println("BATTERY_LOG,empty");
    return;
  }

  Serial.println("BATTERY_LOG_BEGIN,ms,battery_v");
  while (log.available()) {
    Serial.write(log.read());
  }
  log.close();
  Serial.println("BATTERY_LOG_END");
}

void clearBatteryLog() {
  if (!batteryLogReady) {
    Serial.println("ERROR,battery_log_unavailable");
    return;
  }

  LittleFS.remove(kBatteryLogPath);
  Serial.println("BATTERY_LOG,cleared");
}

void handleSerialCommands() {
  while (Serial.available()) {
    static String provisioning;
    static bool receiving = false;
    const char ch = Serial.read();
    if(receiving){
      if(ch=='\n'){Serial.println(cloudSync.configure(provisioning)?"STATUS,cloud_configured":"ERROR,cloud_config_invalid");provisioning="";receiving=false;}
      else if(ch!='\r'){if(provisioning.length()<2048)provisioning+=ch;else{provisioning="";receiving=false;}}
      continue;
    }
    if(ch=='U'){receiving=true;provisioning="";continue;}
    if(ch=='Q'){Serial.println(cloudSync.statusJson());continue;}
    switch (ch) {
      case 'D':
      case 'd':
        if (motionLogger.recording()) Serial.println("ERROR,stop_motion_recording_with_S_first");
        else dumpBatteryLog();
        break;
      case 'C':
      case 'c':
        clearBatteryLog();
        break;
      case 'R':
      case 'r':
        if (!imuReady || !motionLogger.start()) Serial.println("ERROR,motion_start_failed");
        break;
      case 'S':
      case 's':
        motionLogger.stop();
        break;
      case 'L':
      case 'l':
        Serial.println(motionLogger.statusJson());
        break;
      case 'O':
      case 'o':
        // Bench/offline control: retain credentials and the current recording.
        radioEnabled = false;
        WiFi.disconnect(false, false);
        WiFi.mode(WIFI_OFF);
        accessPointRunning = false;
        Serial.println("STATUS,WiFi_off,recording_unchanged");
        break;
      case 'W':
      case 'w':
        radioEnabled = true;
        startAccessPoint();
        connectToStation(stationSsid, stationPassword, false);
        Serial.println("STATUS,WiFi_on,recording_unchanged");
        break;
      case 'N':
      case 'n':
        Serial.printf("STATUS,network,enabled=%d,connected=%d,ip=%s\n", radioEnabled,
                      WiFi.status() == WL_CONNECTED, WiFi.localIP().toString().c_str());
        break;
    }
  }
}

void updateActivity(float motionG, float gyroX, float gyroY, float gyroZ) {
  const float dynamicAcceleration = fabsf(motionG - 1.0f);
  const float gyroMagnitude = sqrtf(gyroX * gyroX + gyroY * gyroY + gyroZ * gyroZ);
  const float rawScore = min(1.0f, dynamicAcceleration * 2.0f + gyroMagnitude / 360.0f);
  latestSample.activityScore = latestSample.activityScore * 0.82f + rawScore * 0.18f;

  if (latestSample.active && latestSample.activityScore < 0.04f) {
    latestSample.active = false;
  } else if (!latestSample.active && latestSample.activityScore > 0.08f) {
    latestSample.active = true;
  }
}

void sendLatestSample() {
  char response[512] = {};
  snprintf(response, sizeof(response),
           "{\"ms\":%lu,\"ax_g\":%.4f,\"ay_g\":%.4f,\"az_g\":%.4f,"
           "\"gx_dps\":%.2f,\"gy_dps\":%.2f,\"gz_dps\":%.2f,"
           "\"temp_c\":%.2f,\"motion_g\":%.4f,\"activity\":%.4f,"
           "\"battery_v\":%.3f,\"state\":\"%s\",\"clients\":%d,"
           "\"wifi_connected\":%s,\"wifi_ip\":\"%s\",\"valid\":%s}",
           latestSample.timestampMs, latestSample.accelX, latestSample.accelY,
           latestSample.accelZ, latestSample.gyroX, latestSample.gyroY,
           latestSample.gyroZ, latestSample.temperatureC, latestSample.motionG,
           latestSample.activityScore, batteryVoltage,
           latestSample.active ? "Active" : "Resting", WiFi.softAPgetStationNum(),
           WiFi.status() == WL_CONNECTED ? "true" : "false",
           WiFi.localIP().toString().c_str(), latestSample.valid ? "true" : "false");
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", response);
}

void sendBatteryLog() {
  if (motionLogger.recording()) {
    server.send(409, "text/plain", "Stop motion recording before downloading logs.\n");
    return;
  }
  if (!batteryLogReady) {
    server.send(503, "text/plain", "Battery log unavailable\n");
    return;
  }

  File log = LittleFS.open(kBatteryLogPath, FILE_READ);
  if (!log) {
    server.send(200, "text/csv", "ms,battery_v\n");
    return;
  }

  server.sendHeader("Content-Disposition", "attachment; filename=battery_voltage.csv");
  server.streamFile(log, "text/csv");
  log.close();
}

void saveStationCredentials() {
  preferences.begin("delta-collar", false);
  preferences.putString("wifi_ssid", stationSsid);
  preferences.putString("wifi_pass", stationPassword);
  preferences.end();
  stationCredentialsNeedSaving = false;
  Serial.printf("STATUS,STA_connected,STA_ip=%s\n", WiFi.localIP().toString().c_str());
}

void startAccessPoint() {
  if (accessPointRunning) {
    return;
  }

  WiFi.mode(WIFI_AP_STA);
  if (!WiFi.softAP(kAccessPointSsid, kAccessPointPassword)) {
    Serial.println("ERROR,AP_start_failed");
    return;
  }

  accessPointRunning = true;
  Serial.printf("STATUS,AP_started,AP_ssid=%s,AP_ip=%s\n", kAccessPointSsid,
                WiFi.softAPIP().toString().c_str());
}

void stopAccessPoint() {
  if (!accessPointRunning) {
    return;
  }

  WiFi.softAPdisconnect(true);
  accessPointRunning = false;
  Serial.println("STATUS,AP_stopped,station_connected");
}

void connectToStation(const String& ssid, const String& password, bool saveOnSuccess) {
  if (ssid.isEmpty()) {
    return;
  }

  stationSsid = ssid;
  stationPassword = password;
  stationCredentialsNeedSaving = saveOnSuccess;
  WiFi.setAutoReconnect(true);
  WiFi.begin(stationSsid.c_str(), stationPassword.c_str());
  Serial.printf("STATUS,STA_connecting,STA_ssid=%s\n", stationSsid.c_str());
}

void sendNetworkStatus() {
  char response[192] = {};
  snprintf(response, sizeof(response), "{\"connected\":%s,\"ip\":\"%s\"}",
           WiFi.status() == WL_CONNECTED ? "true" : "false",
           WiFi.localIP().toString().c_str());
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", response);
}

void receiveNetworkCredentials() {
  const String ssid = server.arg("ssid");
  const String password = server.arg("password");
  if (ssid.isEmpty() || ssid.length() > 32 || password.length() > 63) {
    server.send(400, "text/plain", "Enter a valid network name and password.\n");
    return;
  }

  connectToStation(ssid, password, true);
  server.send(202, "text/plain", "Connection started.\n");
}

void forgetNetwork() {
  WiFi.disconnect(false, true);
  preferences.begin("delta-collar", false);
  preferences.clear();
  preferences.end();
  stationSsid = "";
  stationPassword = "";
  stationCredentialsNeedSaving = false;
  startAccessPoint();
  Serial.println("STATUS,STA_credentials_cleared");
  server.send(200, "text/plain", "Saved network removed.\n");
}

void startDashboard() {
  startAccessPoint();

  server.on("/", HTTP_GET, []() { server.send_P(200, "text/html", kDashboardHtml); });
  server.on("/records", HTTP_GET, []() { server.send_P(200, "text/html", kRecordsHtml); });
  server.on("/api/recording", HTTP_GET, []() {
    server.sendHeader("Cache-Control", "no-store");
    server.send(200, "application/json", motionLogger.statusJson());
  });
  server.on("/api/cloud", HTTP_GET, []() {
    server.sendHeader("Cache-Control", "no-store");
    server.send(200, "application/json", cloudSync.statusJson());
  });
  server.on("/api/recording/start", HTTP_POST, []() {
    if (!imuReady) { server.send(503, "application/json", "{\"error\":\"imu_unavailable\"}"); return; }
    uint64_t unixMs = 0;
    const String supplied = server.arg("unix_ms");
    if (!supplied.isEmpty()) {
      char* end = nullptr;
      unixMs = strtoull(supplied.c_str(), &end, 10);
      if (*end || unixMs < 1577836800000ULL || unixMs > 4102444800000ULL) {
        server.send(400, "application/json", "{\"error\":\"invalid_unix_ms\"}"); return;
      }
    }
    const bool ok = motionLogger.start(unixMs);
    server.send(ok ? 200 : 503, "application/json", motionLogger.statusJson());
  });
  server.on("/api/recording/stop", HTTP_POST, []() {
    const bool ok = motionLogger.stop();
    server.send(ok ? 200 : 500, "application/json", motionLogger.statusJson());
  });
  server.on("/api/sessions", HTTP_GET, []() { motionLogger.list(server); });
  server.on("/api/session", HTTP_GET, []() { motionLogger.download(server); });
  server.on("/api/session", HTTP_DELETE, []() { motionLogger.remove(server); });
  server.on("/setup", HTTP_GET,
            []() { server.send_P(200, "text/html", kNetworkSetupHtml); });
  server.on("/api/latest", HTTP_GET, sendLatestSample);
  server.on("/api/battery-log", HTTP_GET, sendBatteryLog);
  server.on("/api/network", HTTP_GET, sendNetworkStatus);
  server.on("/api/wifi", HTTP_POST, receiveNetworkCredentials);
  server.on("/api/wifi", HTTP_DELETE, forgetNetwork);
  server.onNotFound([]() { server.send(404, "text/plain", "Not found\n"); });
  server.begin();

  preferences.begin("delta-collar", true);
  const String savedSsid = preferences.getString("wifi_ssid", "");
  const String savedPassword = preferences.getString("wifi_pass", "");
  preferences.end();
  connectToStation(savedSsid, savedPassword, false);
}

void printSample() {
  static unsigned long lastBatterySampleMs = 0;
  static unsigned long lastBatteryLogMs = 0;

  const unsigned long now = millis();
  if (now - lastBatterySampleMs >= kBatterySampleIntervalMs) {
    lastBatterySampleMs = now;
    batteryVoltage = readBatteryVoltage();
  }

  if (now - lastBatteryLogMs >= kBatteryLogIntervalMs) {
    lastBatteryLogMs = now;
    appendBatteryLog();
  }

  uint8_t raw[14] = {};
  if (!readRegisters(kOutputStartRegister, raw, sizeof(raw))) {
    Serial.println("ERROR,imu_read_failed");
    latestSample.valid = false;
    motionLogger.readFailure();
    return;
  }

  const int16_t temperatureRaw = toInt16(raw[0], raw[1]);
  const int16_t gyroXRaw = toInt16(raw[2], raw[3]);
  const int16_t gyroYRaw = toInt16(raw[4], raw[5]);
  const int16_t gyroZRaw = toInt16(raw[6], raw[7]);
  const int16_t accelXRaw = toInt16(raw[8], raw[9]);
  const int16_t accelYRaw = toInt16(raw[10], raw[11]);
  const int16_t accelZRaw = toInt16(raw[12], raw[13]);

  const float accelX = accelXRaw * kAccelGPerLsb;
  const float accelY = accelYRaw * kAccelGPerLsb;
  const float accelZ = accelZRaw * kAccelGPerLsb;
  const float motionG = sqrtf(accelX * accelX + accelY * accelY + accelZ * accelZ);
  const float gyroX = gyroXRaw * kGyroDpsPerLsb;
  const float gyroY = gyroYRaw * kGyroDpsPerLsb;
  const float gyroZ = gyroZRaw * kGyroDpsPerLsb;

  latestSample.timestampMs = millis();
  latestSample.accelX = accelX;
  latestSample.accelY = accelY;
  latestSample.accelZ = accelZ;
  latestSample.gyroX = gyroX;
  latestSample.gyroY = gyroY;
  latestSample.gyroZ = gyroZ;
  latestSample.temperatureC = 25.0f + temperatureRaw / 256.0f;
  latestSample.motionG = motionG;
  latestSample.valid = true;
  updateActivity(motionG, gyroX, gyroY, gyroZ);

  motion::Sample stored = {};
  stored.accel[0] = accelXRaw; stored.accel[1] = accelYRaw; stored.accel[2] = accelZRaw;
  stored.gyro[0] = gyroXRaw; stored.gyro[1] = gyroYRaw; stored.gyro[2] = gyroZRaw;
  stored.temperature = temperatureRaw;
  stored.batteryMv = uint16_t(lroundf(batteryVoltage * 1000));
  stored.activity = uint8_t(lroundf(latestSample.activityScore * 255));
  stored.active = latestSample.active;
  motionLogger.sample(stored, latestSample.timestampMs);

  Serial.printf("%lu,%.4f,%.4f,%.4f,%.2f,%.2f,%.2f,%.2f,%.4f,%.3f\n",
                latestSample.timestampMs, accelX, accelY, accelZ, gyroX, gyroY,
                gyroZ, latestSample.temperatureC, motionG, batteryVoltage);
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);
  analogReadResolution(12);
  analogSetPinAttenuation(kBatteryMonitorPin, ADC_11db);
  batteryVoltage = readBatteryVoltage();
  Wire.begin();

  imuReady = configureImu();
  if (!imuReady) {
    Serial.println("ERROR,LSM6DSOX_configuration_failed");
  }

  batteryLogReady = mountLogFilesystem(LittleFS, "spiffs", "/littlefs");
  if (!batteryLogReady) {
    Serial.println("ERROR,battery_log_mount_failed");
  } else {
    appendBatteryLog();
  }

  Serial.printf("STATUS,LSM6DSOX_%s,battery_v=%.3f\n", imuReady ? "ready" : "unavailable", batteryVoltage);
  Serial.println(
      "ms,ax_g,ay_g,az_g,gx_dps,gy_dps,gz_dps,temp_c,motion_g,battery_v");
  cloudSync.begin();
  startDashboard();
  const bool storageReady = motionLogger.begin();
  // With home sync configured, CloudSync starts sessions only away from home
  // Wi-Fi; otherwise keep the original record-from-power-on behavior.
  if (storageReady && imuReady && !cloudSync.enabled()) motionLogger.start();
}

void loop() {
  handleSerialCommands();
  server.handleClient();

  if (stationCredentialsNeedSaving && WiFi.status() == WL_CONNECTED) {
    saveStationCredentials();
  }

  if (radioEnabled && !stationSsid.isEmpty()) {
    if (WiFi.status() == WL_CONNECTED) {
      stopAccessPoint();
    } else {
      startAccessPoint();
      static uint32_t lastReconnect = 0;
      if(millis()-lastReconnect>=15000){lastReconnect=millis();WiFi.reconnect();}
    }
  }

  static unsigned long lastSampleMs = 0;
  const unsigned long now = millis();

  if (imuReady && now - lastSampleMs >= kSampleIntervalMs) {
    lastSampleMs = now;
    printSample();
  }
  motionLogger.tick(millis());
  cloudSync.tick(radioEnabled && WiFi.status() == WL_CONNECTED, imuReady, batteryVoltage);
}
