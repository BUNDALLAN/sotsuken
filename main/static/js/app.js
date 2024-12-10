
let cameraFeed = document.getElementById("cameraFeed");
let quantityInput = document.getElementById("quantityInput");
let activateCameraBtn = document.getElementById("activateCameraBtn");

function startCamera() {
    // カメラを起動
    navigator.mediaDevices.getUserMedia({ video: true })
        .then((stream) => {
            cameraFeed.srcObject = stream;
            // YOLO認識の開始
            recognizeObject();
        })
        .catch((err) => {
            console.log("カメラの起動に失敗しました:", err);
        });
}

function recognizeObject() {
    // YOLOを使った認識処理（サンプル）
    // 商品名が 'takoyaki' と認識された場合、数量入力ボタンを表示
    yolo.detect(cameraFeed).then((detections) => {
        for (let detection of detections) {
            if (detection.class === 'takoyaki') {
                // 「takoyaki」を認識したら数量入力フォームを表示
                quantityInput.style.display = 'block';
                break;
            }
        }
    });
}

function updateStock() {
    // 入庫処理（データベース更新）
    let quantity = document.getElementById("quantity").value;

    // サーバーに数量を送信してデータベースを更新するコード（例）
    fetch('/update_stock', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            item_name: 'takoyaki', // YOLOで認識した商品名
            quantity: quantity,
            action: 'inbound' // 入庫処理
        })
    }).then(response => {
        if (response.ok) {
            alert('在庫が更新されました');
            // 入庫画面に戻るなどの処理
        } else {
            alert('エラーが発生しました');
        }
    });
}
