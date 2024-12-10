// カメラ起動ボタン
document.getElementById('startCameraBtn').addEventListener('click', function() {
    startCamera();
});

// 出庫の数量確定ボタン
document.getElementById('confirmQuantityBtn').addEventListener('click', function() {
    const quantity = document.getElementById('quantityInput').value;
    const productName = document.getElementById('detectedProductName').textContent;
    updateStock('outbound', productName, quantity);
});

// メニューに戻るボタン
document.getElementById('backBtn').addEventListener('click', function() {
    window.location.href = 'menu.html';
});

// カメラ起動処理
async function startCamera() {
    const video = document.getElementById('video');
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;

    // カメラ表示
    document.getElementById('cameraContainer').style.display = 'block';

    // YOLO認識処理を開始
    detectProduct(video);
}

// 製品認識
async function detectProduct(video) {
    const model = await tf.loadGraphModel('model.json');  // モデルのロード

    const predictions = await model.detect(video);
    if (predictions.length > 0) {
        const detectedProduct = predictions[0].class;  // 最初に認識された物体を使用
        document.getElementById('detectedProductName').textContent = detectedProduct;
        document.getElementById('productDetected').style.display = 'block';
    }
}

// 在庫更新処理
function updateStock(type, productName, quantity) {
    fetch(`/update_stock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, productName, quantity })
    })
    .then(response => response.json())
    .then(data => {
        alert('在庫が更新されました');
        window.location.href = 'menu.html';  // メニューに戻る
    });
}
