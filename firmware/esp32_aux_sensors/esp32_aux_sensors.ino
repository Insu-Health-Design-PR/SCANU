#include <Arduino.h>

// Minimal ESP32 auxiliary sensor bridge for SCANU.
// Emits newline-delimited JSON messages compatible with:
// software/layer1_aux_sensors/aux_protocol.py

static const int PIR_PIN = 27;
static const int RF_PIN = 26;                 // Digital RF trigger input
static const int THERMAL_PROBE_PIN = 34;      // ADC input (ESP32: input-only pin)

// Set these to false if a sensor is not wired yet.
static const bool ENABLE_PIR = true;
static const bool ENABLE_RF = true;
static const bool ENABLE_THERMAL_PROBE = true;

// ADC conversion assumptions for a simple analog thermal probe path.
// Adjust these when your exact sensor/conditioning circuit is finalized.
static const float ADC_MAX = 4095.0f;
static const float VREF = 3.3f;
static const float THERMAL_OFFSET_C = 0.0f;
static const float THERMAL_SCALE_C_PER_V = 100.0f;

static const unsigned long STREAM_PERIOD_MS = 100;      // 10 Hz readings
static const unsigned long HEARTBEAT_PERIOD_MS = 2000;  // 0.5 Hz heartbeat

unsigned long g_frame_id = 0;
unsigned long g_last_stream_ms = 0;
unsigned long g_last_heartbeat_ms = 0;

void setup() {
  if (ENABLE_PIR) {
    pinMode(PIR_PIN, INPUT);
  }
  if (ENABLE_RF) {
    pinMode(RF_PIN, INPUT);
  }
  if (ENABLE_THERMAL_PROBE) {
    pinMode(THERMAL_PROBE_PIN, INPUT);
    analogReadResolution(12);  // 0..4095
  }

  Serial.begin(115200);

  // Small startup delay to stabilize USB serial host connection.
  delay(150);
}

static void sendHeartbeat(unsigned long now_ms) {
  Serial.printf(
    "{\"type\":\"heartbeat\",\"device_id\":\"esp32_aux_01\",\"fw\":\"0.1.0\",\"uptime_ms\":%lu}\n",
    now_ms
  );
}

static void sendReading(unsigned long now_ms) {
  const int pir_value = ENABLE_PIR ? (digitalRead(PIR_PIN) ? 1 : 0) : 0;
  const int rf_value = ENABLE_RF ? (digitalRead(RF_PIN) ? 1 : 0) : 0;

  float thermal_c = 0.0f;
  if (ENABLE_THERMAL_PROBE) {
    const int raw = analogRead(THERMAL_PROBE_PIN);
    const float volts = (static_cast<float>(raw) / ADC_MAX) * VREF;
    thermal_c = THERMAL_OFFSET_C + (volts * THERMAL_SCALE_C_PER_V);
  }

  g_frame_id += 1;

  Serial.printf(
    "{\"type\":\"reading\",\"frame_id\":%lu,\"ts_device_ms\":%lu,\"readings\":["
    "{\"sensor_id\":\"pir_1\",\"sensor_type\":\"pir\",\"value\":%d,\"unit\":\"bool\",\"quality\":1.0},"
    "{\"sensor_id\":\"rf_1\",\"sensor_type\":\"rf\",\"value\":%d,\"unit\":\"bool\",\"quality\":1.0},"
    "{\"sensor_id\":\"thermal_probe_1\",\"sensor_type\":\"thermal_probe\",\"value\":%.3f,\"unit\":\"celsius\",\"quality\":1.0}"
    "]}\n",
    g_frame_id,
    now_ms,
    pir_value,
    rf_value,
    thermal_c
  );
}

void loop() {
  const unsigned long now_ms = millis();

  if (now_ms - g_last_heartbeat_ms >= HEARTBEAT_PERIOD_MS) {
    sendHeartbeat(now_ms);
    g_last_heartbeat_ms = now_ms;
  }

  if (now_ms - g_last_stream_ms >= STREAM_PERIOD_MS) {
    sendReading(now_ms);
    g_last_stream_ms = now_ms;
  }
}
