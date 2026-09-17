#include <M5Unified.h>
#include <WiFi.h>
#include <WiFiUdp.h>

// Copy wifi_config.example.h to wifi_config.h and set your Wi-Fi / PC IP.
#include "wifi_config.h"

WiFiUDP udp;

float lastX = 0, lastY = 0, lastZ = 0;
float totalJerk = 0;
unsigned long lastSendTime = 0;
int lastSentLevel = 1;

// LEDの5x5全マスを同じ色に光らせる関数
void setLedColor(uint8_t r, uint8_t g, uint8_t b) {
    // M5UnifiedではDisplayにLEDマトリックスが割り当てられます
    M5.Display.fillScreen(M5.Display.color565(r, g, b));
}

// レベルに応じた色分け
void updateLevelColor(int lvl) {
    switch(lvl) {
        case 0: setLedColor(0, 0, 30);    break; // 青（睡眠・静止）
        case 1: setLedColor(0, 30, 0);    break; // 緑（通常）
        case 2: setLedColor(30, 30, 0);   break; // 黄
        case 3: setLedColor(30, 10, 0);   break; // オレンジ
        case 4: setLedColor(30, 0, 0);    break; // 赤
        case 5: setLedColor(30, 0, 30);   break; // 紫（激しい）
        default: setLedColor(0, 0, 0);    break;
    }
}

void sendLevel(int lvl) {
    udp.beginPacket(udpAddress, udpPort);
    udp.print(lvl);
    udp.endPacket();
    lastSentLevel = lvl;
    
    updateLevelColor(lvl);
    Serial.printf("SentLvl: %d\n", lastSentLevel);
}

void setup() {
    // M5Unifiedの初期化（自動でAtom Matrixを認識し、シリアル速度を115200に設定します）
    auto cfg = M5.config();
    M5.begin(cfg);
    
    // シリアルモニターを確実に9600で動かすため再設定
    Serial.begin(9600);
    delay(500);
    Serial.println("\n--- M5Unified Atom Start ---");
    
    // 起動確認テスト：一瞬白く全点灯
    setLedColor(20, 20, 20);
    delay(500);
    setLedColor(0, 0, 0);

    WiFi.begin(ssid, password);
    Serial.print("Connecting WiFi");
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        setLedColor(10, 10, 10); // 白点滅
        delay(50);
        setLedColor(0, 0, 0);
    }
    Serial.println("\nWiFi Connected!");
    
    updateLevelColor(1);
    lastSendTime = millis();
}

void loop() {
    M5.update();
    
    // センサーデータの取得
    if (M5.Imu.update()) {
        auto imu_data = M5.Imu.getImuData();
        float x = imu_data.accel.x;
        float y = imu_data.accel.y;
        float z = imu_data.accel.z;
            
        float jerk = abs(x - lastX) + abs(y - lastY) + abs(z - lastZ);
        
        if (jerk > 0.08) {
            totalJerk += jerk;
        }

        int instantLevel = 1;
        if (jerk > 5.5) instantLevel = 5;
        else if (jerk > 4.2) instantLevel = 4;
        else if (jerk > 3.0) instantLevel = 3;
        else if (jerk > 2.0) instantLevel = 2;

        lastX = x; lastY = y; lastZ = z;

        if (instantLevel > lastSentLevel) {
            sendLevel(instantLevel);
        }
    }

    // 定期送信（3秒ごと）
    if (millis() - lastSendTime >= 3000) {
        int baseLevel = 1;
        
        if (totalJerk < 2.5) {
            baseLevel = 0; 
        } 
        else if (totalJerk > 60.0) baseLevel = 3;
        else if (totalJerk > 35.0) baseLevel = 2;

        sendLevel(baseLevel);
        
        Serial.printf("JerkSum: %.1f | Accel X:%.2f Y:%.2f Z:%.2f\n", totalJerk, lastX, lastY, lastZ);
        
        totalJerk = 0;
        lastSendTime = millis();
    }

    delay(50);
}