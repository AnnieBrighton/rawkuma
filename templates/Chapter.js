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
    var imageUrls = [];
    var viewer = document.getElementById('image-viewer');
    var currentIndex = 0;

    // <td>要素をすべて取得
    var tdElements = document.querySelectorAll('#image-urls td');

    // 各<td>要素に対して処理を行う
    tdElements.forEach(function (td) {
        // 結果のオブジェクトを配列に追加
        imageUrls.push({
            single: td.getAttribute('data-single') === 'True',
            url: td.getAttribute('data-url')
        });
    });

    function getViewportSize() {
        var width = window.innerWidth || document.documentElement.clientWidth;
        var height = window.innerHeight || document.documentElement.clientHeight;
        return { width: width, height: height };
    }

    function updateImageView(count) {
        let image_left = document.querySelector('div.img-left img');
        let image_center = document.querySelector('div.img-center img');
        let image_right = document.querySelector('div.img-right img');
        let next_left = document.querySelector('div.img-left div');
        let next_center = document.querySelector('div.img-center div');
        let next_right = document.querySelector('div.img-right div');

        /* 計算されたスタイルを取得 */
        let center_element = document.querySelector('div.img-center');
        let left_element = document.querySelector('div.img-left');
        let right_element = document.querySelector('div.img-right');

        function displaySinglePage(isDisplay) {
            if (isDisplay) {
                /* 単ページ表示 */
                if (center_element.style.display !== "inline") {
                    center_element.style.display = "inline";
                    left_element.style.display = "none";
                    right_element.style.display = "none";
                }
            } else {
                /* 両開きページ表示 */
                if (center_element.style.display !== "none") {
                    center_element.style.display = "none";
                    left_element.style.display = "inline";
                    right_element.style.display = "inline";
                }
            }
        }

        /* 単ページ表示 */
        function singleView() {
            if (currentIndex === imageUrls.length) {
                /* 最終ページの次のページを表示のときはnextを表示 */
                next_center.style.visibility = "visible";
                image_center.style.visibility = "hidden";
                image_center.src = imageUrls[0]["url"];
            } else {
                next_center.style.visibility = "hidden";
                image_center.style.visibility = "visible";
                image_center.src = imageUrls[currentIndex]["url"];
            }

            displaySinglePage(true);
        }

        /* 見開きページ表示 */
        function doubleView(left_view, right_view, left_index, right_index) {
            next_left.style.visibility = left_view ? "hidden" : "visible";
            next_right.style.visibility = right_view ? "hidden" : "visible";

            image_left.style.visibility = left_view ? "visible" : "hidden";
            image_right.style.visibility = right_view ? "visible" : "hidden";

            image_left.src = imageUrls[left_index]["url"];
            image_right.src = imageUrls[right_index]["url"];

            displaySinglePage(false);
        }

        function getIndex(number) {
            var ret = 0;
            var pos = 'r';
            for (index = 0; index <= number; index++) {
                if (index < imageUrls.length && imageUrls[index]["single"]) {
                    ret = index;
                    pos = 'c';
                } else if (pos === 'r' || pos === 'c') {
                    ret = index;
                    pos = 'l';
                } else if (pos === 'l') {
                    pos = 'r';
                }
            }
            return ret;
        }

        var viewportSize = getViewportSize();

        if (viewportSize.height * 4 > viewportSize.width * 3) {
            /* 縦長 */
            if (currentIndex + count < 0 || imageUrls.length < currentIndex + count) {
                /* 表示ページが、ページ一覧外の時は処理しない。 */
                return;
            }

            currentIndex = currentIndex + count;
            singleView();
        } else {
            /* 横長 */

            if (count > 0 && currentIndex + count < imageUrls.length && !imageUrls[currentIndex]["single"]) {
                /* 現在、シングルページを表示でない場合、増加率を2倍に */
                count = count * 2;
            }

            if (currentIndex + count < 0 || imageUrls.length < currentIndex + count) {
                /* 表示ページが、ページ一覧外の時は処理しない。 */
                return;
            }

            currentIndex = getIndex(currentIndex + count);

            /* 遷移先がシングルページの場合、シングルページ表示を行う */
            if ((0 <= currentIndex && currentIndex < imageUrls.length) &&
                imageUrls[currentIndex]["single"]) {
                singleView();
                return;
            }

            if (currentIndex === imageUrls.length) {
                /* nextページを単体で表示する場合 */
                singleView();
            } else if (currentIndex + 1 === imageUrls.length) {
                /* 最終イメージとnextページを表示する場合 */
                doubleView(false, true, currentIndex, currentIndex);
            } else {
                /* 両ページの表示 */
                doubleView(true, true, currentIndex + 1, currentIndex);
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
            img.src = imageUrls[index]["url"];
        }
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
            updateImageView(1);
        } else if (touchEndX < touchStartX) {
            updateImageView(-1);
        }
    }, false);

    /* 矢印キーの処理 */
    document.addEventListener('keydown', function (event) {
        if (event.key === 'ArrowRight') updateImageView(-1);
        if (event.key === 'ArrowLeft' || event.key === ' ') updateImageView(1);
    });

    /* 画面サイズ変更を検出 */
    window.addEventListener('resize', function () {
        updateImageView(0);
    });

    /* デバイスの向きが変わった際の変更を検出 */
    window.addEventListener('orientationchange', function () {
        updateImageView(0);
    });

    let debounceTimer;
    let delayY = 0;

    window.addEventListener('wheel', function (event) {
        /* タイマーをリセットする */
        clearTimeout(debounceTimer);
        delayY = delayY + event.deltaY;

        /* 指定した時間（例：200ミリ秒）後にページ移動関数を実行 */
        debounceTimer = setTimeout(function () {
            if (delayY > 0) {
                /* ホイールを下にスクロール 次ページへ */
                updateImageView(1);
            } else if (delayY < 0) {
                /* ホイールを上にスクロール 全ページへ */
                updateImageView(-1);
            }
            delayY = 0;
        }, 200);
    });

    /* 初期画像の表示 */
    updateImageView(0);
    /* プリロード */
    preloadNextImage(0);
});
