#!/usr/bin/env python3

from datetime import datetime, timedelta, timezone
import sqlite3


class DB:
    BOOK_ID = "book_id"
    BOOK_KEY = "book_key"
    BOOK_TYPE = "book_type"
    BOOK_SINGLE = "book_single"
    USE_FLAG = "use_flag"
    USE_FLAG_STOPED = 2  # 更新中止
    USE_FLAG_UPDATE = 1  # 更新中
    USE_FLAG_COMPLETED = 0  # 完了
    USE_FLAG_USED = 3  # 表示対象
    USE_FLAG_NO_USED = 4 # 表示対象外
    URL = "url"
    THUMB = "thumb"
    TITLE = "title"
    AUTHOR = "author"
    KUMA_TITLE = "kuma_title"
    KUMA_AUTHOR = "kuma_author"
    KUMA_TAG = "kuma_tag"
    KUMA_DESCRIPTION = "kuma_description"
    KUMA_POSTED = "kuma_posted"
    KUMA_UPDATED = "kuma_updated"

    CHAPTER_ID = "chapter_id"
    CHAPTER_KEY = "chapter_key"
    CHAPTER_URL = "chapter_url"
    CHAPTER_NUM = "chapter_num"
    CHAPTER_DATE = "chapter_date"
    CHAPTER_SINGLE = "chapter_single"

    PAGE_ID = "page_id"
    PAGE_URL = "page_url"
    PAGE_SINGLE = "page_single"
    PAGE = "page"

    BOOK_TABLE = "BOOK"
    CHAPTER_TABLE = "CHAPTER"
    PAGE_TABLE = "PAGE"
    dbname = "rawkuma.sqlite"

    def __init__(self, logging) -> None:
        self.conn = sqlite3.connect(self.dbname)
        self.__logging = logging
        self.__create_table_book()
        self.__create_table_chapter()
        self.__create_table_page()

    def close(self):
        self.conn.close()

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def __create_table_book(self) -> None:
        self.conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.BOOK_TABLE} (
                book_id integer PRIMARY KEY AUTOINCREMENT, -- ブックID
                book_key text not null, -- URLに含まれる識別子
                book_type char, -- タイプ
                book_single boolean NOT NULL DEFAULT TRUE, -- true : 各チャプターの1ページ目はシングルページ
                use_flag integer, -- 検出有無フラグ
                url text not null, -- URL
                title text,  -- タイトル
                author text, -- 著者
                thumb_url text, -- サムネイルURL
                kuma_author text, -- rawkuma 著者
                kuma_title text, -- rawkuma タイトル
                kuma_tag text, -- rawkuma タグ(カンマ区切り)
                kuma_description text, -- rawkuma 概要
                kuma_posted datetime, -- rawkuma 投稿日時
                kuma_updated datetime, -- rawkuma 更新日時
                created datetime default (datetime('now','localtime')), -- 作成日
                updated datetime default (datetime('now','localtime')) -- 更新日
            )
            """
        )

        self.conn.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {self.BOOK_TABLE}_key ON {self.BOOK_TABLE} (book_key)"
        )

    def insert_book(self, **kwargs) -> int | None:
        book_id = self.getBookID(kwargs[DB.BOOK_KEY])

        if book_id is not None:
            return book_id

        cur = self.conn.cursor()
        cur.executemany(
            f"""
            insert into {self.BOOK_TABLE} (
                book_key,
                book_type,
                book_single,
                use_flag, 
                url,
                title,
                author,
                thumb_url,
                kuma_title,
                kuma_author,
                kuma_tag,
                kuma_description,
                kuma_posted,
                kuma_updated
            ) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                (
                    kwargs[DB.BOOK_KEY],
                    kwargs[DB.BOOK_TYPE] if DB.BOOK_TYPE in kwargs else None,
                    kwargs[DB.BOOK_SINGLE] if DB.BOOK_SINGLE in kwargs else True,
                    kwargs[DB.USE_FLAG] if DB.USE_FLAG in kwargs else None,
                    kwargs[DB.URL],
                    kwargs[DB.TITLE] if DB.TITLE in kwargs else None,
                    kwargs[DB.AUTHOR] if DB.AUTHOR in kwargs else None,
                    kwargs[DB.THUMB] if DB.THUMB in kwargs else None,
                    kwargs[DB.KUMA_TITLE] if DB.KUMA_TITLE in kwargs else None,
                    kwargs[DB.KUMA_AUTHOR] if DB.KUMA_AUTHOR in kwargs else None,
                    kwargs[DB.KUMA_TAG] if DB.KUMA_TAG in kwargs else None,
                    (
                        kwargs[DB.KUMA_DESCRIPTION]
                        if DB.KUMA_DESCRIPTION in kwargs
                        else None
                    ),
                    kwargs[DB.KUMA_POSTED] if DB.KUMA_POSTED in kwargs else None,
                    kwargs[DB.KUMA_UPDATED] if DB.KUMA_UPDATED in kwargs else None,
                )
            ],
        )

        cur.execute(f"select last_insert_rowid() from {self.BOOK_TABLE}")
        for row in cur.fetchall():
            cur.close()
            return row[0]  # 取得したbook_idを返す

        cur.close()
        return None

    def update_book(self, book_id, **kwargs) -> None:
        cur = self.conn.cursor()

        value = []
        value.append(kwargs[DB.BOOK_TYPE]) if DB.BOOK_TYPE in kwargs else None
        value.append(kwargs[DB.BOOK_SINGLE]) if DB.BOOK_SINGLE in kwargs else None
        value.append(kwargs[DB.USE_FLAG]) if DB.USE_FLAG in kwargs else None
        value.append(kwargs[DB.URL]) if DB.URL in kwargs else None
        value.append(kwargs[DB.TITLE]) if DB.TITLE in kwargs else None
        value.append(kwargs[DB.AUTHOR]) if DB.AUTHOR in kwargs else None
        value.append(kwargs[DB.THUMB]) if DB.THUMB in kwargs else None
        value.append(kwargs[DB.KUMA_TITLE]) if DB.KUMA_TITLE in kwargs else None
        value.append(kwargs[DB.KUMA_AUTHOR]) if DB.KUMA_AUTHOR in kwargs else None
        value.append(kwargs[DB.KUMA_TAG]) if DB.KUMA_TAG in kwargs else None
        (
            value.append(kwargs[DB.KUMA_DESCRIPTION])
            if DB.KUMA_DESCRIPTION in kwargs
            else None
        )
        value.append(kwargs[DB.KUMA_POSTED]) if DB.KUMA_POSTED in kwargs else None
        value.append(kwargs[DB.KUMA_UPDATED]) if DB.KUMA_UPDATED in kwargs else None
        value.append(book_id)

        sql = f"update {self.BOOK_TABLE} set updated = datetime('now','localtime')"
        sql += ", book_type = ? " if DB.BOOK_TYPE in kwargs else ""
        sql += ", book_single = ? " if DB.BOOK_SINGLE in kwargs else ""
        sql += ", use_flag = ? " if DB.USE_FLAG in kwargs else ""
        sql += ", url = ? " if DB.URL in kwargs else ""
        sql += ", title = ? " if DB.TITLE in kwargs else ""
        sql += ", author = ? " if DB.AUTHOR in kwargs else ""
        sql += ", thumb_url = ? " if DB.THUMB in kwargs else ""
        sql += ", kuma_title = ? " if DB.KUMA_TITLE in kwargs else ""
        sql += ", kuma_author = ? " if DB.KUMA_AUTHOR in kwargs else ""
        sql += ", kuma_tag = ? " if DB.KUMA_TAG in kwargs else ""
        sql += ", kuma_description = ? " if DB.KUMA_DESCRIPTION in kwargs else ""
        sql += ", kuma_posted = ? " if DB.KUMA_POSTED in kwargs else ""
        sql += ", kuma_updated = ? " if DB.KUMA_UPDATED in kwargs else ""
        sql += " where book_id = ? "
        self.__logging.info(sql)

        cur.executemany(sql, [tuple(value)])
        cur.close()

    def select_book(self, **kwargs):
        cur = self.conn.cursor()
        sql = "select book_id "
        sql += ", book_key " if DB.BOOK_KEY in kwargs else ""
        sql += ", book_type " if DB.BOOK_TYPE in kwargs else ""
        sql += ", book_single " if DB.BOOK_SINGLE in kwargs else ""
        sql += ", use_flag " if DB.USE_FLAG in kwargs else ""
        sql += ", url " if DB.URL in kwargs else ""
        sql += ", title " if DB.TITLE in kwargs else ""
        sql += ", author " if DB.AUTHOR in kwargs else ""
        sql += ", thumb_url " if DB.THUMB in kwargs else ""
        sql += ", kuma_title " if DB.KUMA_TITLE in kwargs else ""
        sql += ", kuma_author " if DB.KUMA_AUTHOR in kwargs else ""
        sql += ", kuma_tag " if DB.KUMA_TAG in kwargs else ""
        sql += ", kuma_description " if DB.KUMA_DESCRIPTION in kwargs else ""
        sql += ", kuma_posted " if DB.KUMA_POSTED in kwargs else ""
        sql += ", kuma_updated " if DB.KUMA_UPDATED in kwargs else ""
        sql += f" from {self.BOOK_TABLE} "

        value = []
        where = [f"use_flag <> {DB.USE_FLAG_NO_USED}"]

        def xset(key, str):
            if key in kwargs and kwargs[key] is not None:
                where.append(f"{str}")
                value.append(kwargs[key])

        xset(DB.BOOK_ID, "book_id = ?")
        xset(DB.BOOK_KEY, "book_key = ?")
        xset(DB.BOOK_TYPE, "book_type = ?")
        xset(DB.USE_FLAG, "use_flag = ?")
        xset(DB.KUMA_UPDATED, "kuma_updated < ?")
        xset(DB.TITLE, "title LIKE ?")

        sql += " where {W}".format(W=" and ".join(where)) if len(where) != 0 else ""
        sql += " order by kuma_updated desc"

        self.__logging.info(sql)
        self.__logging.info(tuple(value))

        cur.execute(sql, tuple(value))

        vals = []
        for row in cur.fetchall():
            l = list(row)
            val = {DB.BOOK_ID: l.pop(0)}
            val.update({DB.BOOK_KEY: l.pop(0)}) if DB.BOOK_KEY in kwargs else ""
            val.update({DB.BOOK_TYPE: l.pop(0)}) if DB.BOOK_TYPE in kwargs else ""
            val.update({DB.BOOK_SINGLE: l.pop(0)}) if DB.BOOK_SINGLE in kwargs else ""
            val.update({DB.USE_FLAG: l.pop(0)}) if DB.USE_FLAG in kwargs else ""
            val.update({DB.URL: l.pop(0)}) if DB.URL in kwargs else ""
            val.update({DB.TITLE: l.pop(0)}) if DB.TITLE in kwargs else ""
            val.update({DB.AUTHOR: l.pop(0)}) if DB.AUTHOR in kwargs else ""
            val.update({DB.THUMB: l.pop(0)}) if DB.THUMB in kwargs else ""
            val.update({DB.KUMA_TITLE: l.pop(0)}) if DB.KUMA_TITLE in kwargs else ""
            val.update({DB.KUMA_AUTHOR: l.pop(0)}) if DB.KUMA_AUTHOR in kwargs else ""
            val.update({DB.KUMA_TAG: l.pop(0)}) if DB.KUMA_TAG in kwargs else ""
            (
                val.update({DB.KUMA_DESCRIPTION: l.pop(0)})
                if DB.KUMA_DESCRIPTION in kwargs
                else ""
            )
            if DB.KUMA_POSTED in kwargs:
                v = l.pop(0)
                val.update(
                    {
                        DB.KUMA_POSTED: (
                            datetime.strptime(v, "%Y-%m-%d %H:%M:%S%z").astimezone(
                                timezone(timedelta(hours=9))
                            )
                            if v is not None
                            else None
                        )
                    }
                )
            if DB.KUMA_UPDATED in kwargs:
                v = l.pop(0)
                val.update(
                    {
                        DB.KUMA_UPDATED: (
                            datetime.strptime(v, "%Y-%m-%d %H:%M:%S%z").astimezone(
                                timezone(timedelta(hours=9))
                            )
                            if v is not None
                            else None
                        )
                    }
                )
            vals.append(val)

        cur.close()
        return vals

    def getBookID(self, book_key) -> int | None:
        cur = self.conn.cursor()
        cur.execute(
            f"select book_id from {self.BOOK_TABLE} where book_key = ?",
            (book_key,),
        )

        for row in cur.fetchall():
            cur.close()
            return row[0]  # 取得したbook_idを返す

        cur.close()
        return None

    def check_book(self, book_key) -> bool:
        cur = self.conn.cursor()
        cur.execute(
            f"select book_id from {self.BOOK_TABLE} where book_key = ?",
            (book_key,),
        )
        lists = cur.fetchall()
        cur.close()
        return len(lists) > 0

    def delete_book(self, book_key) -> None:
        cur = self.conn.cursor()
        cur.execute(
            f"select book_id from {self.BOOK_TABLE} where book_key = ?",
            (book_key,),
        )

        for val in cur.fetchall():
            self.delete_chapter(**{DB.BOOK_ID: val[0]})

        cur.execute(
            f"delete from {self.BOOK_TABLE} where book_key = ?",
            (book_key,),
        )
        cur.close()

    def __create_table_chapter(self) -> None:
        self.conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.CHAPTER_TABLE} (
                chapter_id integer PRIMARY KEY AUTOINCREMENT, -- チャプターID
                chapter_key text not null, -- チャプターキー
                book_id integer not null, -- BOOK ID
                use_flag integer default ({DB.USE_FLAG_USED}), -- 表示対象／非対象
                chapter_single boolean DEFAULT NULL, -- true:単ページ開始, false:BOOKの設定に関係なく見開きページ、NULL:BOOKの設定に従う
                chapter_url text, -- チャプターURL
                chapter_num text, --
                chapter_date datetime, -- 更新日付
                created datetime default (datetime('now','localtime')), -- 作成日
                updated datetime default (datetime('now','localtime')) -- 更新日
            )
            """
        )

        self.conn.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {self.CHAPTER_TABLE}_key ON {self.CHAPTER_TABLE} (
                book_id, chapter_key -- チャプター識別子
            )
            """
        )

    def insert_chapter(self, **kwargs) -> int | None:
        cur = self.conn.cursor()
        cur.execute(
            f"select chapter_id from {self.CHAPTER_TABLE} where book_id = ? and chapter_key = ? ",
            (kwargs[DB.BOOK_ID], kwargs[DB.CHAPTER_KEY]),
        )

        for row in cur.fetchall():
            cur.close()
            return row[0]  # 取得したchapter_idを返す

        cur.executemany(
            f"""
            insert into {self.CHAPTER_TABLE} (
                chapter_key,
                book_id,
                chapter_url,
                chapter_num,
                chapter_date
            ) values (?,?,?,?,?)
            """,
            [
                (
                    kwargs[DB.CHAPTER_KEY],
                    kwargs[DB.BOOK_ID],
                    kwargs[DB.CHAPTER_URL],
                    kwargs[DB.CHAPTER_NUM] if DB.CHAPTER_NUM in kwargs else None,
                    kwargs[DB.CHAPTER_DATE] if DB.CHAPTER_DATE in kwargs else None,
                )
            ],
        )

        rows = cur.execute(f"select last_insert_rowid() from {self.CHAPTER_TABLE}")
        for row in rows:
            cur.close()
            return row[0]  # 取得したchapter_idを返す

        cur.close()
        return None

    def check_chapter(self, book_id, chapter_key) -> bool:
        cur = self.conn.cursor()
        cur.execute(
            f"select chapter_id from {self.CHAPTER_TABLE} where book_id = ? and chapter_key = ? ",
            (book_id, chapter_key),
        )
        lists = cur.fetchall()
        cur.close()
        return len(lists) > 0

    def select_chapter(self, **kwargs):
        cur = self.conn.cursor()

        sql = "select chapter_id "
        sql += ", book_id " if DB.BOOK_ID in kwargs else ""
        sql += ", chapter_key " if DB.CHAPTER_KEY in kwargs else ""
        sql += ", chapter_url " if DB.CHAPTER_URL in kwargs else ""
        sql += ", chapter_single " if DB.CHAPTER_SINGLE in kwargs else ""
        sql += ", chapter_num " if DB.CHAPTER_NUM in kwargs else ""
        sql += ", chapter_date " if DB.CHAPTER_DATE in kwargs else ""
        sql += f" from {self.CHAPTER_TABLE} "

        value = []
        where = [f"use_flag <> {DB.USE_FLAG_NO_USED}"]

        def xset(key, str):
            if key in kwargs and kwargs[key] is not None:
                where.append(f"{str}")
                value.append(kwargs[key])

        xset(DB.BOOK_ID, "book_id = ?")
        xset(DB.CHAPTER_ID, "chapter_id = ?")
        xset(DB.CHAPTER_KEY, "chapter_key = ?")
        xset(DB.CHAPTER_URL, "chapter_url = ?")
        xset(DB.CHAPTER_NUM, "chapter_num = ?")

        sql += " where {W}".format(W=" and ".join(where)) if len(where) != 0 else ""
        sql += " order by chapter_key"

        cur.execute(sql, tuple(value))

        vals = []
        for row in cur.fetchall():
            l = list(row)
            val = {DB.CHAPTER_ID: l.pop(0)}
            val.update({DB.BOOK_ID: l.pop(0)}) if DB.BOOK_ID in kwargs else ""
            val.update({DB.CHAPTER_KEY: l.pop(0)}) if DB.CHAPTER_KEY in kwargs else ""
            val.update({DB.CHAPTER_URL: l.pop(0)}) if DB.CHAPTER_URL in kwargs else ""
            (
                val.update({DB.CHAPTER_SINGLE: l.pop(0)})
                if DB.CHAPTER_SINGLE in kwargs
                else ""
            )
            val.update({DB.CHAPTER_NUM: l.pop(0)}) if DB.CHAPTER_NUM in kwargs else ""
            if DB.CHAPTER_DATE in kwargs:
                v = l.pop(0)
                val.update(
                    {
                        DB.CHAPTER_DATE: (
                            datetime.strptime(v, "%Y-%m-%d %H:%M:%S").astimezone(
                                timezone(timedelta(hours=9))
                            )
                            if v is not None
                            else None
                        )
                    }
                )
            vals.append(val)

        cur.close()
        return vals

    def update_chapter(self, chapter_id, **kwargs) -> None:
        """
        チャプター情報更新
        """
        cur = self.conn.cursor()

        value = []
        sqlval = [
            f"update {self.CHAPTER_TABLE} set updated = datetime('now','localtime')"
        ]

        def xset(key, column):
            if key in kwargs and kwargs[key] is not None:
                sqlval.append(f", {column} = ? ")
                value.append(kwargs[key])

        xset(DB.CHAPTER_KEY, "chapter_key")
        xset(DB.CHAPTER_URL, "chapter_url")
        xset(DB.CHAPTER_SINGLE, "chapter_single")
        xset(DB.CHAPTER_NUM, "chapter_num")
        xset(DB.CHAPTER_DATE, "chapter_date")

        value.append(chapter_id)
        sqlval.append(" where chapter_id = ? ")

        sql = "".join(sqlval)

        self.__logging.info(sql)
        self.__logging.info([tuple(value)])

        cur.executemany(sql, [tuple(value)])
        cur.close()

    def delete_chapter(self, **kwargs) -> None:
        """
        チャプター削除(配下頁込)
        kwargs[DB.BOOK_ID] 指定したbook_idのチャプター削除
        kwargs[DB.CHAPTER_ID] 指定したchapter_idのチャプター削除
        """
        cur = self.conn.cursor()

        sql = f"select chapter_id from {self.CHAPTER_TABLE} "

        value = []
        where = []

        def xset(key, str):
            if key in kwargs and kwargs[key] is not None:
                where.append(f"{str}")
                value.append(kwargs[key])

        xset(DB.BOOK_ID, "book_id = ?")
        xset(DB.CHAPTER_ID, "chapter_id = ?")

        sql += " where {W}".format(W=" and ".join(where)) if len(where) != 0 else ""

        cur.execute(sql, tuple(value))

        # 配下のページ削除
        for val in cur.fetchall():
            self.delete_page4chapter(val[0])

        sql = f"delete from {self.CHAPTER_TABLE} "
        sql += " where {W}".format(W=" and ".join(where)) if len(where) != 0 else ""

        self.__logging.info(sql)
        self.__logging.info(tuple(value))

        # チャプター削除
        cur.execute(sql, tuple(value))
        cur.close()

    def __create_table_page(self) -> None:
        """
        頁テーブル作成
        """
        self.conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.PAGE_TABLE} (
                page_id integer PRIMARY KEY AUTOINCREMENT, -- ページID
                chapter_id integer not null,
                use_flag integer default ({DB.USE_FLAG_USED}), -- 表示対象／非対象
                page integer not null, -- ページ番号
                page_url text not null, -- ページURL
                page_single boolean DEFAULT NULL, -- シングルページフラグ
                created datetime default (datetime('now','localtime')), -- 作成日
                updated datetime default (datetime('now','localtime')) -- 更新日
            )
            """
        )

        self.conn.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {self.PAGE_TABLE}_key ON {self.PAGE_TABLE} (
                chapter_id, page
            )
            """
        )

    def insert_page(self, pagelists) -> None:
        cur = self.conn.cursor()
        cur.executemany(
            f"insert into {self.PAGE_TABLE} (chapter_id, page_url, page) values (?,?,?)",
            pagelists,
        )
        cur.close()

    def select_page(self, **kwargs):
        """
        頁情報取得
        """
        cur = self.conn.cursor()

        sql = "select page_id "
        sql += ", chapter_id " if DB.CHAPTER_ID in kwargs else ""
        sql += ", page " if DB.PAGE in kwargs else ""
        sql += ", page_single " if DB.PAGE_SINGLE in kwargs else ""
        sql += ", page_url " if DB.PAGE_URL in kwargs else ""
        sql += " from {TABLE} ".format(TABLE=self.PAGE_TABLE)

        value = []
        where = [f"use_flag <> {DB.USE_FLAG_NO_USED}"]

        def xset(key, str):
            if key in kwargs and kwargs[key] is not None:
                where.append(f"{str}")
                value.append(kwargs[key])

        xset(DB.PAGE_ID, "page_id = ?")
        xset(DB.CHAPTER_ID, "chapter_id = ?")
        xset(DB.PAGE, "page = ?")
        xset(DB.PAGE_URL, "page_url = ?")
        xset(DB.PAGE_SINGLE, "page_single = ?")

        sql += " where {W}".format(W=" and ".join(where)) if len(where) != 0 else ""
        sql += " order by page"

        cur.execute(sql, tuple(value))

        vals = []
        for row in cur.fetchall():
            l = list(row)
            val = {DB.PAGE_ID: l.pop(0)}
            val.update({DB.CHAPTER_ID: l.pop(0)}) if DB.CHAPTER_ID in kwargs else ""
            val.update({DB.PAGE: l.pop(0)}) if DB.PAGE in kwargs else ""
            val.update({DB.PAGE_SINGLE: l.pop(0)}) if DB.PAGE_SINGLE in kwargs else ""
            val.update({DB.PAGE_URL: l.pop(0)}) if DB.PAGE_URL in kwargs else ""
            vals.append(val)

        cur.close()
        return vals

    def delete_page4chapter(self, chapter_id) -> None:
        """
        頁削除(チャプター単位)
        """
        cur = self.conn.cursor()

        sql = f"delete from {self.PAGE_TABLE} where chapter_id = ?"
        value = (chapter_id,)

        self.__logging.info(sql)
        self.__logging.info(tuple(value))

        cur.execute(sql, tuple(value))
        cur.close()

    def delete_page(self, page_id) -> None:
        """
        頁削除
        """
        cur = self.conn.cursor()

        sql = f"delete from {self.PAGE_TABLE} where page_id = ?"
        value = (page_id,)

        self.__logging.info(sql)
        self.__logging.info(tuple(value))

        cur.execute(sql, tuple(value))
        cur.close()

    def update_page(self, page_id, **kwargs) -> None:
        """
        頁情報更新
        """
        cur = self.conn.cursor()

        value = []
        sqlval = [f"update {self.PAGE_TABLE} set updated = datetime('now','localtime')"]

        def xset(key, column):
            if key in kwargs and kwargs[key] is not None:
                sqlval.append(f", {column} = ? ")
                value.append(kwargs[key])

        xset(DB.PAGE, "page")
        xset(DB.PAGE_SINGLE, "page_single")
        xset(DB.PAGE_URL, "page_url")

        value.append(page_id)
        sqlval.append(" where page_id = ? ")

        sql = "".join(sqlval)

        self.__logging.info(sql)
        self.__logging.info([tuple(value)])

        cur.executemany(sql, [tuple(value)])
        cur.close()
