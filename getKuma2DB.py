#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RawKuma 収集 → DB 反映ツール（Enum版 DB ライブラリ対応）
--------------------------------------------------------
役割:
- 指定 URL（https://rawkuma.com/manga/${URL}）から作品情報・チャプター・ページ情報を収集
- 収集結果を SQLite（DB ライブラリ）に保存・更新
- CLI からバッチ更新 / 新着確認 / 個別操作（ON/OFF/STOP/CLEAN/DELETE/UPDATE/TEST など）を提供

設計メモ:
- DB アクセスは先に提供した Enum 版ライブラリを使用（I/F は JST、DB 内部は UTC で保存）
- select_* の規約:
    * キーを列挙したカラムは SELECT 対象に含まれる
    * 値が None 以外のキーは WHERE 条件（AND 結合）
- 返ってくる行は「キー=Enum」の辞書（例: row[BookCol.KEY]）
- HTML 側の取得結果の日時が文字列でも受け取れるよう、可能な限り JST datetime に正規化する
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import unquote

# ===== あなたの既存モジュール =====
from Chrome import Chrome
from analyzeHTML import analyzeHTML, getGooglBooks

# ===== Enum版 DB ライブラリ =====
from DB import DB, UseFlag, CommonCol, BookCol, ChapterCol

# --------------------------------
# ログ設定（ファイル + コンソール）
# --------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(threadName)s: %(message)s",
    filename="rawkuma.log",
)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(threadName)s: %(message)s"))
logging.getLogger("").addHandler(console)

# --------------------------------
# タイムゾーン（JST 固定）
# --------------------------------
JST = timezone(timedelta(hours=9), "JST")


def func_hook(func):
    """関数呼び出しの前後にログを出すデコレータ。デバッグ容易化のための薄い仕組み。"""
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logging.info("▶ call %s", func.__name__)
            try:
                ret = await func(*args, **kwargs)
                return ret
            finally:
                logging.info("◀ return %s", func.__name__)
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logging.info("▶ call %s", func.__name__)
            try:
                ret = func(*args, **kwargs)
                return ret
            finally:
                logging.info("◀ return %s", func.__name__)
        return sync_wrapper

def func_hook(func):
    """関数呼び出しの前後にログを出すデコレータ。デバッグ容易化のための薄い仕組み。"""
    async def _awaitable(ret):
        return await ret

    def wrapper(*args, **kwargs):
        logging.info("▶ call %s", func.__name__)
        ret = func(*args, **kwargs)
        # 非同期関数なら await 完了時点で return ログを出したい場面もあるが、
        # ここでは簡易化のため呼び出し直後に return ログを出す。
        logging.info("◀ return %s", func.__name__)
        return ret
    return wrapper


# =========================================================
# 収集本体クラス
# =========================================================
class KumaFetcher:
    """
    RawKuma から情報を取得し、Enum 版 DB ライブラリに反映するクラス。
    """

    BASE_PATH = "Books"  # 画像などを保存する場合のベースディレクトリ（必要であれば使用）
    LIMITS = 1           # 併行数（Chrome ページ取得の同時リクエスト数）
    PAGE_GET_LIMITS = 1  # 併行数（Chrome ページ取得の同時リクエスト数）

    # 新規追加ブックの「強制更新起点」として使う古い日時（JST）
    ADDBOOK_DATE_JST = datetime(1900, 1, 1, 9, 0, 0, tzinfo=JST)

    def __init__(self) -> None:
        self.db = DB(logging)
        self.chrome: Optional[Chrome] = None

    # --------------- ユーティリティ ---------------

    @staticmethod
    def _normalize_to_jst_dt(v: Any) -> Optional[datetime]:
        """
        取得元の日時が文字列/naive/aware のいずれでも、できる限り JST の aware datetime に正規化する。
        - すでに tz-aware なら JST へ変換
        - naive なら JST を付与
        - 文字列は代表的なフォーマットを試行（ISO8601 / "%Y-%m-%d %H:%M:%S%z"）
        """
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.astimezone(JST) if v.tzinfo else v.replace(tzinfo=JST)
        if isinstance(v, str):
            s = v.strip()
            # ISO 風（Z を +00:00 に）
            try:
                if s.endswith("Z"):
                    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                else:
                    dt = datetime.fromisoformat(s)
                return dt.astimezone(JST) if dt.tzinfo else dt.replace(tzinfo=JST)
            except Exception:
                pass
            # 旧フォーマット "%Y-%m-%d %H:%M:%S%z"
            try:
                dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S%z")
                return dt.astimezone(JST)
            except Exception:
                pass
            # "YYYY-MM-DD" のみ → 0時で JST とみなす
            if len(s) == 10 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
                y, m, d = map(int, s.split("-"))
                return datetime(y, m, d, 0, 0, 0, tzinfo=JST)
        # パース不能は None 扱い（上流で無視/ログ）
        return None

    def _book_key_from_url(self, url: str) -> str:
        """URL 末尾の余計なスラッシュを除去し、HTML 解析器から BOOK KEY を得る。"""
        url = re.sub(r"/$", "", url)
        return analyzeHTML().getBookKey(url)

    async def _ensure_chrome(self):
        """Chrome ドライバの起動（未起動時のみ）。"""
        if self.chrome is None:
            self.chrome = Chrome(logging)
            await self.chrome.start()

    async def _shutdown_chrome(self):
        """Chrome ドライバの停止（起動していれば）。"""
        if self.chrome is not None:
            try:
                await self.chrome.stop()
            finally:
                self.chrome = None

    async def _analyze_html(self, url: str):
        """
        指定 URL の HTML を解析してオブジェクトを返す。
        - analyzeHTML(url, chrome).getHTML() を使い、内部でページ取得も行う。
        """
        await self._ensure_chrome()
        html = analyzeHTML(url, self.chrome).getHTML()
        await html.getTEXT4HTML(url)
        return html

    # --------------- 検証用（TEST） ---------------

    @func_hook
    async def testbook(self, url: str, wait: int = 300):
        """
        指定 URL をスクレイピングし、取得した情報をログに出すのみ（DB へは書かない）。
        開発・検証用。
        """
        try:
            await self._ensure_chrome()
            html = await self._analyze_html(url)
            if html is None:
                logging.info("情報が取得できませんでした。url=%s", url)
                return

            images = html.getImageList()
            urls = html.getURLlists()
            tags = html.getTAGlist()
            artists = html.getARTIST()
            titles = html.getTitle()
            post = self._normalize_to_jst_dt(html.getPostedOn())
            update = self._normalize_to_jst_dt(html.getUpdatedOn())
            thumb = html.getThumbnail()
            description = html.getDescription()
            latestpages = html.getLatestPage()

            logging.info("urls=%s", urls)
            logging.info("tags=%s", tags)
            logging.info("artists=%s", artists)
            logging.info("titles=%s", titles)
            logging.info("post(JST)=%s", post)
            logging.info("update(JST)=%s", update)
            logging.info("thumb=%s", thumb)
            logging.info("description=%s", description)
            logging.info("images=%s", images)
            logging.info("latestpages=%s", latestpages)

            books = getGooglBooks()
            title, author = books.getTitle(titles)
            logging.info("title=%s", title)
            logging.info("author=%s", author)

            # 少し待ってから終了（手動確認のため）
            logging.info("stop (sleep=%ss)", wait)
            await asyncio.sleep(wait)
        finally:
            await self._shutdown_chrome()

    # --------------- BOOK 追加 ---------------

    @func_hook
    def addbook(self, url: str, kind: str) -> None:
        """
        BOOK を新規登録（既存なら type を更新）。
        - kind: テーブル種別（A〜Z の1文字想定）
        """
        # URL 正規化
        url = re.sub(r"/$", "", url)
        logging.info("get book info URL=%s", url)

        book_key = self._book_key_from_url(url)

        # 既存検索（BOOK_TYPE も列に含める）
        result = self.db.select_book({BookCol.KEY: book_key, BookCol.TYPE: None})
        logging.info("select_book -> %s", result)

        if len(result) == 0:
            if book_key == url:
                # BOOK KEY が生成できず、URL そのものと同じ＝形式エラーと判断
                logging.error("URL 形式エラー: book_key=%s, url=%s", book_key, url)
                return

            # 新規作成。KUMA_UPDATED を古い日時に設定して、後段更新対象に含める
            self.db.insert_book(
                {
                    BookCol.KEY: book_key,
                    BookCol.URL: url,
                    BookCol.TYPE: kind.upper(),
                    CommonCol.USE_FLAG: UseFlag.UPDATE,
                    BookCol.KUMA_UPDATED: self.ADDBOOK_DATE_JST,  # JST で渡す
                }
            )
            self.db.commit()
            logging.info("insert_book OK: key=%s", book_key)
        else:
            current_type = result[0].get(BookCol.TYPE)
            if current_type != kind.upper():
                logging.info("%s は既に登録済み。TYPE %s -> %s", url, current_type, kind.upper())
                self.db.update_book(result[0][BookCol.ID], {BookCol.TYPE: kind.upper()})
                self.db.commit()
            else:
                logging.info("%s は既に登録済み（TYPE 変更なし）。", url)

    # --------------- BOOK/CHAPTER/PAGE 更新の実体 ---------------

    @func_hook
    async def updatedb2(self, row: Dict[Any, Any], ext_chapter: List[Dict[Any, Any]] = None):
        """
        1作品（BOOK）分の詳細を取得し、DB を更新する。
        - 引数 row は select_book の返り値の1行（Enum キーの dict）
        """
        book_id = row[BookCol.ID]
        book_key = row.get(BookCol.KEY, "UNKNOWN")

        # 作品ページ HTML 解析（作品全体の更新情報・チャプター一覧など）
        html = await self._analyze_html(url=row[BookCol.URL])
        if html is None:
            return

        url_tuples = html.getURLlists()    # [(chapter_url, chapter_num, chapter_date), ...]

        if ext_chapter is not None:
            # logging.info(f"{ext_chapter=}")
            # logging.info(f"{url_tuples=}")

            # すでに存在するURLをセットにしておく
            existing_urls = {u[0] for u in url_tuples}

            # ext_chapter から、まだ無いURLだけを url_tuples に追加
            for ch in ext_chapter:
                if ch["url"] not in existing_urls:
                    url_tuples.append((ch["url"], ch["num"], ch["date"]))

            # logging.info(f"{url_tuples=}")

        tags = html.getTAGlist()
        artists = html.getARTIST()
        titles = html.getTitle()
        post = self._normalize_to_jst_dt(html.getPostedOn())
        update = self._normalize_to_jst_dt(html.getUpdatedOn())
        thumb = html.getThumbnail()
        description = html.getDescription()

        # 取得更新日時と DB の更新日時が同じならスキップ
        if update == row.get(BookCol.KUMA_UPDATED):
            logging.info(f"{book_key} は更新なし {update=}")
            return

        logging.info(f"{book_key} 更新あり → 反映開始 {update=}, {row.get(BookCol.KUMA_UPDATED)=}")

        # BOOK メタの更新
        update_data = {
            BookCol.KUMA_THUMB: thumb,
            BookCol.KUMA_TITLE: ",".join(titles),
            BookCol.KUMA_AUTHOR: ",".join(artists),
            BookCol.KUMA_TAG: ",".join(tags),
            BookCol.KUMA_DESC: description,
            BookCol.KUMA_POSTED: post,     # JST datetime を渡す
            BookCol.KUMA_UPDATED: update,  # JST datetime を渡す
        }

        # タイトル未設定なら Google Books API で補完（独自実装）
        if not row.get(BookCol.TITLE):
            books = getGooglBooks()
            title, authors = books.getTitle(titles)
            update_data[BookCol.TITLE] = (
                unicodedata.normalize("NFC", title.strip()) if title else None
            )
            update_data[BookCol.AUTHOR] = ",".join(authors) if authors else None

        self.db.update_book(book_id, update_data)

        # 以降、新規チャプターとページを追加
        page_jobs: List[Dict[Any, Any]] = []
        for u in url_tuples:
            chapter_url, chapter_num, chapter_date_raw = u[0], u[1], u[2]
            chapter_key = html.getURL2Chapter(chapter_url)
            if chapter_key is None:
                continue
            if self.db.check_chapter(book_id, chapter_key):
                # 既存チャプターはスキップ（ページ追加のみしたい場合はここで select して判定してもよい）
                continue

            chapter_date = self._normalize_to_jst_dt(chapter_date_raw)

            # CHAPTER レコード作成（upsert）
            chapter_id = self.db.insert_chapter(
                {
                    ChapterCol.BOOK_ID: book_id,
                    ChapterCol.URL: chapter_url,
                    ChapterCol.KEY: chapter_key,
                    ChapterCol.NUM: chapter_num,
                    ChapterCol.DATE: chapter_date,  # JST datetime を渡す
                }
            )

            # 後続でページを取得・挿入するためのジョブ配列に登録
            page_jobs.append({ChapterCol.ID: chapter_id, ChapterCol.URL: chapter_url})

        # ページ情報の並列取得（過負荷回避のためセマフォで制限）
        sem = asyncio.Semaphore(self.PAGE_GET_LIMITS)

        async def fetch_and_insert_pages(job: Dict[Any, Any]):
            """チャプターURLを開いて画像URL一覧を取得し、PAGE テーブルに一括挿入する。"""
            chapter_url = job[ChapterCol.URL]
            html2 = await self._analyze_html(url=chapter_url)
            if html2 is None:
                return
            imgurls: List[str] = html2.getImageList()
            await asyncio.sleep(3)

            # DB.insert_page の I/F は [(chapter_id, page_url, page_num), ...]
            pagelists = [(job[ChapterCol.ID], page_url, idx + 1) for idx, page_url in enumerate(imgurls)]
            if pagelists:
                self.db.insert_page(pagelists)

        async def call(job: Dict[Any, Any]):
            async with sem:
                return await fetch_and_insert_pages(job)

        # 並列実行
        await asyncio.gather(*[call(j) for j in page_jobs])

        # すべて完了後にコミット
        self.db.commit()

    # --------------- 更新バッチ（古いもの） ---------------

    @func_hook
    async def updatedb(self) -> None:
        """
        DB 更新バッチ:
        - USE_FLAG=UPDATE で、KUMA_UPDATED が「1週間より前」の作品を更新対象に選ぶ
        - サイトで更新確認 → 差分ある作品のみ詳細更新（CHAPTER/PAGE まで）
        """
        before_week = datetime.now(JST) - timedelta(days=7)

        # 候補一覧の取得（SELECT 列は必要なものだけ列挙）
        candidates = self.db.select_book(
            {
                BookCol.URL: None,
                BookCol.KEY: None,
                BookCol.KUMA_UPDATED: before_week.date().strftime("%Y-%m-%d"),
                BookCol.TITLE: None,
                CommonCol.USE_FLAG: UseFlag.UPDATE,
            }
        )

        try:
            await self._ensure_chrome()
            await self._download(candidates)  # 差分判定 → 差分のみ updatedb2
            # 少し待って終了（Chrome 内部処理の掃除のため）
            await asyncio.sleep(2)
        finally:
            await self._shutdown_chrome()

        logging.info("updatedb 完了")
        os._exit(0)  # 既存挙動踏襲（不要なら削除可）

    # --------------- 新着系（更新リストから選別） ---------------

    async def updatenew(self, limit: int = 1) -> None:
        """
        新着（更新一覧ページから取得） + 既存 DB のうち USE_FLAG=UPDATE の作品を対象に差分更新する。
        - limit: 更新一覧ページの参照ページ数
        """
        # USE_FLAG=UPDATE の BOOK 一覧
        dbvals = self.db.select_book(
            {
                BookCol.URL: None,
                BookCol.KEY: None,
                BookCol.KUMA_UPDATED: None,
                BookCol.TITLE: None,
                CommonCol.USE_FLAG: UseFlag.UPDATE,
            }
        )

        # 更新候補キー（更新一覧ページを走査して抽出）
        latest_keys: List[str] = []
        chapter_info = {}

        @func_hook
        async def fetch_update_list(url: str):
            html = await self._analyze_html(url=url)
            # getLatestPage() が返す URL リストから book_key を抽出し、候補に追加
            latest_urls = html.getLatestPage()
            latest_keys.extend([self._book_key_from_url(u['url']) for u in latest_urls])
            for u in latest_urls:
                chapter_info[self._book_key_from_url(u['url'])] = u['chapter'] 

            await asyncio.sleep(3)

        try:
            await self._ensure_chrome()
            sem = asyncio.Semaphore(self.PAGE_GET_LIMITS)

            async def call(url: str):
                async with sem:
                    return await fetch_update_list(url)

            await asyncio.gather(*[call(url) for url in analyzeHTML().getUpdateListUrl(limit)])

            # 強制更新基準（新規追加ブックは古い日時で登録されている）
            newdate = self.ADDBOOK_DATE_JST

            # DB 側リストから「更新候補キー」または「新規追加（古い基準日）」を抽出
            targets = []
            for row in dbvals:
                if row[BookCol.KEY] in latest_keys or row.get(BookCol.KUMA_UPDATED) == newdate:
                    targets.append(row)

            await self._download(targets, chapter_info)
            await asyncio.sleep(2)
        finally:
            await self._shutdown_chrome()

        logging.info("updatenew 完了")
        os._exit(0)

    # --------------- 差分抽出 → 詳細更新 ---------------

    async def _download(self, rows: Iterable[Dict[Any, Any]], chapter_info: Dict[str, List]) -> None:
        """
        一覧（作品群）に対し、サイト側の「更新日時」を見て差分がある作品のみ updatedb2 を実行。
        """
        # 差分対象
        to_update: List[Dict[Any, Any]] = []

        @func_hook
        async def check_one(row: Dict[Any, Any]):
            html = await self._analyze_html(url=row[BookCol.URL])
            if html is None:
                return
            update_jst = self._normalize_to_jst_dt(html.getUpdatedOn())
            logging.info("更新日時 check: %s site=%s db=%s", row[BookCol.KEY], update_jst, row.get(BookCol.KUMA_UPDATED))
            if update_jst != row.get(BookCol.KUMA_UPDATED):
                to_update.append(row)

        sem = asyncio.Semaphore(self.LIMITS)

        async def call(row: Dict[Any, Any]):
            async with sem:
                return await check_one(row)

        await asyncio.gather(*[call(r) for r in rows])

        # 差分のみ詳細更新
        for r in to_update:
            logging.info("差分更新: %s", r[BookCol.KEY])
            await self.updatedb2(r, chapter_info[r[BookCol.KEY]] if r[BookCol.KEY] in chapter_info else None)

    # --------------- その他ユーティリティ ---------------

    @func_hook
    def flagset(self, url: str, kind: str) -> None:
        """
        USE_FLAG 変更（ON:UPDATE / OFF:COMPLETED / STOP:STOPPED）
        """
        book_key = self._book_key_from_url(url)
        book_id = self.db.get_book_id(book_key)
        if book_id is None:
            logging.warning("book not found: %s", book_key)
            return

        if kind.upper() == "ON":
            flag = UseFlag.UPDATE
        elif kind.upper() == "OFF":
            flag = UseFlag.COMPLETED
        elif kind.upper() == "STOP":
            flag = UseFlag.STOPPED
        else:
            logging.warning("unknown flag: %s", kind)
            return

        self.db.update_book(book_id, {CommonCol.USE_FLAG: flag})
        self.db.commit()
        logging.info("flagset OK: %s -> %s", book_key, flag.name)

    @func_hook
    def printinfo(self, url: str) -> None:
        """
        作品の基本情報を表示（簡易表示。必要に応じて拡張）
        """
        book_key = self._book_key_from_url(url)
        rows = self.db.select_book(
            {
                BookCol.URL: None,
                BookCol.KEY: book_key,
                BookCol.TYPE: None,
                BookCol.TITLE: None,
                CommonCol.USE_FLAG: None,
            }
        )
        for r in rows:
            print(f"{r[BookCol.KEY]}={r.get(BookCol.TYPE)} {r.get(BookCol.URL)} {r.get(BookCol.TITLE)}")

    @func_hook
    def clean(self, url: str) -> None:
        """
        チャプター・ページ情報の削除。
        - URL がチャプター URL の場合はそのチャプターを削除
        - BOOK URL の場合は BOOK KEY を求め、該当作品の全チャプターを削除
        """
        # チャプター URL として存在するか確認
        chapters = self.db.select_chapter({ChapterCol.URL: url})
        if len(chapters) == 0:
            # BOOK 単位で削除
            book_key = self._book_key_from_url(url)
            rows = self.db.select_book({BookCol.URL: None, BookCol.ID: None, BookCol.KEY: book_key})
            for r in rows:
                self.db.delete_chapter({ChapterCol.BOOK_ID: r[BookCol.ID]})
            self.db.commit()
            logging.info("clean(BOOK) OK: %s", book_key)
        else:
            self.db.delete_chapter({ChapterCol.ID: chapters[0][ChapterCol.ID]})
            self.db.commit()
            logging.info("clean(CHAPTER) OK: %s", url)

    @func_hook
    def delete(self, url: str) -> None:
        """
        BOOK の削除（配下の CHAPTER/PAGE は CASCADE で自動削除）
        """
        book_key = self._book_key_from_url(url)
        self.db.delete_book(book_key)
        self.db.commit()
        logging.info("delete BOOK OK: %s", book_key)

    @func_hook
    async def update(self, url: str) -> None:
        """
        指定 BOOK の強制更新（KUMA_UPDATED を古い日時に見せて差分更新させる）
        """
        book_key = self._book_key_from_url(url)
        rows = self.db.select_book(
            {
                BookCol.URL: None,
                BookCol.KEY: book_key,
                BookCol.KUMA_UPDATED: None,
                BookCol.TITLE: None,
                CommonCol.USE_FLAG: None,
            }
        )

        try:
            await self._ensure_chrome()
            for r in rows:
                logging.info("強制更新: %s (%s)", r[BookCol.KEY], r[BookCol.ID])
                # 差分判定を必ずヒットさせるため、古い KUMA_UPDATED を渡して updatedb2 を実行
                r[BookCol.KUMA_UPDATED] = self.ADDBOOK_DATE_JST
                await self.updatedb2(r)
            await asyncio.sleep(2)
        finally:
            await self._shutdown_chrome()

        logging.info("update 完了")
        os._exit(0)

    @func_hook
    def update_title(self, url: str, title: str) -> None:
        """
        BOOK タイトルの手動更新（NFC 正規化）
        """
        book_id = self.db.get_book_id(self._book_key_from_url(url))
        if book_id is None:
            logging.warning("book not found")
            return

        self.db.update_book(
            book_id, {BookCol.TITLE: unicodedata.normalize("NFC", title.strip())}
        )
        self.db.commit()
        logging.info("title updated")

    @func_hook
    def update_thumb(self, url: str, thumb: str) -> None:
        """
        BOOK タイトルの手動更新（NFC 正規化）
        """
        book_id = self.db.get_book_id(self._book_key_from_url(url))
        if book_id is None:
            logging.warning("book not found")
            return

        if thumb == "":
            self.db.update_book(book_id, {BookCol.THUMB: None})
        else:
            self.db.update_book(book_id, {BookCol.THUMB: thumb.strip()})
        self.db.commit()
        logging.info("thumb updated")

    @func_hook
    def search(self, title: str) -> None:
        """
        タイトル LIKE 検索（キーワードは NFC 正規化）
        """
        pattern = "%{}%".format(unicodedata.normalize("NFC", title.strip()))
        rows = self.db.select_book(
            {
                BookCol.URL: None,
                BookCol.KEY: None,
                BookCol.KUMA_UPDATED: None,
                BookCol.TITLE: pattern,  # LIKE 検索（DB ライブラリが自動判定）
            }
        )
        for r in rows:
            print(f"{r[BookCol.KEY]}  {r.get(BookCol.TITLE)}")


# =========================================================
# CLI エントリポイント
# =========================================================

@func_hook
def main():
    if len(sys.argv) == 1:
        # DB 更新バッチ
        app = KumaFetcher()
        asyncio.run(app.updatedb())
        app.db.close()

    elif len(sys.argv) == 2:
        cmd = sys.argv[1]
        app = KumaFetcher()
        if cmd.upper() == "NEW":
            asyncio.run(app.updatenew())
        else:
            app.printinfo(unquote(sys.argv[1]))
        app.db.close()

    elif len(sys.argv) == 3:
        url = unquote(sys.argv[1])
        arg = sys.argv[2]
        logging.info("URL=%s, ARG=%s", url, arg)

        app = KumaFetcher()
        if url.upper() == "NEW":
            asyncio.run(app.updatenew(limit=int(arg)))
        elif arg.upper() in ("ON", "OFF", "STOP"):
            app.flagset(url, arg)
        elif len(arg) == 1 and "A" <= arg[0].upper() <= "Z":
            app.addbook(url, arg)
        elif arg.upper() == "CLEAN":
            app.clean(url)
        elif arg.upper() == "DELETE":
            app.delete(url)
        elif arg.upper() == "UPDATE":
            asyncio.run(app.update(url))
        elif arg.upper() == "TEST":
            asyncio.run(app.testbook(url))
        elif url.upper() == "SEARCH":
            app.search(arg)
        else:
            logging.info("不明な引数: %s", arg)
        app.db.close()

    elif len(sys.argv) >= 4:
        url = unquote(sys.argv[1])
        arg = sys.argv[2]
        arg1 = sys.argv[3]
        logging.info("URL=%s, ARG=%s, ARG1=%s", url, arg, arg1)

        app = KumaFetcher()
        if arg.upper() == "TEST":
            asyncio.run(app.testbook(url, int(arg1)))
        elif arg.upper() == "TITLE" and len(sys.argv) == 4:
            app.update_title(url, arg1)
        elif arg.upper() == "THUMB" and len(sys.argv) == 4:
            app.update_thumb(url, arg1)
        app.db.close()


if __name__ == "__main__":
    main()
    logging.info("return main()")
