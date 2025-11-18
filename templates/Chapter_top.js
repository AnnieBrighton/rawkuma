
// localStorage からAPIトークンを取得
function getToken() {
    const t = localStorage.getItem("API_TOKEN");
    if (!t) {
        console.error("API_TOKEN is not set. Please visit token_setup.html first.");
    }
    return t;
}

// 認証付きfetchのラッパ
async function apiFetch(path, options = {}) {
    const token = getToken();
    if (!token) {
        // トークンが未設定なら401になる前に止める
        throw new Error("No API token");
    }

    const headers = options.headers ? {...options.headers} : {};
    headers["Authorization"] = "Bearer " + token;

    // JSON投げるときは呼び出し側でContent-Typeつける。
    // ここでは勝手に上書きしない。

    const resp = await fetch(path, {
        ...options,
        headers,
    });

    return resp;
}

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

window.returnChapter = async function (url) {
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

window.handleClick = async function(book_key, title, thumb) {
    let checkbox = document.getElementById('MarkCheckbox');

    if (checkbox.checked) {
        // 追加 / 更新
        const regex = new RegExp('([^/]*/[^/]*/[^/?]*)[^/]*$');
        const results = regex.exec(window.location.href);
        let url;
        if (!results || !results[1]) {
            url = '';
        } else {
            url = results[1];
        }
        url = url + '?TOP=1&MARK=1';

        const body = {
            title: title,
            thumb: thumb,
            url: url,
            update: getDate()
        };

        const resp = await apiFetch(
            `/mankitsu_api/v1/me/bookmarks/${encodeURIComponent(book_key)}`,
            {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body)
            }
        );
        if (!resp.ok) {
            console.error("Failed to PUT bookmark", resp.status);
        }        
    } else {
        // 削除
        const resp = await apiFetch(
            `/mankitsu_api/v1/me/bookmarks/${encodeURIComponent(book_key)}`,
            { method: "DELETE" }
        );
        if (!resp.ok) {
            console.error("Failed to DELETE bookmark", resp.status);
        }
    }
}

/* ローカルストレージからキー=book_keyで情報を取得 */
async function loadChapterKey(book_key) {
    const resp = await apiFetch(
        `/mankitsu_api/v1/me/chapters/${encodeURIComponent(book_key)}`,
        { method: "GET" }
    );

    if (resp.ok) {
        const data = await resp.json();
        const chapterStr = data.chapter;
        if (chapterStr) {

            const colorPalette = ["#40F0B0", "#60D090", "#80B070", "#A09050"];
            let ci = 0;
            for (const chapterId of chapterStr.split(" ")) {
                // そのchapterIdに対応する要素群へ色付け
                const tags = document.getElementsByClassName("type-" + chapterId);
                for (let i = 0; i < tags.length; i++) {
                    tags[i].style.background = colorPalette[ci];
                }
                ci++;
                if (ci >= colorPalette.length) {
                    break;
                }
            }
        }
    }

    var checkbox = document.getElementById('MarkCheckbox');
    const resp1 = await apiFetch(`/mankitsu_api/v1/me/bookmarks`, { method: "GET" });
    if (!resp1.ok) {
        console.error("Failed to fetch bookmarks", resp1.status);
        checkbox.checked = false;
        return;
    }
    const data = await resp1.json();
    // dataは { "book_key": {title,thumb,url,update}, ... }
    checkbox.checked = !!data[book_key];
}
