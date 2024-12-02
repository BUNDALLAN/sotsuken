from ultralytics import YOLO
import mysql.connector

# MySQL接続設定
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Gina@mart1",
    database="inventory_system"
)
cursor = connection.cursor()

# YOLOモデルのロード
model = YOLO("/Users/princessabigailbundallan/Desktop/sotsuken/runs/detect/train/weights/best.pt")

# カメラからの物体検出
results = model(0, show=True, conf=0.7)  # カメラ入力、リアルタイム表示、信頼度0.7以上

# 検出された物体をデータベースに反映
for result in results:
    for prediction in result.boxes.data.tolist():
        x1, y1, x2, y2, conf, cls = prediction
        product_name = model.names[int(cls)]  # 商品名を取得

        # データベースで商品を検索
        cursor.execute("SELECT product_id, stock_quantity FROM products WHERE name = %s", (product_name,))
        product = cursor.fetchone()

        if product:
            product_id, stock_quantity = product
            print(f"Detected {product_name} with confidence {conf:.2f}")

            # 在庫を増加処理
            cursor.execute("UPDATE products SET stock_quantity = stock_quantity + 1 WHERE product_id = %s", (product_id,))
            connection.commit()

            # トランザクション履歴の登録（入庫処理）
            cursor.execute("INSERT INTO transactions (product_id, quantity) VALUES (%s, %s)", (product_id, 1))
            connection.commit()

            print(f"Stock increased for {product_name}. New stock quantity: {stock_quantity + 1}")

        else:
            print(f"Product {product_name} not found in database.")

# 接続を閉じる
connection.close()
