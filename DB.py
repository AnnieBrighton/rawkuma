#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DB アクセスライブラリ（最終版）
--------------------------------
目的:
- Webで収集した BOOK / CHAPTER / PAGE 情報を SQLite に保存・取得する。
- アプリ側 I/F は「すべて JST(+09:00) の datetime」を扱い、DB 内部は UTC ISO8601(TEXT) で統一。
- 使い方（select/update の規約）は以下を満たす:
    - select_*: kwargs のキーに列挙したカラムは SELECT 対象。
                そのうち値が None 以外なら WHERE 条件 (AND) に含める。
                特例: BookCol.KUMA_UPDATED に値がある場合は `<` 比較を行う（従来互換）。
    - update_*: kwargs のキー/値を UPDATE に反映。日時は JST を渡せば内部で UTC へ変換。
- スキーマは Enum で定義（Table / CommonCol / BookCol / ChapterCol / PageCol / UseFlag）。
- insert_* は upsert (ON CONFLICT DO UPDATE) + RETURNING で ID を返す。
- select_* の既定で use_flag <> NO_USED を自動付与（非表示レコードを除外）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum, IntEnum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import sqlite3


# =========================
# タイムゾーンと日時変換ヘルパ
# =========================

# アプリ I/F の既定タイムゾーン（日本時間）
JST = timezone(timedelta(hours=9), "JST")


def _to_db_dt_jst(dt: Optional[datetime]) -> Optional[str]:
    """
    アプリ側(JST/naive許容)の datetime を DB保存用(UTC ISO8601文字列)に変換する。
    - naive の場合は JST と見なして +09:00 を付与。
    - DB は ISO8601(Z表記)で統一。
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _from_db_dt_jst(s: Optional[str]) -> Optional[datetime]:
    """
    DB保存の UTC ISO8601 文字列を、JST の timezone-aware datetime に変換する。
    """
    if not s:
        return None
    # "Z" を "+00:00" に置換して fromisoformat に通す
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(JST)


# =========================
# スキーマ（テーブル・カラム・フラグ）
# =========================

class Table(Enum):
    BOOK = "BOOK"
    CHAPTER = "CHAPTER"
    PAGE = "PAGE"


class UseFlag(IntEnum):
    COMPLETED = 0     # 完了
    UPDATE = 1        # 更新中
    STOPPED = 2       # 更新中止
    USED = 3          # 表示対象
    NO_USED = 4       # 表示対象外（select_* で既定で除外する）


class CommonCol(Enum):
    CREATED = "created"   # 作成時刻（DBはUTC ISO、I/FはJST datetime）
    UPDATED = "updated"   # 更新時刻（同上）
    USE_FLAG = "use_flag" # 表示制御フラグ（UseFlag）


class BookCol(Enum):
    ID = "book_id"
    KEY = "book_key"
    TYPE = "book_type"
    SINGLE = "book_single"     # 1:true / 0:false
    URL = "book_url"
    TITLE = "book_title"
    AUTHOR = "book_author"
    THUMB = "thumb"
    KUMA_THUMB = "kuma_thumb"
    KUMA_TITLE = "kuma_title"
    KUMA_AUTHOR = "kuma_author"
    KUMA_TAG = "kuma_tag"
    KUMA_DESC = "kuma_description"
    KUMA_POSTED = "kuma_posted"     # DB: ISO(UTC), I/F: JST datetime
    KUMA_UPDATED = "kuma_updated"   # 同上


class ChapterCol(Enum):
    ID = "chapter_id"
    KEY = "chapter_key"
    BOOK_ID = "book_id"
    SINGLE = "chapter_single"   # 1:true / 0:false / NULL:book設定に従う
    URL = "chapter_url"
    NUM = "chapter_num"
    DATE = "chapter_date"       # DB: ISO(UTC), I/F: JST datetime


class PageCol(Enum):
    ID = "page_id"
    CHAPTER_ID = "chapter_id"
    NUM = "page_num"
    URL = "page_url"
    SINGLE = "page_single"


# JST変換対象の日時カラム（保存はUTC、I/FはJST）
_DT_COLS = {
    CommonCol.CREATED, CommonCol.UPDATED,
    BookCol.KUMA_POSTED, BookCol.KUMA_UPDATED,
    ChapterCol.DATE,
}


# =========================
# DB クラス本体
# =========================

class DB:
    """
    SQLite を用いた軽量 ORM 風ラッパ（Enum で列を指定する）
    - select_*: 指定キーは SELECT 対象。値 None → WHERE には含めない。値あり → WHERE col = ?（一部例外あり）
    - update_*: 指定キー/値を UPDATE に反映。日時は JST を渡せば内部で UTC へ保存。
    - insert_*: upsert + RETURNING で ID を返す（既存は更新）。
    """

    dbname = "rawkuma.sqlite"

    def __init__(self, logging) -> None:
        self.log = logging
        self.conn = sqlite3.connect(self.dbname)
        self.conn.row_factory = sqlite3.Row
        self._pragma()
        self._create_book()
        self._create_chapter()
        self._create_page()

    # --------------- コンテキスト管理 ---------------
    def __enter__(self) -> "DB":
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc:
                self.conn.rollback()
            else:
                self.conn.commit()
        finally:
            self.conn.close()

    # --------------- トランザクション ---------------
    def close(self): self.conn.close()
    def commit(self): self.conn.commit()
    def rollback(self): self.conn.rollback()

    # --------------- PRAGMA 最適化 ---------------
    def _pragma(self):
        cur = self.conn.cursor()
        # 外部キー制約を有効化（CASCADE を効かせる）
        cur.execute("PRAGMA foreign_keys = ON")
        # 併用アクセスに強いWALモード（書き込み遅延を減らす）
        cur.execute("PRAGMA journal_mode = WAL")
        # 速度と安全性のバランス
        cur.execute("PRAGMA synchronous = NORMAL")
        cur.close()

    # =========================
    # テーブル作成
    # =========================

    def _create_book(self):
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {Table.BOOK.value} (
                {BookCol.ID.value} INTEGER PRIMARY KEY AUTOINCREMENT,
                {BookCol.KEY.value} TEXT NOT NULL,
                {BookCol.TYPE.value} TEXT,
                {BookCol.SINGLE.value} INTEGER NOT NULL DEFAULT 1,
                {CommonCol.USE_FLAG.value} INTEGER,
                {BookCol.URL.value}   TEXT NOT NULL,
                {BookCol.TITLE.value}  TEXT,
                {BookCol.AUTHOR.value} TEXT,
                {BookCol.THUMB.value} TEXT DEFAULT NULL,
                {BookCol.KUMA_THUMB.value} TEXT,
                {BookCol.KUMA_AUTHOR.value} TEXT,
                {BookCol.KUMA_TITLE.value}  TEXT,
                {BookCol.KUMA_TAG.value}    TEXT,
                {BookCol.KUMA_DESC.value}   TEXT,
                {BookCol.KUMA_POSTED.value}  TEXT, -- ISO8601(UTC)
                {BookCol.KUMA_UPDATED.value} TEXT, -- ISO8601(UTC)
                {CommonCol.CREATED.value}  TEXT DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ','now')),
                {CommonCol.UPDATED.value}  TEXT DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ','now')),
                UNIQUE({BookCol.KEY.value})
            );
        """)

    def _create_chapter(self):
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {Table.CHAPTER.value} (
                {ChapterCol.ID.value} INTEGER PRIMARY KEY AUTOINCREMENT,
                {ChapterCol.KEY.value} TEXT NOT NULL,
                {ChapterCol.BOOK_ID.value} INTEGER NOT NULL
                    REFERENCES {Table.BOOK.value}({BookCol.ID.value}) ON DELETE CASCADE,
                {CommonCol.USE_FLAG.value} INTEGER DEFAULT ({UseFlag.USED}),
                {ChapterCol.SINGLE.value} INTEGER,
                {ChapterCol.URL.value} TEXT,
                {ChapterCol.NUM.value} TEXT,
                {ChapterCol.DATE.value} TEXT, -- ISO8601(UTC)
                {CommonCol.CREATED.value}  TEXT DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ','now')),
                {CommonCol.UPDATED.value}  TEXT DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ','now')),
                UNIQUE({ChapterCol.BOOK_ID.value}, {ChapterCol.KEY.value})
            );
        """)

    def _create_page(self):
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {Table.PAGE.value} (
                {PageCol.ID.value} INTEGER PRIMARY KEY AUTOINCREMENT,
                {PageCol.CHAPTER_ID.value} INTEGER NOT NULL
                    REFERENCES {Table.CHAPTER.value}({ChapterCol.ID.value}) ON DELETE CASCADE,
                {CommonCol.USE_FLAG.value} INTEGER DEFAULT ({UseFlag.USED}),
                {PageCol.NUM.value}  INTEGER NOT NULL,
                {PageCol.URL.value}  TEXT NOT NULL,
                {PageCol.SINGLE.value} INTEGER,
                {CommonCol.CREATED.value}  TEXT DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ','now')),
                {CommonCol.UPDATED.value}  TEXT DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ','now')),
                UNIQUE({PageCol.CHAPTER_ID.value}, {PageCol.NUM.value})
            );
        """)

    # =========================
    # 内部共通ヘルパ
    # =========================

    def _normalize_outgoing(self, col: Enum, v: Any) -> Any:
        """
        アプリ(I/F) → DB へ書き込む際の正規化。
        - 日時カラムは JST datetime を UTC ISO に変換。
        """
        if col in _DT_COLS and isinstance(v, datetime):
            return _to_db_dt_jst(v)
        return v

    def _normalize_incoming(self, col: Enum, v: Any) -> Any:
        """
        DB → アプリ(I/F) へ返す際の正規化。
        - 日時カラムは UTC ISO を JST datetime に変換。
        """
        if col in _DT_COLS and v is not None:
            return _from_db_dt_jst(v)
        return v

    def _where_from_kwargs(
        self,
        table_cols: Sequence[Enum],
        kw: Dict[Enum, Any],
        *,
        add_default_visible_filter: bool = False,
    ) -> Tuple[str, List[Any]]:
        """
        kwargs の規約に基づいて WHERE を構築する。
        - key が存在 → SELECT 列に含める（WHERE には影響しない）
        - 値が None 以外 → WHERE 条件として追加（AND結合）
        - 特例:
            * BookCol.KUMA_UPDATED に値がある場合は `< ?` 比較（従来実装互換）
            * BookCol.TITLE に '%%' を含む文字列を渡された場合は LIKE 比較
            * 日付系の値が 'YYYY-MM-DD' の場合は "T00:00:00Z" を補完して比較
        """
        clauses: List[str] = []
        values: List[Any] = []

        if add_default_visible_filter:
            # 非表示レコードを既定で除外
            clauses.append(f"{CommonCol.USE_FLAG.value} <> ?")
            values.append(int(UseFlag.NO_USED))

        for col in table_cols:
            if col not in kw:
                continue
            val = kw[col]
            if val is None:
                # SELECT 列に含めたいだけで WHERE には入れない
                continue

            # 日時文字列の補完：'YYYY-MM-DD' → 'YYYY-MM-DDT00:00:00Z'
            if col in (BookCol.KUMA_POSTED, BookCol.KUMA_UPDATED, ChapterCol.DATE,
                       CommonCol.CREATED, CommonCol.UPDATED):
                if isinstance(val, datetime):
                    val = _to_db_dt_jst(val)
                elif isinstance(val, str) and len(val) == 10:
                    val = val + "T00:00:00Z"

            # 比較演算の分岐
            if col is BookCol.KUMA_UPDATED:
                # 従来実装に合わせ、指定があれば「より前」を取得
                clauses.append(f"{col.value} < ?")
                values.append(val)

            elif col is BookCol.TITLE and isinstance(val, str) and "%" in val:
                clauses.append(f"{col.value} LIKE ?")
                values.append(val)

            else:
                clauses.append(f"{col.value} = ?")
                values.append(val)

        sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return sql, values

    def _select(
        self,
        table: Table,
        select_cols: List[Enum],
        where_sql: str,
        values: List[Any],
        order_by: Optional[str] = None,
    ) -> List[sqlite3.Row]:
        """
        SELECT 実行ヘルパ。必要に応じ ORDER BY を付与。
        """
        columns = ", ".join([c.value for c in select_cols])
        sql = f"SELECT {columns} FROM {table.value}{where_sql}"
        if order_by:
            sql += f" ORDER BY {order_by}"

        self.log.info(sql)
        self.log.info(tuple(values))
        cur = self.conn.execute(sql, tuple(values))
        return cur.fetchall()

    def _update(self, table: Table, id_col: Enum, id_val: Any, updates: Dict[Enum, Any]) -> None:
        """
        UPDATE 実行ヘルパ。
        - `updated` は常に現在時刻 (UTC) に自動更新（sqliteの STRFTIME を使用）
        - updates の各値は必要に応じて UTC 文字列へ正規化
        """
        sets = [f"{CommonCol.UPDATED.value} = STRFTIME('%Y-%m-%dT%H:%M:%fZ','now')"]
        vals: List[Any] = []

        for col, v in updates.items():
            v = self._normalize_outgoing(col, v)
            sets.append(f"{col.value} = ?")
            vals.append(v)

        vals.append(id_val)
        sql = f"UPDATE {table.value} SET {', '.join(sets)} WHERE {id_col.value} = ?"
        self.log.info(sql)
        self.log.info(tuple(vals))
        self.conn.execute(sql, vals)

    # =========================
    # BOOK
    # =========================

    def insert_book(self, data: Dict[BookCol | CommonCol, Any]) -> Optional[int]:
        """
        BOOK の upsert。存在すれば更新し、いずれも ID を返す。
        必須: BookCol.KEY, BookCol.URL
        """
        if BookCol.KEY not in data or BookCol.URL not in data:
            raise ValueError("BookCol.KEY と BookCol.URL は必須です。")

        # 値の正規化（日時は UTC 文字列へ）
        norm: Dict[Enum, Any] = {}
        for col, v in data.items():
            norm[col] = self._normalize_outgoing(col, v)

        cols = list(norm.keys())
        names = ", ".join([c.value for c in cols])
        placeholders = ", ".join(["?"] * len(cols))
        updates = ", ".join([f"{c.value}=excluded.{c.value}" for c in cols if c is not BookCol.KEY])

        sql = f"""
            INSERT INTO {Table.BOOK.value} ({names})
            VALUES ({placeholders})
            ON CONFLICT({BookCol.KEY.value})
            DO UPDATE SET {updates}
            RETURNING {BookCol.ID.value};
        """
        self.log.info(sql)
        cur = self.conn.execute(sql, [norm[c] for c in cols])
        row = cur.fetchone()
        return int(row[0]) if row else None

    def update_book(self, book_id: int, data: Dict[BookCol | CommonCol, Any]) -> None:
        self._update(Table.BOOK, BookCol.ID, book_id, data)

    def select_book(self, kw: Dict[BookCol | CommonCol, Any]) -> List[Dict[Enum, Any]]:
        """
        BOOK の SELECT。
        - kw のキーは SELECT 対象となる列。
        - 値が None 以外のキーは WHERE にも使われる。
        - 既定で use_flag <> NO_USED を付与する。
        - 戻り値の日時列は JST の datetime。
        """
        # SELECT 列: ID は常に含める
        select_cols: List[Enum] = [BookCol.ID] + [c for c in list(BookCol) + list(CommonCol) if c in kw]
        where_sql, values = self._where_from_kwargs(list(BookCol) + list(CommonCol), kw, add_default_visible_filter=True)
        rows = self._select(Table.BOOK, select_cols, where_sql, values, order_by=f"{BookCol.KUMA_UPDATED.value} DESC")

        out: List[Dict[Enum, Any]] = []
        for r in rows:
            d: Dict[Enum, Any] = {}
            for c in select_cols:
                raw = r[c.value]
                d[c] = self._normalize_incoming(c, raw)
            out.append(d)
        return out

    def get_book_id(self, book_key: str) -> Optional[int]:
        cur = self.conn.execute(
            f"SELECT {BookCol.ID.value} FROM {Table.BOOK.value} WHERE {BookCol.KEY.value} = ?",
            (book_key,),
        )
        row = cur.fetchone()
        return int(row[0]) if row else None

    def check_book(self, book_key: str) -> bool:
        return self.get_book_id(book_key) is not None

    def delete_book(self, book_key: str) -> None:
        # CASCADE により CHAPTER / PAGE も連鎖削除される
        self.conn.execute(
            f"DELETE FROM {Table.BOOK.value} WHERE {BookCol.KEY.value} = ?",
            (book_key,),
        )

    # =========================
    # CHAPTER
    # =========================

    def insert_chapter(self, data: Dict[ChapterCol | CommonCol, Any]) -> Optional[int]:
        """
        CHAPTER の upsert。 (book_id, chapter_key) でユニーク。
        必須: ChapterCol.BOOK_ID, ChapterCol.KEY
        """
        if ChapterCol.BOOK_ID not in data or ChapterCol.KEY not in data:
            raise ValueError("ChapterCol.BOOK_ID と ChapterCol.KEY は必須です。")

        # 日時含む値の正規化
        norm: Dict[Enum, Any] = {}
        for col, v in data.items():
            norm[col] = self._normalize_outgoing(col, v)

        cols = list(norm.keys())
        names = ", ".join([c.value for c in cols])
        placeholders = ", ".join(["?"] * len(cols))
        updates = ", ".join([f"{c.value}=excluded.{c.value}" for c in cols if c not in (ChapterCol.BOOK_ID, ChapterCol.KEY)])

        sql = f"""
            INSERT INTO {Table.CHAPTER.value} ({names})
            VALUES ({placeholders})
            ON CONFLICT({ChapterCol.BOOK_ID.value}, {ChapterCol.KEY.value})
            DO UPDATE SET {updates}
            RETURNING {ChapterCol.ID.value};
        """
        self.log.info(sql)
        cur = self.conn.execute(sql, [norm[c] for c in cols])
        row = cur.fetchone()
        return int(row[0]) if row else None

    def update_chapter(self, chapter_id: int, data: Dict[ChapterCol | CommonCol, Any]) -> None:
        self._update(Table.CHAPTER, ChapterCol.ID, chapter_id, data)

    def select_chapter(self, kw: Dict[ChapterCol | CommonCol, Any]) -> List[Dict[Enum, Any]]:
        """
        CHAPTER の SELECT（既定で非表示除外）。戻り値の日時列は JST。
        """
        select_cols: List[Enum] = [ChapterCol.ID] + [c for c in list(BookCol) + list(ChapterCol) + list(CommonCol) if c in kw]
        where_sql, values = self._where_from_kwargs(list(BookCol) + list(ChapterCol) + list(CommonCol), kw, add_default_visible_filter=True)
        rows = self._select(Table.CHAPTER, select_cols, where_sql, values, order_by=ChapterCol.KEY.value)

        out: List[Dict[Enum, Any]] = []
        for r in rows:
            d: Dict[Enum, Any] = {}
            for c in select_cols:
                raw = r[c.value]
                d[c] = self._normalize_incoming(c, raw)
            out.append(d)
        return out

    def check_chapter(self, book_id: int, chapter_key: str) -> bool:
        cur = self.conn.execute(
            f"""SELECT {ChapterCol.ID.value}
                  FROM {Table.CHAPTER.value}
                 WHERE {ChapterCol.BOOK_ID.value} = ? AND {ChapterCol.KEY.value} = ?""",
            (book_id, chapter_key),
        )
        return cur.fetchone() is not None

    def delete_chapter(self, kw: Dict[ChapterCol, Any]) -> None:
        """
        CHAPTER の削除。
        指定可能: ChapterCol.BOOK_ID / ChapterCol.ID
        - CASCADE により PAGE も削除される。
        """
        clauses: List[str] = []
        values: List[Any] = []

        for col in (ChapterCol.BOOK_ID, ChapterCol.ID):
            if col in kw and kw[col] is not None:
                clauses.append(f"{col.value} = ?")
                values.append(kw[col])

        where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"DELETE FROM {Table.CHAPTER.value}{where_sql}"
        self.log.info(sql)
        self.log.info(tuple(values))
        self.conn.execute(sql, tuple(values))

    # =========================
    # PAGE
    # =========================

    def insert_page(self, pagelists: Iterable[Tuple[int, str, int]]) -> None:
        """
        PAGE を一括挿入。
        引数: [(chapter_id, page_url, page_num), ...]
        - 既存 UNIQUE (chapter_id, page_num) とぶつかる場合はエラーなくスキップしたいなら
          呼び出し側で既存在チェック、または REPLACE/ON CONFLICT DO NOTHING 化を検討。
        """
        sql = f"INSERT INTO {Table.PAGE.value} ({PageCol.CHAPTER_ID.value}, {PageCol.URL.value}, {PageCol.NUM.value}) VALUES (?,?,?)"
        self.conn.executemany(sql, list(pagelists))

    def update_page(self, page_id: int, data: Dict[PageCol | CommonCol, Any]) -> None:
        self._update(Table.PAGE, PageCol.ID, page_id, data)

    def select_page(self, kw: Dict[PageCol | CommonCol, Any]) -> List[Dict[Enum, Any]]:
        """
        PAGE の SELECT（既定で非表示除外）。
        """
        select_cols: List[Enum] = [PageCol.ID] + [c for c in list(ChapterCol) + list(PageCol) + list(CommonCol) if c in kw]
        where_sql, values = self._where_from_kwargs(list(ChapterCol) + list(PageCol) + list(CommonCol), kw, add_default_visible_filter=True)
        rows = self._select(Table.PAGE, select_cols, where_sql, values, order_by=PageCol.NUM.value)

        out: List[Dict[Enum, Any]] = []
        for r in rows:
            d: Dict[Enum, Any] = {}
            for c in select_cols:
                raw = r[c.value]
                d[c] = self._normalize_incoming(c, raw)
            out.append(d)
        return out

    def delete_page_for_chapter(self, chapter_id: int) -> None:
        """
        指定チャプター配下の PAGE を一括削除。
        """
        sql = f"DELETE FROM {Table.PAGE.value} WHERE {PageCol.CHAPTER_ID.value} = ?"
        self.log.info(sql)
        self.conn.execute(sql, (chapter_id,))

    def delete_page(self, page_id: int) -> None:
        """
        指定 PAGE を削除。
        """
        sql = f"DELETE FROM {Table.PAGE.value} WHERE {PageCol.ID.value} = ?"
        self.log.info(sql)
        self.conn.execute(sql, (page_id,))