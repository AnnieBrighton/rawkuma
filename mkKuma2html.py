#!/usr/bin/env python3

import logging
import os
import sys
import html
import hashlib

from urllib.parse import unquote
from mako.template import Template
from mako.lookup import TemplateLookup

# ===== Enum版 DB ライブラリ =====
from DB import DB, UseFlag, CommonCol, BookCol, ChapterCol, PageCol

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(threadName)s: %(message)s",
    filename="rawkuma.log",
)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter("%(asctime)s %(threadName)s: %(message)s"))
logging.getLogger("").addHandler(console)


class MkKuma2Html:
    BASE_PATH = "Books"

    def __init__(self) -> None:
        self.db = DB(logging)
        self.path = os.path.abspath(os.path.dirname(sys.argv[0]))
        self.lookup = TemplateLookup(
            filesystem_checks=False, directories=[self.path + "/templates"]
        )

    def getHash(self, val) -> str:
        return hashlib.md5(val.encode("utf-8")).hexdigest()[0:2]

    def tohtml(self) -> None:
        """HTML出力"""
        lists = self.db.select_book({BookCol.TYPE: None})
        types = sorted(set([val[BookCol.TYPE] for val in lists]))

        # ベースディレクトリ作成
        os.makedirs(self.BASE_PATH, exist_ok=True)

        # タイプリストHTML出力
        self.output_book(types)

        for type in types:
            books = self.db.select_book(
                {
                    BookCol.KEY: None,
                    BookCol.TITLE: None,
                    BookCol.THUMB: None,
                    BookCol.TYPE: type,
                    BookCol.SINGLE: None,
                    BookCol.KUMA_TITLE: None,
                    BookCol.KUMA_THUMB: None,
                    CommonCol.USE_FLAG: None,
                }
            )

            # ブック一覧HTML出力
            self.output_book_type(books, types, type)

            for book in books:
                chapters = self.db.select_chapter(
                    {
                        BookCol.ID: book[BookCol.ID],
                        ChapterCol.ID: None,
                        ChapterCol.KEY: None,
                        ChapterCol.URL: None,
                        ChapterCol.NUM: None,
                        ChapterCol.DATE: None,
                        ChapterCol.SINGLE: None,
                    }
                )

                path = unquote(
                    os.path.join(
                        self.BASE_PATH,
                        self.getHash(book[BookCol.KEY]),
                        book[BookCol.KEY],
                    )
                )

                # チャプター格納ディレクトリ作成
                os.makedirs(path, exist_ok=True)

                # チャプター一覧HTML出力
                self.output_chapter_top(type, book, path, chapters)

                # チャプターHTML出力
                self.output_chapter(book, path, chapters)

    def output_book(self, types):
        """トップの Books.html を作成

        Args:
            types ( list ): タイプのリスト
        """

        tmpl = self.lookup.get_template("Books.html")
        data = {"types": [type for type in types]}

        with open(os.path.join(self.BASE_PATH, "Books.html"), mode="w") as f:
            f.write(tmpl.render(**data))

    def output_book_type(self, books, types, type):
        """タイプのブック一覧表示

        Args:
            books (_type_): ブックリスト
            types (_type_): タイプリスト
            type (_type_): タイプ
        """

        tmpl = self.lookup.get_template("Books_type.html")

        data = {
            "types": [type for type in types],
            "cur_type": type,
            "books": [
                {
                    "HREF": os.path.join(
                        self.getHash(book[BookCol.KEY]),
                        book[BookCol.KEY],
                        book[BookCol.KEY] + ".html",
                    ),
                    "SRC": book[BookCol.THUMB] if book[BookCol.THUMB] is not None else book[BookCol.KUMA_THUMB],
                    "FLAG": book[CommonCol.USE_FLAG],
                    "TITLE": (
                        html.escape(book[BookCol.TITLE] if book[BookCol.TITLE] is not None else book[BookCol.KUMA_TITLE], quote=True)
                        if book[BookCol.KUMA_TITLE] is not None or book[BookCol.TITLE] is not None
                        else "未設定"
                    ),
                }
                for book in books
            ],
        }

        with open(
            os.path.join(self.BASE_PATH, "Books{TYPE}.html".format(TYPE=type)), mode="w"
        ) as f:
            f.write(tmpl.render(**data))

        tmpl = self.lookup.get_template("Books_Mark.html")
        with open(os.path.join(self.BASE_PATH, "BooksMark.html"), mode="w") as f:
            f.write(tmpl.render(**data))

    def output_chapter_top(self, type, book, path, chapters):
        """_summary_

        Args:
            type (_type_): _description_
            book (_type_): _description_
            path (_type_): _description_
            chapters (_type_): _description_
        """

        tmpl = self.lookup.get_template("Chapter_top.html")

        data = {
            "type": type,
            "thumb": book[BookCol.THUMB] if book[BookCol.THUMB] is not None else book[BookCol.KUMA_THUMB],
            "title": (
                html.escape(book[BookCol.TITLE] if book[BookCol.TITLE] is not None else book[BookCol.KUMA_TITLE], quote=True)
                if book[BookCol.KUMA_TITLE] is not None or book[BookCol.TITLE] is not None
                else "未設定"
            ),
            "book_key": book[BookCol.KEY],
            "chapters": [
                {
                    "KEY": chap[ChapterCol.KEY],
                    "HREF": chap[ChapterCol.KEY] + ".html",
                    "NUM": chap[ChapterCol.NUM],
                    "DATE": chap[ChapterCol.DATE].strftime("%Y年%m月%d日"),
                }
                for chap in sorted(
                    chapters, key=lambda x: x[ChapterCol.KEY], reverse=True
                )
            ],
        }

        with open(
            unquote(os.path.join(path, book[BookCol.KEY] + ".html")), mode="w"
        ) as f:
            f.write(tmpl.render(**data))

    def output_chapter(self, book, path, chapters):
        """_summary_

        Args:
            book (_type_): _description_
            path (_type_): _description_
            chapters (_type_): チャプターリスト
        """

        tmpl = self.lookup.get_template("Chapter.html")

        max = len(chapters)
        for index, chapter in enumerate(chapters):
            prev = chapters[index - 1]
            next = chapters[(index + 1) % max]

            pages = self.db.select_page(
                {
                    ChapterCol.ID: chapter[ChapterCol.ID],
                    PageCol.URL: None,
                    PageCol.SINGLE: None,
                }
            )

            # 単ページから開始するか、
            single_page_start = (
                book[BookCol.SINGLE] != 0 and chapter[ChapterCol.SINGLE] is None
            ) or (
                chapter[ChapterCol.SINGLE] != 0
                and chapter[ChapterCol.SINGLE] is not None
            )

            data = {
                "prev": {
                    "HREF": prev[ChapterCol.KEY] + ".html",
                    "NUM": prev[ChapterCol.NUM],
                },
                "next": {
                    "HREF": next[ChapterCol.KEY] + ".html",
                    "NUM": next[ChapterCol.NUM],
                },
                "book_key": book[BookCol.KEY],
                "chapter_key": chapter[ChapterCol.KEY],
                "title": (
                    html.escape(book[BookCol.TITLE] if book[BookCol.TITLE] is not None else book[BookCol.KUMA_TITLE], quote=True)
                    if book[BookCol.KUMA_TITLE] is not None or book[BookCol.TITLE] is not None
                    else "未設定"
                ),
                "chapter_top": book[BookCol.KEY] + ".html",
                "chapters": [
                    {
                        "KEY": chap[ChapterCol.KEY],
                        "HREF": chap[ChapterCol.KEY] + ".html",
                        "NUM": chap[ChapterCol.NUM],
                    }
                    for chap in sorted(
                        chapters, key=lambda x: x[ChapterCol.KEY], reverse=True
                    )
                ],
                "pages": [
                    {
                        "URL": page[PageCol.URL],
                        "SINGLE": (
                            (
                                page[PageCol.SINGLE] != 0
                                and page[PageCol.SINGLE] is not None
                            )
                            or (num == 0 and single_page_start)
                        ),
                    }
                    for num, page in enumerate(pages)
                ],
            }

            with open(
                unquote(
                    os.path.join(
                        path,
                        chapter[ChapterCol.KEY] + ".html",
                    )
                ),
                mode="w",
            ) as f:
                f.write(tmpl.render(**data))


#
# メイン
#

if __name__ == "__main__":
    kuma = MkKuma2Html()
    kuma.tohtml()
