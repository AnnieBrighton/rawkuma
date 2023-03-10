#!/usr/bin/env python3

from datetime import datetime, timedelta, timezone
import sqlite3

class DB:
    BOOK_ID = 'book_id'
    BOOK_KEY = 'book_key'
    BOOK_TYPE = 'book_type'
    USE_FLAG = 'use_flag'
    USE_FLAG_ON = 1
    USE_FLAG_OFF = 0
    URL = 'url'
    THUMB = 'thumb'
    TITLE = 'title'
    AUTHOR = 'author'
    KUMA_TITLE = 'kuma_title'
    KUMA_AUTHOR = 'kuma_author'
    KUMA_TAG = 'kuma_tag'
    KUMA_DESCRIPTION = 'kuma_description'
    KUMA_POSTED = 'kuma_posted'
    KUMA_UPDATED = 'kuma_updated'

    CHAPTER_ID = 'chapter_id'
    CHAPTER_KEY = 'chapter_key'
    CHAPTER_URL = 'chapter_url'
    CHAPTER_NUM = 'chapter_num'
    CHAPTER_DATE = 'chapter_date'

    PAGE_ID = 'page_id'
    PAGE_URL = 'page_url'
    PAGE = 'page'

    book_name_table = 'BOOK'
    chapter_name_table = 'CHAPTER'
    page_name_table = 'PAGE'
    dbname = 'rawkuma.sqlite'

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
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS {TABLE} (
                book_id integer PRIMARY KEY AUTOINCREMENT, -- ブックID
                book_key text not null, -- URLに含まれる識別子
                book_type char, -- タイプ
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
        '''.format(TABLE=self.book_name_table))

        self.conn.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS {TABLE}_key ON {TABLE} (
                book_key -- URLに含まれる識別子
            )
        '''.format(TABLE=self.book_name_table))

    def insert_book(self, **kwargs) -> int:
        book_id = self.getBookID(kwargs[DB.BOOK_KEY])
    
        if book_id is not None:
            return book_id
    
        cur = self.conn.cursor()
        cur.executemany('''
            insert into {TABLE} (
                book_key,
                book_type,
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
            ) values (?,?,?,?,?,?,?,?,?,?,?,?,?)
        '''.format(TABLE=self.book_name_table), [(
            kwargs[DB.BOOK_KEY],
            kwargs[DB.BOOK_TYPE] if DB.BOOK_TYPE in kwargs else None,
            kwargs[DB.USE_FLAG] if DB.USE_FLAG in kwargs else None,
            kwargs[DB.URL],
            kwargs[DB.TITLE] if DB.TITLE in kwargs else None,
            kwargs[DB.AUTHOR] if DB.AUTHOR in kwargs else None,
            kwargs[DB.THUMB] if DB.THUMB in kwargs else None,
            kwargs[DB.KUMA_TITLE] if DB.KUMA_TITLE in kwargs else None,
            kwargs[DB.KUMA_AUTHOR] if DB.KUMA_AUTHOR in kwargs else None,
            kwargs[DB.KUMA_TAG] if DB.KUMA_TAG in kwargs else None,
            kwargs[DB.KUMA_DESCRIPTION] if DB.KUMA_DESCRIPTION in kwargs else None,
            kwargs[DB.KUMA_POSTED] if DB.KUMA_POSTED in kwargs else None,
            kwargs[DB.KUMA_UPDATED] if DB.KUMA_UPDATED in kwargs else None
        )])

        cur.execute('select last_insert_rowid() from {TABLE}'.format(TABLE=self.book_name_table))
        for row in cur.fetchall():
            cur.close()
            return row[0] # 取得したbook_idを返す

        cur.close()
        return None


    def update_book(self, book_id, **kwargs) -> None:
        cur = self.conn.cursor()

        value = []
        value.append(kwargs[DB.BOOK_TYPE]) if DB.BOOK_TYPE in kwargs else None
        value.append(kwargs[DB.USE_FLAG]) if DB.USE_FLAG in kwargs else None
        value.append(kwargs[DB.URL]) if DB.URL in kwargs else None
        value.append(kwargs[DB.TITLE]) if DB.TITLE in kwargs else None
        value.append(kwargs[DB.AUTHOR]) if DB.AUTHOR in kwargs else None
        value.append(kwargs[DB.THUMB]) if DB.THUMB in kwargs else None
        value.append(kwargs[DB.KUMA_TITLE]) if DB.KUMA_TITLE in kwargs else None
        value.append(kwargs[DB.KUMA_AUTHOR]) if DB.KUMA_AUTHOR in kwargs else None
        value.append(kwargs[DB.KUMA_TAG]) if DB.KUMA_TAG in kwargs else None
        value.append(kwargs[DB.KUMA_DESCRIPTION]) if DB.KUMA_DESCRIPTION in kwargs else None
        value.append(kwargs[DB.KUMA_POSTED]) if DB.KUMA_POSTED in kwargs else None
        value.append(kwargs[DB.KUMA_UPDATED]) if DB.KUMA_UPDATED in kwargs else None
        value.append(book_id)

        sql = "update {TABLE} set updated = datetime('now','localtime')".format(TABLE=self.book_name_table)
        sql += ", book_type = ? " if DB.BOOK_TYPE in kwargs else ""
        sql += ", use_flag = ? " if DB.USE_FLAG in kwargs else ""
        sql += ", url = ? " if DB.URL in kwargs else ""
        sql += ", title = ? " if DB.TITLE in kwargs else ""
        sql += ', author = ? ' if DB.AUTHOR in kwargs else ""
        sql += ', thumb_url = ? ' if DB.THUMB in kwargs else ""
        sql += ', kuma_title = ? ' if DB.KUMA_TITLE in kwargs else ""
        sql += ', kuma_author = ? ' if DB.KUMA_AUTHOR in kwargs else ""
        sql += ', kuma_tag = ? ' if DB.KUMA_TAG in kwargs else ""
        sql += ', kuma_description = ? ' if DB.KUMA_DESCRIPTION in kwargs else ""
        sql += ', kuma_posted = ? ' if DB.KUMA_POSTED in kwargs else ""
        sql += ', kuma_updated = ? ' if DB.KUMA_UPDATED in kwargs else ""
        sql += " where book_id = ? "
        self.__logging.info(sql)

        cur.executemany(sql, [tuple(value)])
        cur.close()

    def select_book(self, **kwargs):
        cur = self.conn.cursor()
        sql = "select book_id ".format(TABLE=self.book_name_table)
        sql += ", book_key " if DB.BOOK_KEY in kwargs else ""
        sql += ", book_type " if DB.BOOK_TYPE in kwargs else ""
        sql += ", use_flag " if DB.USE_FLAG in kwargs else ""
        sql += ", url " if DB.URL in kwargs else ""
        sql += ", title " if DB.TITLE in kwargs else ""
        sql += ', author ' if DB.AUTHOR in kwargs else ""
        sql += ', thumb_url ' if DB.THUMB in kwargs else ""
        sql += ', kuma_title ' if DB.KUMA_TITLE in kwargs else ""
        sql += ', kuma_author ' if DB.KUMA_AUTHOR in kwargs else ""
        sql += ', kuma_tag ' if DB.KUMA_TAG in kwargs else ""
        sql += ', kuma_description ' if DB.KUMA_DESCRIPTION in kwargs else ""
        sql += ', kuma_posted ' if DB.KUMA_POSTED in kwargs else ""
        sql += ', kuma_updated ' if DB.KUMA_UPDATED in kwargs else ""
        sql += ' from {TABLE} '.format(TABLE=self.book_name_table)

        value = []
        where = []
        if DB.BOOK_ID in kwargs and kwargs[DB.BOOK_ID] is not None:
            where.append('book_id = ?')
            value.append(kwargs[DB.BOOK_ID])

        if DB.BOOK_KEY in kwargs and kwargs[DB.BOOK_KEY] is not None:
            where.append('book_key = ?')
            value.append(kwargs[DB.BOOK_KEY])

        if DB.BOOK_TYPE in kwargs and kwargs[DB.BOOK_TYPE] is not None:
            where.append('book_type = ?')
            value.append(kwargs[DB.BOOK_TYPE])

        if DB.USE_FLAG in kwargs and kwargs[DB.USE_FLAG] is not None:
            where.append('use_flag = ?')
            value.append(kwargs[DB.USE_FLAG])

        if DB.KUMA_UPDATED in kwargs and kwargs[DB.KUMA_UPDATED] is not None:
            where.append('kuma_updated < ?')
            value.append(kwargs[DB.KUMA_UPDATED])

        sql += ' where {W}'.format(W=' and '.join(where)) if len(where) != 0 else ''
        sql += ' order by kuma_updated desc'
        self.__logging.info(sql)

        self.__logging.info(tuple(value))
        cur.execute(sql, tuple(value))

        vals = []
        for row in cur.fetchall():
            l = list(row)
            val = {DB.BOOK_ID: l.pop(0)}
            val.update({DB.BOOK_KEY: l.pop(0)}) if DB.BOOK_KEY in kwargs else ""
            val.update({DB.BOOK_TYPE: l.pop(0)}) if DB.BOOK_TYPE in kwargs else ""
            val.update({DB.USE_FLAG: l.pop(0)}) if DB.USE_FLAG in kwargs else ""
            val.update({DB.URL: l.pop(0)}) if DB.URL in kwargs else ""
            val.update({DB.TITLE: l.pop(0)}) if DB.TITLE in kwargs else ""
            val.update({DB.AUTHOR: l.pop(0)}) if DB.AUTHOR in kwargs else ""
            val.update({DB.THUMB: l.pop(0)}) if DB.THUMB in kwargs else ""
            val.update({DB.KUMA_TITLE: l.pop(0)}) if DB.KUMA_TITLE in kwargs else ""
            val.update({DB.KUMA_AUTHOR: l.pop(0)}) if DB.KUMA_AUTHOR in kwargs else ""
            val.update({DB.KUMA_TAG: l.pop(0)}) if DB.KUMA_TAG in kwargs else ""
            val.update({DB.KUMA_DESCRIPTION: l.pop(0)}) if DB.KUMA_DESCRIPTION in kwargs else ""
            if DB.KUMA_POSTED in kwargs:
                v = l.pop(0)
                val.update({DB.KUMA_POSTED: datetime.strptime(v,'%Y-%m-%d %H:%M:%S%z').astimezone(timezone(timedelta(hours=9))) if v is not None else None})
            if DB.KUMA_UPDATED in kwargs:
                v = l.pop(0)
                val.update({DB.KUMA_UPDATED: datetime.strptime(v,'%Y-%m-%d %H:%M:%S%z').astimezone(timezone(timedelta(hours=9))) if v is not None else None})
            vals.append(val)

        cur.close()
        return vals
        

    def getBookID(self, book_key) -> int:
        cur = self.conn.cursor()
        cur.execute('select book_id from {TABLE} where book_key = ?'.format(TABLE=self.book_name_table), (book_key,))

        for row in cur.fetchall():
            cur.close()
            return row[0] # 取得したbook_idを返す

        cur.close()
        return None

    def check_book(self, book_key) -> bool:
        cur = self.conn.cursor()
        cur.execute('select book_id from {TABLE} where book_key = ?'.format(TABLE=self.book_name_table), (book_key,))
        lists = cur.fetchall()
        cur.close()
        return len(lists) > 0

    def delete_book(self, book_key) -> None:
        cur = self.conn.cursor()
        cur.execute('select book_id from {TABLE} where book_key = ?'.format(TABLE=self.book_name_table), (book_key,))

        for val in cur.fetchall():
            self.delete_chapter(val[0])

        cur.execute('delete from {TABLE} where book_key = ?'.format(TABLE=self.book_name_table), (book_key,))
        cur.close()


    def __create_table_chapter(self) -> None:
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS {TABLE} (
                chapter_id integer PRIMARY KEY AUTOINCREMENT, -- チャプターID
                chapter_key text not null, -- 
                book_id integer not null,
                chapter_url text, -- チャプターURL
                chapter_num text, --
                chapter_date datetime, -- 更新日付
                created datetime default (datetime('now','localtime')), -- 作成日
                updated datetime default (datetime('now','localtime')) -- 更新日
            )
        '''.format(TABLE=self.chapter_name_table))

        self.conn.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS {TABLE}_key ON {TABLE} (
                book_id, chapter_key -- チャプター識別子
            )
        '''.format(TABLE=self.chapter_name_table))

    def insert_chapter(self, **kwargs) -> int:
        cur = self.conn.cursor()
        cur.execute('''
            select chapter_id from {TABLE} where book_id = ? and chapter_key = ?
        '''.format(TABLE=self.chapter_name_table), (kwargs[DB.BOOK_ID], kwargs[DB.CHAPTER_KEY]))

        for row in cur.fetchall():
            cur.close()
            return row[0] # 取得したchapter_idを返す

        cur.executemany('''
            insert into {TABLE} (
                chapter_key,
                book_id,
                chapter_url,
                chapter_num,
                chapter_date
            ) values (?,?,?,?,?)
        '''.format(TABLE=self.chapter_name_table), [(
            kwargs[DB.CHAPTER_KEY],
            kwargs[DB.BOOK_ID],
            kwargs[DB.CHAPTER_URL],
            kwargs[DB.CHAPTER_NUM] if DB.CHAPTER_NUM in kwargs else None,
            kwargs[DB.CHAPTER_DATE] if DB.CHAPTER_DATE in kwargs else None
        )])

        rows = cur.execute('select last_insert_rowid() from {TABLE}'.format(TABLE=self.chapter_name_table))
        for row in rows:
            cur.close()
            return row[0] # 取得したchapter_idを返す

        cur.close()
        return None


    def check_chapter(self, book_id, chapter_key) -> bool:
        cur = self.conn.cursor()
        cur.execute('''
            select chapter_id from {TABLE} where book_id = ? and chapter_key = ?
        '''.format(TABLE=self.chapter_name_table), (book_id, chapter_key))
        lists = cur.fetchall()
        cur.close()
        return len(lists) > 0

    def select_chapter(self, book_id):
        cur = self.conn.cursor()
        cur.execute('''
            select chapter_id, chapter_key, chapter_url, chapter_num, chapter_date from {TABLE} where book_id = ? order by chapter_key
        '''.format(TABLE=self.chapter_name_table), (book_id,))
    
        lists = [{DB.CHAPTER_ID: val[0],
                  DB.CHAPTER_KEY: val[1],
                  DB.CHAPTER_URL: val[2],
                  DB.CHAPTER_NUM: val[3],
                  DB.CHAPTER_DATE: datetime.strptime(val[4], '%Y-%m-%d %H:%M:%S') if val[4] is not None else None
                 } for val in cur.fetchall() ]
        cur.close()
        return lists

    def delete_chapter(self, book_id) -> None:
        cur = self.conn.cursor()
        cur.execute('select chapter_id from {TABLE} where book_id = ?'.format(TABLE=self.chapter_name_table), (book_id,))
    
        for val in cur.fetchall():
            self.delete_page(val[0])

        sql = 'delete from {TABLE} where book_id = ?'.format(TABLE=self.chapter_name_table)
        value = (book_id,)
        self.__logging.info(sql)
        self.__logging.info(tuple(value))
        cur.execute(sql, tuple(value))
        cur.close()


    def __create_table_page(self) -> None:
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS {TABLE} (
                page_id integer PRIMARY KEY AUTOINCREMENT, -- ページID
                chapter_id integer not null,
                page integer not null, -- ページ番号
                page_url text not null, -- ページURL
                created datetime default (datetime('now','localtime')), -- 作成日
                updated datetime default (datetime('now','localtime')) -- 更新日
            )
        '''.format(TABLE=self.page_name_table, CHAPTER=self.chapter_name_table))

        self.conn.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS {TABLE}_key ON {TABLE} (
                chapter_id, page
            )
        '''.format(TABLE=self.page_name_table))

    def insert_page(self, pagelists) -> None:
        cur = self.conn.cursor()
        cur.executemany('''
            insert into {TABLE} (chapter_id, page_url, page) values (?,?,?)
        '''.format(TABLE=self.page_name_table), pagelists)
        cur.close()

    def select_page(self, chapter_id):
        cur = self.conn.cursor()
        cur.execute('''
            select page_id, page, page_url from {TABLE} where chapter_id = ? order by page
        '''.format(TABLE=self.page_name_table), (chapter_id,))

        lists = [ {DB.PAGE_ID: val[0], DB.PAGE: val[1], DB.PAGE_URL: val[2]} for val in cur.fetchall() ]
        cur.close()
        return lists

    def delete_page(self, chapter_id) -> None:
        cur = self.conn.cursor()
        sql = 'delete from {TABLE} where chapter_id = ?'.format(TABLE=self.page_name_table)
        value = (chapter_id,)
        self.__logging.info(sql)
        self.__logging.info(tuple(value))
        cur.execute(sql, tuple(value))
        cur.close()
