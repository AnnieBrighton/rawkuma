/* クエリパラメータを取得する関数 */
function getQueryParam(name) {
    var regex = new RegExp('[?&]' + name + '(=([^&#]*)|&|#|$)'),
        results = regex.exec(window.location.href);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, ' '));
}

function returnBookList(url) {
    var abcValue = getQueryParam('MARK');
    if (abcValue === '1') {
        window.location.href = url + "?MARK=1";
    } else {
        window.location.href = url;
    }
    /* デフォルトのaタグの動作を停止する */
    return false;
}

function returnChapter(url) {
    var abcValue = getQueryParam('MARK');
    if (abcValue === '1') {
        window.location.href = url + '?MARK=1';
    } else {
        window.location.href = url;
    }
    /* デフォルトのaタグの動作を停止する */
    return false;
}

function getDate() {
    var now = new Date();
    return ("0000" + now.getFullYear()).slice(-4) + "/" + // 年の取り出し
        ("00" + (now.getMonth() + 1)).slice(-2) + "/" +   // 月の取り出し
        ("00" + now.getDate()).slice(-2) + " " +        // 日の取り出し        
        ("00" + now.getHours()).slice(-2) + ":" +       // 時の取り出し
        ("00" + now.getMinutes()).slice(-2) + ":" +     // 分の取り出し
        ("00" + now.getSeconds()).slice(-2);            // 秒の取り出し
}

function saveChapterKey(book_key, chapter_key) {
    /* 現在閲覧中のチャプターをキーに保存する。 */
    var items = localStorage.getItem("CHAPTER_NUMBER");
    if (items == null || items === "") {
        items = {};
    } else {
        items = JSON.parse(items);
    }

    var before_chapter = chapter_key;
    if (book_key in items && "chapter" in items[book_key] && items[book_key]["chapter"] != null) {
        let c = 1;
        for (const item of items[book_key]["chapter"].split(' ')) {
            if (before_chapter != item && c < 3) {
                before_chapter += ' ' + item;
            }
            c++;
        }
        items[book_key]["chapter"] = before_chapter;
    } else {
        let minKey = null;
        let minValue = 999999999;
        let maxValue = 0;

        for (let key in items) {
            if (items[key].number < minValue) {
                minValue = items[key].number;
                minKey = key;
            }
            if (items[key].number > maxValue) {
                maxValue = items[key].number;
            }
        }
        if (Object.keys(items).length > 300) {
            delete items[minKey];
        }
        items[book_key] = { "number": maxValue + 1, "chapter": before_chapter };
    }

    localStorage.setItem("CHAPTER_NUMBER", JSON.stringify(items));

    /* マーカー情報の更新時間を更新  */
    var marks = localStorage.getItem("CHAPTER_MARKER");
    if (marks != null && marks != "") {
        marks = JSON.parse(marks);
        if (book_key in marks) {
            marks[book_key]["update"] = getDate();
            localStorage.setItem("CHAPTER_MARKER", JSON.stringify(marks));
        }
    }
}

function updateProgressBar(progress) {
    var progressBar = document.getElementById("myProgressBar");
    progressBar.style.width = progress + '%';
}

document.addEventListener('DOMContentLoaded', function () {
    var imageUrls = Array.from(document.querySelectorAll('#image-urls td')).map(td => td.textContent.replace(/\r\n|\n|\r/gm, "").trim());
    var viewer = document.getElementById('image-viewer');
    var currentIndex = 0;

    function updateImageView(count) {
        let image_left = document.querySelector('div.img-left img');
        let image_center = document.querySelector('div.img-center img');
        let image_right = document.querySelector('div.img-right img');
        let next_left = document.querySelector('div.img-left div');
        let next_center = document.querySelector('div.img-center div');
        let next_right = document.querySelector('div.img-right div');

        /* 計算されたスタイルを取得 */
        let style_center = window.getComputedStyle(document.querySelector('div.img-center'));

        let index = currentIndex;

        /* centerのdisplayがnoneの場合、左右表示と判断 */
        /* 画像数を二枚、右側を偶数ページに設定 */
        if (style_center.display == "none") {
            count = count * 2;
            index = index - (index % 2)
        }

        if (0 <= index + count && index + count <= imageUrls.length) {
            if (index + count == imageUrls.length) {
                currentIndex = index + count;

                next_center.style.visibility = "visible";
                image_center.style.visibility = "hidden";
                image_center.src = imageUrls[0];

                next_left.style.visibility = "hidden";
                next_right.style.visibility = "visible";

                image_left.style.visibility = "hidden";
                image_right.style.visibility = "hidden";

                image_left.src = imageUrls[0];
                image_right.src = imageUrls[0];

            } else if (count == 2 && index + count + 1 == imageUrls.length) {
                currentIndex = index + count;

                next_center.style.visibility = "hidden";
                image_center.style.visibility = "visible";
                image_center.src = imageUrls[0];

                next_left.style.visibility = "visible";
                next_right.style.visibility = "hidden";

                image_left.style.visibility = "hidden";
                image_right.style.visibility = "visible";

                image_left.src = imageUrls[currentIndex];
                image_right.src = imageUrls[currentIndex];

            } else {
                currentIndex = index + count;

                next_center.style.visibility = "hidden";
                image_center.style.visibility = "visible";
                image_center.src = imageUrls[currentIndex];

                next_left.style.visibility = "hidden";
                next_right.style.visibility = "hidden";

                image_left.style.visibility = "visible";
                image_right.style.visibility = "visible";

                image_left.src = imageUrls[(currentIndex + 1) % imageUrls.length];
                image_right.src = imageUrls[currentIndex];

            }
        }
    }

    /* 次に表示する画像を先読み */
    function preloadNextImage(index) {
        if (index < imageUrls.length) {
            var img = new Image();
            img.onload = function () {
                updateProgressBar((index + 1) * 100 / imageUrls.length);
                /* 読み込み完了後に、次の画像読み込みを行う */
                preloadNextImage(index + 1);
            };
            img.src = imageUrls[index];
        }
    }

    function showNextImage() {
        updateImageView(1);
    }

    function showPreviousImage() {
        updateImageView(-1);
    }

    /* タッチスワイプ操作の処理 */
    var touchStartX = 0;
    var touchEndX = 0;

    viewer.addEventListener('touchstart', function (event) {
        touchStartX = event.changedTouches[0].screenX;
    }, false);

    viewer.addEventListener('touchend', function (event) {
        touchEndX = event.changedTouches[0].screenX;
        if ((touchEndX > touchStartX) || Math.abs(touchEndX - touchStartX) < 10) {
            showNextImage();
        } else if (touchEndX < touchStartX) {
            showPreviousImage();
        }
    }, false);

    /* 矢印キーの処理 */
    document.addEventListener('keydown', function (event) {
        if (event.key === 'ArrowRight') showPreviousImage();
        if (event.key === 'ArrowLeft' || event.key === ' ') showNextImage();
    });

    /* 初期画像の表示 */
    updateImageView(0);
    /* プリロード */
    preloadNextImage(0);
});
