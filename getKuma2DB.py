#!/usr/bin/env python3
#
# https://rawkuma.com/manga/${URL} より以下の情報を取得
#
# - URL
# - タイトル
# - 著者
# - チャプタ番号(nnnn.n)
# -
# - Posted On
# - Updated On

import asyncio
import os
from datetime import datetime, timedelta, timezone
import logging
import re
import sys
from urllib.parse import unquote
from Chrome import Chrome
import unicodedata

from DB import DB
from analyzeHTML import getGooglBooks, analyzeHTML

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(threadName)s: %(message)s",
    filename="rawkuma.log",
)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter("%(asctime)s %(threadName)s: %(message)s"))
logging.getLogger("").addHandler(console)

#


def func_hook(func):
    def wrapper(*arg, **kwargs):
        logging.info("call %s" % (func.__name__))
        ret = func(*arg, **kwargs)
        logging.info("return %s" % (func.__name__))
        return ret

    return wrapper


class getKuma2DB:
    BASE_PATH = "Books"
    ADDBOOK_DATE = "1900-01-01 00:00:00+09:00"
    LIMITS = 15

    def __init__(self) -> None:
        self.db = DB(logging)
        self.chrome = None

    @func_hook
    async def testbook(self, url, wait=300):
        self.chrome = Chrome(logging)

        await self.chrome.start()

        html = await self.analyzeHTML(url=url)
        if html is None:
            logging.info("情報が取得できませんでした。{url}".format(url=url))
            return

        images = html.getImageList()

        urls = html.getURLlists()

        tags = html.getTAGlist()
        artists = html.getARTIST()
        titles = html.getTitle()
        post = html.getPostedOn()
        update = html.getUpdatedOn()
        thumb = html.getThumbnail()
        description = html.getDescription()
        latespages = html.getLatestPage()

        logging.info("urls={urls}".format(urls=urls))
        logging.info("tags={tags}".format(tags=tags))
        logging.info("artists={artists}".format(artists=artists))
        logging.info("titles={titles}".format(titles=titles))
        logging.info("post={post}".format(post=post))
        logging.info("update={update}".format(update=update))
        logging.info("thumb={thumb}".format(thumb=thumb))
        logging.info("description={description}".format(description=description))
        logging.info("images={images}".format(images=images))
        logging.info("latespages={latespages}".format(latespages=latespages))

        books = getGooglBooks()
        title, author = books.getTitle(titles)
        logging.info("title={title}".format(title=title))
        logging.info("author={author}".format(author=author))

        logging.info("stop")
        await asyncio.sleep(wait)

        await self.chrome.stop()

    @func_hook
    def addbook(self, url, type) -> None:
        # urlが最後/で終わる場合、/を取り除く
        url = re.sub(r"/$", "", url)

        # チャプター情報取得
        logging.info("get book info {URL}".format(URL=url))

        book_key = self.get_book_key(url)

        result = self.db.select_book(**{DB.BOOK_KEY: book_key, DB.BOOK_TYPE: None})
        logging.info(result)

        if len(result) == 0:
            if book_key == url:
                # ダウンロードできるURLでないため終了
                logging.error(
                    "URL形式エラー:book_key={key}, url={url}".format(key=book_key, url=url)
                )
                return

            self.db.insert_book(
                **{
                    DB.BOOK_KEY: book_key,
                    DB.URL: url,
                    DB.BOOK_TYPE: type.upper(),
                    DB.USE_FLAG: DB.USE_FLAG_UPDATE,
                    DB.KUMA_UPDATED: self.ADDBOOK_DATE,
                }
            )
            self.db.commit()
        else:
            if result[0][DB.BOOK_TYPE] != type.upper():
                logging.info(
                    "{URL} はすでに登録済み。TYPE {OLD} -> {NEW}".format(
                        URL=url, OLD=result[0][DB.BOOK_TYPE], NEW=type.upper()
                    )
                )
                self.db.update_book(
                    result[0][DB.BOOK_ID], **{DB.BOOK_TYPE: type.upper()}
                )
                self.db.commit()

                # チャプター格納ディレクトリ作成
                os.makedirs(
                    os.path.join(self.BASE_PATH, "img{TYPE}".format(TYPE=type.upper())),
                    exist_ok=True,
                )

                #
                olddir = os.path.join(
                    self.BASE_PATH,
                    "img{TYPE}".format(TYPE=result[0][DB.BOOK_TYPE]),
                    result[0][DB.BOOK_KEY],
                )
                if os.path.isdir(olddir):
                    newdir = os.path.join(
                        self.BASE_PATH,
                        "img{TYPE}".format(TYPE=type.upper()),
                        result[0][DB.BOOK_KEY],
                    )

                    logging.info("{OLD} -> {NEW}".format(OLD=olddir, NEW=newdir))
                    os.rename(olddir, newdir)

            else:
                logging.info("{URL} はすでに登録済み。".format(URL=url))

    def close(self) -> None:
        self.db.close()

    @func_hook
    async def analyzeHTML(self, url):
        logging.info("get book info {URL}".format(URL=url))
        html = analyzeHTML(url, self.chrome).getHTML()

        await html.getTEXT4HTML(url)

        return html

    # ダウンロード
    @func_hook
    async def updatedb2(self, val):
        """ """
        book_id = val[DB.BOOK_ID]
        book_key = val[DB.BOOK_KEY]

        # チャプター情報取得
        html = await self.analyzeHTML(url=val[DB.URL])
        if html is None:
            return

        urls = html.getURLlists()

        tags = html.getTAGlist()
        artists = html.getARTIST()
        titles = html.getTitle()
        post = html.getPostedOn()
        update = html.getUpdatedOn()
        thumb = html.getThumbnail()
        description = html.getDescription()

        if update == val[DB.KUMA_UPDATED]:
            # 取得更新日付とDB上の更新日付が同じ
            logging.info("{BOOK}は更新が無い".format(BOOK=book_key))
            return

        logging.info("{BOOK}更新".format(BOOK=book_key))

        data = {
            DB.THUMB: thumb,
            DB.KUMA_TITLE: ",".join(titles),
            DB.KUMA_AUTHOR: ",".join(artists),
            DB.KUMA_TAG: ",".join(tags),
            DB.KUMA_DESCRIPTION: description,
            DB.KUMA_POSTED: post,
            DB.KUMA_UPDATED: update,
        }

        if val[DB.TITLE] is None or val[DB.TITLE] == "":
            books = getGooglBooks()
            title, author = books.getTitle(titles)
            data[DB.TITLE] = (
                unicodedata.normalize("NFC", title.strip())
                if title is not None
                else None
            )
            data[DB.AUTHOR] = ",".join(author)

        self.db.update_book(book_id, **data)

        page_vals = []
        for url in urls:
            # ファイルを展開するパスを作成 (最後に / を含む)
            # URLからチャプター番号を生成
            chapter = html.getURL2Chapter(url[0])
            if chapter is None:
                continue

            if self.db.check_chapter(book_id, chapter):
                # logging.info('すでに存在:{URL}'.format(URL=url[0]))
                continue

            # チャプターレコード作成
            data = {
                DB.BOOK_ID: book_id,
                DB.CHAPTER_URL: url[0],
                DB.CHAPTER_KEY: chapter,
                DB.CHAPTER_NUM: url[1],
                DB.CHAPTER_DATE: url[2],
            }
            chapter_id = self.db.insert_chapter(**data)

            page_vals.append({DB.CHAPTER_ID: chapter_id, DB.CHAPTER_URL: url[0]})

        @func_hook
        async def getChapterHTML(val):
            url = val[DB.CHAPTER_URL]
            # ページ情報取得
            html = await self.analyzeHTML(url=val[DB.CHAPTER_URL])
            if html is None:
                return

            imgurls = html.getImageList()

            # ページ登録情報作成
            pagelists = []
            for page, page_url in enumerate(imgurls):
                pagelists.append((val[DB.CHAPTER_ID], page_url, page + 1))

            # ページレコード作成
            self.db.insert_page(pagelists)

        sem = asyncio.Semaphore(self.LIMITS)

        async def call(val):
            async with sem:
                return await getChapterHTML(val)

        await asyncio.gather(*[call(val) for val in page_vals])

        self.db.commit()

        return

    async def download(self, vals) -> None:
        newvals = []

        @func_hook
        async def getHTML(val):
            html = await self.analyzeHTML(url=val[DB.URL])
            if html is None:
                return

            update = html.getUpdatedOn()
            logging.info(f"更新日時 {val[DB.BOOK_KEY]} {update} {val[DB.KUMA_UPDATED]}")

            # DBの更新日時とチャプターページの更新日時が異なるブックを更新対象に追加
            if update != val[DB.KUMA_UPDATED]:
                newvals.append(val)

        sem = asyncio.Semaphore(self.LIMITS)

        async def call(val):
            async with sem:
                return await getHTML(val)

        await asyncio.gather(*[call(val) for val in vals])

        for val in newvals:
            logging.info(f"新規更新 {val[DB.BOOK_KEY]}")
            await self.updatedb2(val)

    @func_hook
    async def updatedb(self) -> None:
        """DB更新"""
        # DBの更新対象を、USEフラグがONで、かつ、更新日が7日より前のBOOK
        before_week = datetime.now(timezone(timedelta(hours=9), "JST")) - timedelta(
            days=7
        )
        vals = self.db.select_book(
            **{
                DB.URL: None,
                DB.BOOK_KEY: None,
                DB.KUMA_UPDATED: before_week.date().strftime("%Y-%m-%d"),
                DB.TITLE: None,
                DB.USE_FLAG: DB.USE_FLAG_UPDATE,
            }
        )

        self.chrome = Chrome(logging)
        await self.chrome.start()

        await self.download(vals)

        await asyncio.sleep(10)

        await self.chrome.stop()

    async def updatenew(self, limit=2) -> None:
        # DBの更新対象を、USEフラグがONのBOOK
        dbvals = self.db.select_book(
            **{
                DB.URL: None,
                DB.BOOK_KEY: None,
                DB.KUMA_UPDATED: None,
                DB.TITLE: None,
                DB.USE_FLAG: DB.USE_FLAG_UPDATE,
            }
        )
        vals = []
        newvals = []
        self.chrome = Chrome(logging)
        await self.chrome.start()

        @func_hook
        async def getHTML(url):
            # 検索ページを取得
            html = await self.analyzeHTML(url=url)

            # 検索ページの情報を取り出し
            update = html.getLatestPage()

            vals.extend([self.get_book_key(url) for url in update])

        sem = asyncio.Semaphore(self.LIMITS)

        async def call(url):
            async with sem:
                return await getHTML(url)

        await asyncio.gather(
            *[call(url) for url in analyzeHTML().getUpdateListUrl(limit)]
        )

        # 新規追加ブックの更新時刻
        newdate = datetime.strptime(
            self.ADDBOOK_DATE, "%Y-%m-%d %H:%M:%S%z"
        ).astimezone(timezone(timedelta(hours=9)))

        for val in dbvals:
            # 更新検索画面、5画面分のブック、または、新規追加ブックを更新確認対象にする
            if val[DB.BOOK_KEY] in vals or val[DB.KUMA_UPDATED] == newdate:
                newvals.append(val)

        await self.download(newvals)

        await asyncio.sleep(10)

        await self.chrome.stop()

    # URLからBOOK KEYを取得
    def get_book_key(self, url) -> str:
        return analyzeHTML().getBookKey(url)

    # flag set
    @func_hook
    def flagset(self, url, type) -> None:
        """USEフラグ変更
        Args:
            url (_type_): BOOK URL
            type (_type_): 変更後のUSEフラグ
        """
        book_key = self.get_book_key(url)
        book_id = self.db.getBookID(book_key)

        if type.upper() == "ON":
            flag = DB.USE_FLAG_UPDATE
        elif type.upper() == "OFF":
            flag = DB.USE_FLAG_COMPLETED
        elif type.upper() == "STOP":
            flag = DB.USE_FLAG_STOPED
        else:
            return

        self.db.update_book(book_id, **{DB.USE_FLAG: flag})

        self.db.commit()

    @func_hook
    def printinfo(self, url) -> None:
        """情報出力
        Args:
            url (_type_): BOOK URL
        """
        book_key = self.get_book_key(url)

        vals = self.db.select_book(
            **{
                DB.URL: None,
                DB.BOOK_KEY: book_key,
                DB.BOOK_TYPE: None,
                DB.TITLE: None,
                DB.USE_FLAG: None,
            }
        )
        for val in vals:
            print(
                f"{val[DB.BOOK_KEY]}={val[DB.BOOK_TYPE]} {val[DB.URL]} {val[DB.TITLE]}"
            )

    @func_hook
    def clean(self, url) -> None:
        """チャプター、ページ情報削除
        Args:
            url (_type_): BOOK URL
        """

        # 指定URLがチャプターテーブルに存在するか確認
        chapters = self.db.select_chapter(**{DB.CHAPTER_URL: url})

        if len(chapters) == 0:
            # チャプターテーブルになければ、ブック指定として処理
            book_key = self.get_book_key(url)
            vals = self.db.select_book(
                **{DB.URL: None, DB.BOOK_ID: None, DB.BOOK_KEY: book_key}
            )
            for val in vals:
                self.db.delete_chapter(**{DB.BOOK_ID: val[DB.BOOK_ID]})
            self.db.commit()
        else:
            self.db.delete_chapter(**{DB.CHAPTER_ID: chapters[0][DB.CHAPTER_ID]})
            self.db.commit()

    @func_hook
    def delete(self, url) -> None:
        """BOOK削除
        Args:
            url (_type_): BOOK URL
        """
        book_key = self.get_book_key(url)
        self.db.delete_book(book_key)
        self.db.commit()

    @func_hook
    async def update(self, url) -> None:
        """BOOK情報更新
        Args:
            url (_type_): BOOK URL
        """
        book_key = self.get_book_key(url)
        vals = self.db.select_book(
            **{
                DB.URL: None,
                DB.BOOK_KEY: book_key,
                DB.KUMA_UPDATED: None,
                DB.TITLE: None,
                DB.USE_FLAG: None,
            }
        )

        self.chrome = Chrome(logging)
        await self.chrome.start()

        for val in vals:
            logging.info(f"新規更新 {val[DB.BOOK_ID]} {val[DB.BOOK_KEY]}")
            val[DB.KUMA_UPDATED] = self.ADDBOOK_DATE
            await self.updatedb2(val)

        await asyncio.sleep(10)
        await self.chrome.stop()

    @func_hook
    def update_title(self, url, title) -> None:
        """TITLE情報更新
        Args:
            url (_type_): BOOK URL
        """
        book_id = self.db.getBookID(self.get_book_key(url))

        self.db.update_book(
            book_id, **{DB.TITLE: unicodedata.normalize("NFC", title.strip())}
        )

        self.db.commit()

    @func_hook
    def search(self, title) -> None:
        """TITLE検索
        Args:
            title : 検索文字列
        """
        vals = self.db.select_book(
            **{
                DB.URL: None,
                DB.BOOK_KEY: None,
                DB.KUMA_UPDATED: None,
                DB.TITLE: "%{STR}%".format(
                    STR=unicodedata.normalize("NFC", title.strip())
                ),
            }
        )

        for val in vals:
            print("{KEY}  {TITLE}".format(KEY=val[DB.BOOK_KEY], TITLE=val[DB.TITLE]))


#
# メイン
#


@func_hook
def main():
    if len(sys.argv) == 1:
        # DB更新実行
        kuma = getKuma2DB()
        asyncio.run(kuma.updatedb())
        kuma.close()

    elif len(sys.argv) == 2:
        cmd = sys.argv[1]
        kuma = getKuma2DB()
        if cmd.upper() == "NEW":
            asyncio.run(kuma.updatenew())
        else:
            kuma.printinfo(unquote(sys.argv[1]))
        kuma.close()

    elif len(sys.argv) == 3:
        url = unquote(sys.argv[1])
        type = sys.argv[2]
        logging.info("URL={URL}, TYPE={TYPE}".format(URL=url, TYPE=type))

        kuma = getKuma2DB()
        if url.upper() == "NEW":
            asyncio.run(kuma.updatenew(limit=int(type)))
        elif type.upper() == "ON" or type.upper() == "OFF" or type.upper() == "STOP":
            # USEフラグ変更
            kuma.flagset(url, type)
        elif len(type) == 1 and "A" <= type[0].upper() and type[0].upper() <= "Z":
            # テーブル登録
            kuma.addbook(url, type)
        elif type.upper() == "CLEAN":
            kuma.clean(url)
        elif type.upper() == "DELETE":
            kuma.delete(url)
        elif type.upper() == "UPDATE":
            asyncio.run(kuma.update(url))
        elif type.upper() == "TEST":
            asyncio.run(kuma.testbook(url))
        elif url.upper() == "SEARCH":
            kuma.search(type)
        else:
            logging.info("{TYPE} error".format(TYPE=type))
        kuma.close()

    elif len(sys.argv) >= 4:
        url = unquote(sys.argv[1])
        type = sys.argv[2]
        arg1 = sys.argv[3]
        logging.info(
            "URL={URL}, TYPE={TYPE}, ARG1={ARG1}".format(URL=url, TYPE=type, ARG1=arg1)
        )

        kuma = getKuma2DB()
        if type.upper() == "TEST":
            asyncio.run(kuma.testbook(url, int(arg1)))
        elif type.upper() == "TITLE" and len(sys.argv) == 4:
            kuma.update_title(url, arg1)


if __name__ == "__main__":
    main()
