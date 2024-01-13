/* クエリパラメータを取得する関数 */
function getQueryParam(name) {
    var regex = new RegExp('[?&]' + name + '(=([^&#]*)|&|#|$)'),
        results = regex.exec(window.location.href);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, ' '));
}

function returnBookList(url) {
    var abcValue = getQueryParam('TOP');
    if (abcValue === '1') {
        /* BookListから遷移してきた場合、前のページに戻る */
        window.history.back();
    } else {
        /* 指定されたURLに移動する */
        abcValue = getQueryParam('MARK');
        if (abcValue === '1') {
            window.location.href = '../../BooksMark.html';
        } else {
            window.location.href = url;
        }
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
            ("00" + (now.getMonth()+1)).slice(-2) + "/" +   // 月の取り出し
            ("00" + now.getDate()).slice(-2) + " " +        // 日の取り出し        
            ("00" + now.getHours()).slice(-2) + ":" +       // 時の取り出し
            ("00" + now.getMinutes()).slice(-2) + ":" +     // 分の取り出し
            ("00" + now.getSeconds()).slice(-2);            // 秒の取り出し
}

function handleClick(book_key, title, thumb) {
    let checkbox = document.getElementById('MarkCheckbox');
    let marks = localStorage.getItem("CHAPTER_MARKER");
    if (marks != null) {
        marks = JSON.parse(marks);
    } else {
        marks = {}
    }

    if (checkbox.checked) {
        let regex = new RegExp('([^/]*/[^/]*/[^/?]*)[^/]*$'),
            results = regex.exec(window.location.href);
        if (!results || !results[1]) {
            url = '';
        } else {
            url = results[1];
        }

        marks[book_key] = { "title": title, "thumb": thumb, "url": url + '?TOP=1&MARK=1', "update": getDate() };
        localStorage.setItem("CHAPTER_MARKER", JSON.stringify(marks));
    } else {
        if (marks != null && book_key in marks) {
            delete marks[book_key];
            localStorage.setItem("CHAPTER_MARKER", JSON.stringify(marks));
        }
    }
}

/* ローカルストレージからキー=book_keyで情報を取得 */
function loadChapterKey(book_key) {
    var items = localStorage.getItem("CHAPTER_NUMBER");
    if (items != null && items !== "") {
        items = JSON.parse(items);
        if (book_key in items && "chapter" in items[book_key]) {
            var color = ["#40F0B0", "#60D090", "#80B070", "#A09050"];
            var c = 0;
            for (const item of items[book_key]["chapter"].split(' ')) {
                var tags = document.getElementsByClassName("type-" + item);
                len = tags.length | 0;
                for (i = 0; i < len; i = i + 1) {
                    tags[i].style.background = color[c];
                }
                c++;
                if (c > color.length) {
                    break;
                }
            }
        }
    }
    var checkbox = document.getElementById('MarkCheckbox');
    var marks = localStorage.getItem("CHAPTER_MARKER");
    if (marks != null && marks != "") {
        marks = JSON.parse(marks);

        if (book_key in marks) {
            /* チェックボックスをチェック */
            checkbox.checked = true;
        } else {
            /* チェックボックスのチェックを外す */
            checkbox.checked = false;
        }
    } else {
        marks = {}
    }
}
