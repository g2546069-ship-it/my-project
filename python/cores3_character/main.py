import socket
import cv2
import time
import threading

UDP_IP = "0.0.0.0"
UDP_PORT = 50007

# 状態管理変数
target_level = 1       # CoreS3から届いた最新の「最大ヤバいレベル」
active_level = -1      # 現在再生中の動画のレベル
base_level = 1         # 普段の基本レベル（高いレベルのキープが終わったらここに戻る）

max_level_detected = 1 # 割り込みで検知した最大レベル
high_level_time = 0    # 最大レベルを検知した時刻
KEEP_DURATION = 9.0    # 高いレベルをキープする秒数

def udp_listener():
    global target_level, max_level_detected, high_level_time, base_level
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"[受信待機中] ポート {UDP_PORT} でデータを受信しています...")

    user_states = {}

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            level = int(data.decode('utf-8').strip())
            now = time.time()
            user_states[addr[0]] = (level, now)

            # 有効な全ユーザーのレベルを抽出
            valid_users = [lvl for ip, (lvl, t) in user_states.items() if now - t < 8]
            if not valid_users:
                continue

            current_max = max(valid_users)

            # 新しくこれまでの最大値を上回るレベルを検知した場合
            if current_max > max_level_detected:
                max_level_detected = current_max
                high_level_time = now
                print(f"★高レベル割り込み検知!: レベル {max_level_detected} (9秒キープ開始)")
            
            # 普段のベースレベルも常に更新
            base_level = current_max

        except (ValueError, OSError):
            pass

# 受信スレッド開始
threading.Thread(target=udp_listener, daemon=True).start()

cap = None
DISPLAY_WIDTH = 480

while True:
    now = time.time()

    # 【9秒タイマーの判定】
    # もし最大値を検知してから9秒以上経っていたら、最大値の記録をリセットして現在のベースレベルに戻す
    if max_level_detected > 1 and (now - high_level_time >= KEEP_DURATION):
        print(f"➔ 9秒経過したため、現在のベースレベル ({base_level}) に戻ります。")
        max_level_detected = base_level

    # 最終的にウサギに反映させるべき目標レベルを決定
    target_level = max(max_level_detected, base_level)

    # 最初の動画の読み込み、または「動画の1サイクルが終わった瞬間」に次のレベルへ切り替える
    # (active_level != target_level の条件チェックを動画終了時に行う)
    if cap is None:
        active_level = target_level
        cap = cv2.VideoCapture(f"{active_level}.mp4")

    ret, frame = cap.read()
    
    # ★ここがポイント：動画が最後のフレームに達した（1サイクル終わった）とき
    if not ret:
        # 1サイクル終わったまさにこの瞬間に、次の新しいレベルにスムーズに切り替える！
        if active_level != target_level:
            active_level = target_level
            print(f"➔ 動画サイクル終了。次の動画へ切り替えます: {active_level}.mp4")
        
        cap.release()
        cap = cv2.VideoCapture(f"{active_level}.mp4")
        ret, frame = cap.read()
        if not ret:
            continue

    # 表示サイズ調整
    h, w, _ = frame.shape
    resized_frame = cv2.resize(frame, (DISPLAY_WIDTH, int(DISPLAY_WIDTH / (w / h))))

    cv2.imshow("Group Reaction Character", resized_frame)

    key = cv2.waitKey(30) & 0xFF
    if key == ord('q'):
        break
    elif ord('0') <= key <= ord('5'): # キーボードテスト用
        max_level_detected = int(chr(key))
        high_level_time = time.time()

if cap is not None:
    cap.release()
cv2.destroyAllWindows()