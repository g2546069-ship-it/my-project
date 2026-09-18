import cv2
import paho.mqtt.client as mqtt
import threading
import time
import ssl
import os

# =================【接続設定エリア】=================
MQTT_BROKER = "YOUR_MQTT_BROKER_URL"
MQTT_PORT   = 8883
MQTT_USER   = "YOUR_MQTT_USER"
MQTT_PASS   = "YOUR_MQTT_PASSWORD"
MQTT_TOPIC  = "usappey/level/+"
# ===================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

user_levels = {}
current_aggregated_level = 1
last_spike_time = time.time()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("\n [TEST] EMQX Cloud 接続成功！")
        client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global current_aggregated_level, last_spike_time
    try:
        user_id = msg.topic.split('/')[-1]
        val = int(msg.payload.decode('utf-8'))
        
        user_levels[user_id] = val
        highest_level = max(user_levels.values()) if user_levels else 1
        
        print(f"[受信] ID: {user_id:<8} | 送信Lv: {val} | 全員の状態: {user_levels}")
        
        if highest_level > current_aggregated_level:
            current_aggregated_level = highest_level
            last_spike_time = time.time()
            print(f"  >>> 【割込検知】最高レベル更新 -> Lv.{current_aggregated_level}")
        elif highest_level <= 1 and (time.time() - last_spike_time > 9.0):
            current_aggregated_level = highest_level

    except Exception as e:
        print("[受信エラー]", e)

def start_mqtt():
    client = mqtt.Client()
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
        
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        print("[接続例外エラー]", e)

threading.Thread(target=start_mqtt, daemon=True).start()

video_paths = {
    0: os.path.join(BASE_DIR, "0.mp4"),
    1: os.path.join(BASE_DIR, "1.mp4"),
    2: os.path.join(BASE_DIR, "2.mp4"),
    3: os.path.join(BASE_DIR, "3.mp4"),
    4: os.path.join(BASE_DIR, "4.mp4"),
    5: os.path.join(BASE_DIR, "5.mp4")
}

cv2.namedWindow("Usappey Test Window", cv2.WINDOW_NORMAL)

while True:
    play_level = current_aggregated_level
    video_path = video_paths.get(play_level, os.path.join(BASE_DIR, "1.mp4"))
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        time.sleep(1)
        continue

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # 画面サイズをコンパクト（横幅400px）に縮小
        h, w = frame.shape[:2]
        target_w = 400
        target_h = int(h * (target_w / w))
        resized_frame = cv2.resize(frame, (target_w, target_h))

        info_text = f"Lv: {current_aggregated_level} | Users: {len(user_levels)}"
        cv2.putText(resized_frame, info_text, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Usappey Test Window", resized_frame)
        
        if cv2.waitKey(30) & 0xFF == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            exit()
            
        if current_aggregated_level > play_level:
            break
            
    cap.release()