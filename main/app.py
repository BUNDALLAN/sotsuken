from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import cv2
from ultralytics import YOLO
import calendar

app = Flask(__name__)
app.debug = True

# グローバル変数
video_stream = cv2.VideoCapture(0)

# データベース接続
def get_db_connection():
    try:
        return mysql.connector.connect(
             host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
    except Error as e:
        print(f"Error: {e}")
        return None

@app.teardown_appcontext
def close_connection(exception):
    if connection and connection.is_connected():
        connection.close()

# グローバル接続変数
connection = get_db_connection()

model = YOLO("sotsuken/runs//detect/train/weights/best.pt")

# メニュー画面
@app.route("/")
def index():
    return render_template("index.html")

# 在庫一覧
@app.route("/view_stock")
def view_stock():
    connection = get_db_connection()
    if not connection:
        return "データベース接続に失敗しました。", 500

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM inventory")
            items = cursor.fetchall()
        return render_template("view_stock.html", items=items)
    finally:
        connection.close()

# カレンダー画面
@app.route("/calendar")
def calendar_view():
    year = request.args.get('year', default=datetime.now().year, type=int)
    month = request.args.get('month', default=datetime.now().month, type=int)
    cal = calendar.monthcalendar(year, month)

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    connection = get_db_connection()
    if connection is None:
        return "データベース接続に失敗しました。", 500

    cursor = connection.cursor()
    try:
        cursor.execute("SELECT * FROM inventory_log WHERE YEAR(date) = %s AND MONTH(date) = %s", (year, month))
        logs = cursor.fetchall()

        day_logs = {}
        for log in logs:
            if isinstance(log[0], int):
                log = list(log)
                log[0] = datetime.fromtimestamp(log[0])
            day = log[0].day
            if day not in day_logs:
                day_logs[day] = {'inbound': 0, 'outbound': 0}
            if log[3] == 'inbound':
                day_logs[day]['inbound'] += log[2]
            elif log[3] == 'outbound':
                day_logs[day]['outbound'] += log[2]

        return render_template("calendar.html", 
                               year=year, month=month, cal=cal, day_logs=day_logs,
                               prev_year=prev_year, prev_month=prev_month, 
                               next_year=next_year, next_month=next_month)
    except mysql.connector.errors.ProgrammingError:
        return "クエリ実行に失敗しました。", 500

# 日付ごとの詳細情報を表示
@app.route("/calendar/<int:year>/<int:month>/<int:day>")
def day_details(year, month, day):
    connection = get_db_connection()
    if connection is None:
        return "データベース接続に失敗しました。", 500

    cursor = connection.cursor()
    try:
        # 指定された日にちの入庫・出庫のデータを取得
        cursor.execute("""
            SELECT product_name, quantity, type
            FROM inventory_log
            WHERE YEAR(date) = %s AND MONTH(date) = %s AND DAY(date) = %s
        """, (year, month, day))

        logs = cursor.fetchall()

        inbound_items = [log for log in logs if log[2] == 'inbound']
        outbound_items = [log for log in logs if log[2] == 'outbound']

        return render_template("day_details.html", 
                               year=year, month=month, day=day, 
                               inbound_items=inbound_items, outbound_items=outbound_items)
    except mysql.connector.errors.ProgrammingError:
        return "クエリ実行に失敗しました。", 500

# カメラからのフレーム生成
def generate_frames():
    while True:
        success, frame = video_stream.read()
        if not success:
            break
        else:
            # フレームサイズを変更 (幅 640px、高さ 480px に調整)
            frame = cv2.resize(frame, (400, 300))
            
             # YOLO 推論 (信頼度 0.9 を指定)
            results = model(frame, conf=0.9)
            
            # 推論結果の描画
            annotated_frame = results[0].plot()
            # JPEG にエンコード
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# 入庫用カメラ映像
@app.route('/video_feed/inbound')
def video_feed_inbound():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# 出庫用カメラ映像
@app.route('/video_feed/outbound')
def video_feed_outbound():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


# 入庫・出庫処理
@app.route("/<action>", methods=["GET", "POST"])
def inventory_update(action):
    if action not in ["inbound", "outbound"]:
        return "無効な操作です。", 400

    if request.method == "POST":
        product_name = request.form["product_name"]
        quantity = int(request.form["quantity"])

        connection = get_db_connection()
        if not connection:
            return "データベース接続に失敗しました。", 500

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT stock FROM inventory WHERE product_name = %s", (product_name,))
                current_stock = cursor.fetchone()
                if not current_stock:
                    return f"商品 {product_name} が見つかりません。", 404

                new_stock = (current_stock[0] + quantity if action == "inbound" else current_stock[0] - quantity)
                if new_stock < 0:
                    return "在庫数が不足しています。", 400

                cursor.execute("UPDATE inventory SET stock = %s WHERE product_name = %s", (new_stock, product_name))
                cursor.execute("INSERT INTO inventory_log (product_name, quantity, type, date,item_name) VALUES (%s, %s, %s, NOW(),%s)",
                               (product_name, quantity, action, product_name))
                connection.commit()
            return redirect(url_for("view_stock"))
        finally:
            connection.close()

    return render_template(f"{action}.html")

   # カメラ起動処理
@app.route('/start_camera/<mode>', methods=['POST'])
def start_camera(mode):
    cap = cv2.VideoCapture(0)  # カメラ起動
    product_name = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # YOLOモデルで認識
        results = model(frame)
        if results and len(results[0].boxes) > 0:
            for box in results[0].boxes:
                class_id = int(box.cls[0])
                product_name = model.names[class_id]
                break

        if product_name:
            break

    cap.release()  # カメラリソースを解放
    return jsonify({'product_name': product_name, 'mode': mode})

if __name__ == "__main__":
    app.run(debug=True, port=5000)


