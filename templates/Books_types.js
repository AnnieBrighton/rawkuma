

/*  */
async function getBooksMarkInfo() {
    const token = localStorage.getItem("API_TOKEN");
    if (!token) {
        console.warn("No API_TOKEN in localStorage");
        return null;
    }
    const resp = await fetch("/mankitsu_api/v1/me/bookmarks", {
        headers: {
            "Authorization": "Bearer " + token
        }
    });
    if (!resp.ok) {
        console.error("Failed:", resp.status);
        return null;
    }
    return await resp.json(); // { book_key: {...}, ... }
}


/* ブックマーク情報があれば、Menuにブックマークを表示 */
async function InsertBooksMarkMenu() {
    let menu = document.getElementById("BooksMark");
    if (menu != null) {
        /* すでにマークを表示済み */
        return;
    }
    let marks = await getBooksMarkInfo();
    if (Object.keys(marks).length === 0) {
        return;
    }
    let row = document.getElementById("myRow");
    row.insertAdjacentHTML("beforeend", '<a href="BooksMark.html" id="BooksMark">マーク</a>');
}


async function CreateBooksMarkPage() {
    let marker_list = await getBooksMarkInfo();
    if (marker_list == null) {
        return;
    }
    /* ①要素を変数保持 */
    let marks = Object.keys(marker_list).map(function(key) {
        return marker_list[key];
    /* ②dateでソート */
    }).sort(function(a, b) {
        return (a.update < b.update) ? -1 : 1;  /* オブジェクトの昇順ソート */
    });                    

    for (let key in marks) {
        let title = marks[key]["title"];
        let thumb = marks[key]["thumb"];
        let url = marks[key]["url"];

        let row = document.getElementById("myBooks");
        row.insertAdjacentHTML("afterbegin",
            '<div class="bs"><div class="thumbnail-list">' + 
                '<a href="' + url + '">' +
                    '<div class="thumbnail"><img src="' + thumb + '"></div>' +
                    '<div class="title">' + title + '</div>' +
                '</a>' +
            '</div></div>');
    }
}


async function MoveMenu(offset) {
    /* "myRow"の配下の<a>タグをすべて取得 */
    var anchorElements = document.getElementById("myRow").getElementsByTagName("a");

    for (var i = 0; i < anchorElements.length; i++) {
        var anchor = anchorElements[i];
        /* href属性がない場合 */
        if (!anchor.hasAttribute('href')) {
            /* 一つ前後の<a>タグのインデックスを計算 */
            let prevIndex = (i + offset + anchorElements.length) % anchorElements.length;
    
            /* 一つ前後の<a>タグを取得 */
            let prevAnchor = anchorElements[prevIndex];
            let hrefToOpen = prevAnchor.getAttribute('href');
    
            /* hrefを開く（ページ遷移） */
            window.location.href = hrefToOpen;
        }
    }
}


async function viewLeftMenu() {
    await MoveMenu(-1);
}


async function viewRightMenu() {
    await MoveMenu(1);
}


document.addEventListener('DOMContentLoaded', () => {
    /* 矢印キーの処理 */
    window.addEventListener('keyup', async (event) => {
        if (event.key === 'ArrowRight') await viewRightMenu();
        if (event.key === 'ArrowLeft' || event.key === ' ') await viewLeftMenu();
    });

    /* タッチスワイプ操作の処理 */
    var touchStartX = 0;
    var touchEndX = 0;

    /* タッチ開始 */
    window.addEventListener('touchstart', async (event) => {
        console.log('touchstart');
        touchStartX = event.changedTouches[0].screenX;
    });

    /*  */
    window.addEventListener('touchend', async (event) => {
        console.log('touchend');
        touchEndX = event.changedTouches[0].screenX;
        if (Math.abs(touchEndX - touchStartX) > 100) {
            if (touchEndX > touchStartX) {
                await viewRightMenu();
            } else if (touchEndX < touchStartX) {
                await viewLeftMenu();
            }
        }
    });

    /* ブックマーク */
    (async () => { await InsertBooksMarkMenu(); })();
});
