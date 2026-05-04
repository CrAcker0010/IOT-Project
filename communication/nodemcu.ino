/*
 * nodemcu.ino  —  Home Automation Firmware
 * ==========================================
 * Platform : ESP32 / NodeMCU ESP8266
 * Role     : WiFi HTTP server that receives commands from the
 *            Raspberry Pi and controls:
 *              • Light 1  (relay on D1 / GPIO5)
 *              • Light 2  (relay on D2 / GPIO4)
 *              • Light 3  (relay on D3 / GPIO0)
 *              • Door 4   (relay on D4 / GPIO2)
 *
 * API Endpoints (HTTP GET):
 *   /light/1/on    /light/1/off
 *   /light/2/on    /light/2/off
 *   /light/3/on    /light/3/off
 *   /door/4/on     /door/4/off   (on = unlock / open)
 *   /status        → returns JSON with current states
 *   /all/off       → turn everything off
 *
 * ── HOW TO CONFIGURE ─────────────────────────────────────────────
 * 1. Set WIFI_SSID and WIFI_PASSWORD below.
 * 2. After flashing, open Serial Monitor (9600 baud) to find the
 *    IP address the ESP was assigned.
 * 3. Set NODEMCU_IP in the Raspberry Pi config.py to that address.
 * ─────────────────────────────────────────────────────────────────
 */

// ── Board-specific WiFi library ───────────────────────────────────
#ifdef ESP32
  #include <WiFi.h>
  #include <WebServer.h>
  WebServer server(80);
#else
  // NodeMCU ESP8266
  #include <ESP8266WiFi.h>
  #include <ESP8266WebServer.h>
  ESP8266WebServer server(80);
#endif

// ── WiFi Credentials ─────────────────────────────────────────────
const char* WIFI_SSID     = "krish";
const char* WIFI_PASSWORD = "harekrishna";

// ── Pin Definitions ───────────────────────────────────────────────
// Relay modules are usually ACTIVE LOW — change RELAY_ON / RELAY_OFF if yours differ
#define RELAY_ON   LOW
#define RELAY_OFF  HIGH

// NodeMCU D-pins map to GPIO numbers printed on the board
#define PIN_LIGHT1  5   // GPIO5
#define PIN_LIGHT2  2   // GPIO4
#define PIN_LIGHT3  3   // GPIO0
#define PIN_DOOR4   18   // GPIO2  (also the onboard LED on most boards)

// ── State Tracking ────────────────────────────────────────────────
bool stateLight1 = false;
bool stateLight2 = false;
bool stateLight3 = false;
bool stateDoor4  = false;

// ── Helper: set relay and update state ───────────────────────────
void setRelay(int pin, bool& state, bool turnOn) {
  state = turnOn;
  digitalWrite(pin, turnOn ? RELAY_ON : RELAY_OFF);
}

// ── JSON Status Builder ──────────────────────────────────────────
String buildStatus() {
  String json = "{";
  json += "\"light1\":" + String(stateLight1 ? "true" : "false") + ",";
  json += "\"light2\":" + String(stateLight2 ? "true" : "false") + ",";
  json += "\"light3\":" + String(stateLight3 ? "true" : "false") + ",";
  json += "\"door4\":"  + String(stateDoor4  ? "true" : "false");
  json += "}";
  return json;
}

// ── HTTP Route Handlers ───────────────────────────────────────────
void handleStatus() {
  server.send(200, "application/json", buildStatus());
}

void handleLight1On()  { setRelay(PIN_LIGHT1, stateLight1, true);  server.send(200, "application/json", buildStatus()); }
void handleLight1Off() { setRelay(PIN_LIGHT1, stateLight1, false); server.send(200, "application/json", buildStatus()); }

void handleLight2On()  { setRelay(PIN_LIGHT2, stateLight2, true);  server.send(200, "application/json", buildStatus()); }
void handleLight2Off() { setRelay(PIN_LIGHT2, stateLight2, false); server.send(200, "application/json", buildStatus()); }

void handleLight3On()  { setRelay(PIN_LIGHT3, stateLight3, true);  server.send(200, "application/json", buildStatus()); }
void handleLight3Off() { setRelay(PIN_LIGHT3, stateLight3, false); server.send(200, "application/json", buildStatus()); }

void handleDoor4On()  { setRelay(PIN_DOOR4, stateDoor4, true);  server.send(200, "application/json", buildStatus()); }
void handleDoor4Off() { setRelay(PIN_DOOR4, stateDoor4, false); server.send(200, "application/json", buildStatus()); }

void handleAllOff() {
  setRelay(PIN_LIGHT1, stateLight1, false);
  setRelay(PIN_LIGHT2, stateLight2, false);
  setRelay(PIN_LIGHT3, stateLight3, false);
  setRelay(PIN_DOOR4,  stateDoor4,  false);
  server.send(200, "application/json", buildStatus());
}

void handleNotFound() {
  server.send(404, "text/plain", "Not Found");
}

// ── Setup ─────────────────────────────────────────────────────────
void setup() {
  Serial.begin(9600);

  // Output pins — safe initial state (all OFF)
  pinMode(PIN_LIGHT1, OUTPUT); digitalWrite(PIN_LIGHT1, RELAY_OFF);
  pinMode(PIN_LIGHT2, OUTPUT); digitalWrite(PIN_LIGHT2, RELAY_OFF);
  pinMode(PIN_LIGHT3, OUTPUT); digitalWrite(PIN_LIGHT3, RELAY_OFF);
  pinMode(PIN_DOOR4,  OUTPUT); digitalWrite(PIN_DOOR4,  RELAY_OFF);

  // Connect to WiFi
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected!");
  Serial.print("NodeMCU IP Address: ");
  Serial.println(WiFi.localIP());   // ← Copy this into config.py → NODEMCU_IP

  // Register HTTP routes
  server.on("/status",      HTTP_GET, handleStatus);

  server.on("/light/1/on",  HTTP_GET, handleLight1On);
  server.on("/light/1/off", HTTP_GET, handleLight1Off);
  server.on("/light/2/on",  HTTP_GET, handleLight2On);
  server.on("/light/2/off", HTTP_GET, handleLight2Off);
  server.on("/light/3/on",  HTTP_GET, handleLight3On);
  server.on("/light/3/off", HTTP_GET, handleLight3Off);

  server.on("/door/4/on",   HTTP_GET, handleDoor4On);
  server.on("/door/4/off",  HTTP_GET, handleDoor4Off);

  server.on("/all/off",     HTTP_GET, handleAllOff);

  server.onNotFound(handleNotFound);
  server.begin();

  Serial.println("HTTP server started. Waiting for commands...");
}

// ── Main Loop ─────────────────────────────────────────────────────
void loop() {
  server.handleClient();   // Process incoming HTTP requests
}
