#!/usr/bin/env python3

import logging
import os
import sys
from DB import DB
import html
import hashlib

from urllib.parse import unquote
from mako.template import Template
from mako.lookup import TemplateLookup

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
        lists = self.db.select_book(**{DB.BOOK_TYPE: None})
        types = sorted(set([val[DB.BOOK_TYPE] for val in lists]))

        # ベースディレクトリ作成
        os.makedirs(self.BASE_PATH, exist_ok=True)

        # タイプリストHTML出力
        self.output_book(types)

        for type in types:
            books = self.db.select_book(
                **{
                    DB.BOOK_KEY: None,
                    DB.TITLE: None,
                    DB.BOOK_TYPE: type,
                    DB.BOOK_SINGLE: None,
                    DB.THUMB: None,
                    DB.USE_FLAG: None,
                }
            )

            # ブック一覧HTML出力
            self.output_book_type(books, types, type)

            for book in books:
                chapters = self.db.select_chapter(
                    **{
                        DB.BOOK_ID: book[DB.BOOK_ID],
                        DB.CHAPTER_ID: None,
                        DB.CHAPTER_KEY: None,
                        DB.CHAPTER_URL: None,
                        DB.CHAPTER_NUM: None,
                        DB.CHAPTER_DATE: None,
                        DB.CHAPTER_SINGLE: None,
                    }
                )

                path = unquote(
                    os.path.join(
                        self.BASE_PATH,
                        self.getHash(book[DB.BOOK_KEY]),
                        book[DB.BOOK_KEY],
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
                        self.getHash(book[DB.BOOK_KEY]),
                        book[DB.BOOK_KEY],
                        book[DB.BOOK_KEY] + ".html",
                    ),
                    "SRC": book[DB.THUMB],
                    "FLAG": book[DB.USE_FLAG],
                    "TITLE": (
                        html.escape(book[DB.TITLE], quote=True)
                        if book[DB.TITLE] is not None
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
            "thumb": book[DB.THUMB],
            "title": (
                html.escape(book[DB.TITLE], quote=True)
                if book[DB.TITLE] is not None
                else "未設定"
            ),
            "book_key": book[DB.BOOK_KEY],
            "chapters": [
                {
                    "KEY": chap[DB.CHAPTER_KEY],
                    "HREF": book[DB.BOOK_KEY] + "_" + chap[DB.CHAPTER_KEY] + ".html",
                    "NUM": chap[DB.CHAPTER_NUM],
                    "DATE": chap[DB.CHAPTER_DATE].strftime("%Y年%m月%d日"),
                }
                for chap in sorted(
                    chapters, key=lambda x: x[DB.CHAPTER_KEY], reverse=True
                )
            ],
        }

        with open(
            unquote(os.path.join(path, book[DB.BOOK_KEY] + ".html")), mode="w"
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
                **{
                    DB.CHAPTER_ID: chapter[DB.CHAPTER_ID],
                    DB.PAGE_URL: None,
                    DB.PAGE_SINGLE: None,
                }
            )

            # 単ページから開始するか、
            single_page_start = (
                book[DB.BOOK_SINGLE] != 0 and chapter[DB.CHAPTER_SINGLE] is None
            ) or (
                chapter[DB.CHAPTER_SINGLE] != 0
                and chapter[DB.CHAPTER_SINGLE] is not None
            )

            data = {
                "prev": {
                    "HREF": book[DB.BOOK_KEY] + "_" + prev[DB.CHAPTER_KEY] + ".html",
                    "NUM": prev[DB.CHAPTER_NUM],
                },
                "next": {
                    "HREF": book[DB.BOOK_KEY] + "_" + next[DB.CHAPTER_KEY] + ".html",
                    "NUM": next[DB.CHAPTER_NUM],
                },
                "book_key": book[DB.BOOK_KEY],
                "chapter_key": chapter[DB.CHAPTER_KEY],
                "title": (
                    html.escape(book[DB.TITLE], quote=True)
                    if book[DB.TITLE] is not None
                    else "未設定"
                ),
                "chapter_top": book[DB.BOOK_KEY] + ".html",
                "chapters": [
                    {
                        "KEY": chap[DB.CHAPTER_KEY],
                        "HREF": book[DB.BOOK_KEY]
                        + "_"
                        + chap[DB.CHAPTER_KEY]
                        + ".html",
                        "NUM": chap[DB.CHAPTER_NUM],
                    }
                    for chap in sorted(
                        chapters, key=lambda x: x[DB.CHAPTER_KEY], reverse=True
                    )
                ],
                "pages": [
                    {
                        "URL": page[DB.PAGE_URL],
                        "SINGLE": (
                            (
                                page[DB.PAGE_SINGLE] != 0
                                and page[DB.PAGE_SINGLE] is not None
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
                        book[DB.BOOK_KEY] + "_" + chapter[DB.CHAPTER_KEY] + ".html",
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
