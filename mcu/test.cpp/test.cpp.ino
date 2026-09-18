#include <M5Unified.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

// =================【接続設定エリア】=================
const char* ssid         = "YOUR_WIFI_SSID";              
const char* password     = "YOUR_WIFI_PASSWORD";      
const char* mqtt_server  = "YOUR_MQTT_BROKER_URL"; 
const int   mqtt_port    = 8883;                                     

const char* mqtt_user    = "YOUR_MQTT_USER";              
const char* mqtt_pass    = "YOUR_MQTT_PASSWORD";
// ===================================================

WiFiClientSecure espClient;
PubSubClient client(espClient);

float lastX = 0, lastY = 0, lastZ = 0;
int currentSentLevel = 1;
unsigned long lastPeakTime = 0;
unsigned long lastHeartbeatTime = 0;

void connectMQTT() {
    espClient.setInsecure();
    while (!client.connected()) {
        String clientId = "ATOM_Client_" + String(random(0xffff), HEX);
        client.connect(clientId.c_str(), mqtt_user, mqtt_pass);
        delay(1000);
    }
}

void sendLevel(int lvl) {
    if (client.connected()) {
        client.publish(mqtt_topic, String(lvl).c_str());
        currentSentLevel = lvl;
    }
}

void setup() {
    auto cfg = M5.config();
    M5.begin(cfg);
    M5.Imu.begin();

    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
    }

    client.setServer(mqtt_server, mqtt_port);
    connectMQTT();

    float x = 0, y = 0, z = 0;
    M5.Imu.getAccel(&x, &y, &z);
    lastX = x; lastY = y; lastZ = z;

    lastPeakTime = millis();
    lastHeartbeatTime = millis();
    sendLevel(1);
}

void loop() {
    M5.update();

    if (!client.connected()) {
        connectMQTT();
    }
    client.loop();

    float x = 0, y = 0, z = 0;
    M5.Imu.getAccel(&x, &y, &z);

    float jerk = abs(x - lastX) + abs(y - lastY) + abs(z - lastZ);
    lastX = x; lastY = y; lastZ = z;

    // ★ 感度としきい値の調整エリア（過剰反応を防ぐ設定）
    int rawLevel = 1;
    if (jerk > 5.5)      rawLevel = 5; // かなり激しく振ったとき
    else if (jerk > 3.8) rawLevel = 4; // しっかり振ったとき
    else if (jerk > 2.2) rawLevel = 3; // 普通に振ったとき
    else if (jerk > 1.0) rawLevel = 2; // 軽く振ったとき

    unsigned long now = millis();

    // 1. より高いレベルを検知したら即時送信
    if (rawLevel > currentSentLevel) {
        sendLevel(rawLevel);
        lastPeakTime = now;
    }

    // 2. 2.0秒間動きが収まったら自動的にレベル1へリセット
    if (currentSentLevel > 1 && (now - lastPeakTime > 2000)) {
        sendLevel(1);
    }

    // 3. 3秒ごとの定期生存送信
    if (now - lastHeartbeatTime >= 3000) {
        sendLevel(currentSentLevel);
        lastHeartbeatTime = now;
    }

    delay(50);
}