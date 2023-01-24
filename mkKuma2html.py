#!/usr/bin/env python3

import logging
import os
import sys
from DB import DB

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(threadName)s: %(message)s', filename='rawkuma.log')
console = logging.StreamHandler()
console.setFormatter(logging.Formatter('%(asctime)s %(threadName)s: %(message)s'))
logging.getLogger('').addHandler(console)

HEADER='''<html xmlns="https://www.w3.org/1999/xhtml" lang="en-US">
<head>
    <meta charset="utf-8">
    <meta name="referrer" content="no-referrer">
    <style>
        .Header {
            position: sticky;
            /* ヘッダーを固定する */
            top: 0;
            /* 上部から配置の基準位置を決める */
            left: 0;
            /* 左から配置の基準位置を決める */
            width: 100%;
            /* ヘッダーの横幅を指定する */
            height: 15px;
            /* ヘッダーの高さを指定する */
            padding: 10px;
            /* ヘッダーの余白を指定する(上下左右) */
            background-color: #31a9ee;
            /* ヘッダーの背景色を指定する */
            color: #000000;
            /* フォントの色を指定する */
        }

        .Footer {
            width: 100%;
            /* ヘッダーの横幅を指定する */
            height: 15px;
            /* ヘッダーの高さを指定する */
            padding: 10px;
            /* ヘッダーの余白を指定する(上下左右) */
            background-color: #31a9ee;
            /* ヘッダーの背景色を指定する */
            color: #000000;
            /* フォントの色を指定する */
        }

        .Contents img {
            width: 100%;
            /* コンテンツの横幅を指定する */
            overflow: auto;
            /* コンテンツの表示を自動に設定（スクロール） */
            display: block;
            margin: auto;
            /* 中央よせ */
        }

        .chbox {
            background: #efefef;
            background-image: initial;
            background-position-x: initial;
            background-position-y: initial;
            background-size: initial;
            background-repeat-x: initial;
            background-repeat-y: initial;
            background-attachment: initial;
            background-origin: initial;
            background-clip: initial;
            background-color: rgb(239, 239, 239);
            border-color: #efefef;
            border-top-color: rgb(239, 239, 239);
            border-right-color: rgb(239, 239, 239);
            border-bottom-color: rgb(239, 239, 239);
            border-left-color: rgb(239, 239, 239);
        }

        .chbox {
            margin-left: 0;
        }

        .chbox {
            overflow: hidden;
            padding: 5px 10px;
            border: 1px solid #333;
            font-size: 14px;
            margin: 0 5px;
            margin-bottom: 10px;
            position: relative;
            border-radius: 5px;
        }

        .clstyle {
            margin-left: 0;
        }

        .eph-num {
            width: 85%;
        }
        span.chapternum {
            font-weight: 400;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        span.chapterdate {
           font-size: 12px;
            color: #888;
        }

        ul {
            padding: 0;
            list-style: none;
            margin: 0;
            margin-left: -5px;
            overflow: auto;
        }

    </style>
</head>
'''


class MkKuma2Html:
    def __init__(self) -> None:
        self.db = DB(logging)        

    def tohtml(self) -> None:
        lists = self.db.select_book(**{DB.BOOK_TYPE: None})
        types = set([ val[DB.BOOK_TYPE] for val in lists ])

        self.output_book(types)

        for type in types:
            books = self.db.select_book(**{DB.BOOK_KEY: None, DB.TITLE: None, DB.BOOK_TYPE: type, DB.THUMB: None})

            self.output_book_type(books, type)

            for book in books:
                chapters = self.db.select_chapter(book[DB.BOOK_ID])

                path = os.path.join('img{TYPE}'.format(TYPE=book[DB.BOOK_TYPE]), book[DB.BOOK_KEY])
                # print(os.path.join(path, book[DB.BOOK_KEY] + '.html'))

                # ディレクトリ作成
                os.makedirs(path, exist_ok=True)

                self.output_chapter_top(book, path, chapters)

                self.output_chapter(book, path, chapters)

    def output_book(self, types):
        with open('Books.html', mode='w') as i:
            # HTMLヘッダ出力
            i.write(HEADER)

            # HTMLボディ出力
            i.write('<body>\n')
            i.write('<div><ul class="clstyle">')

            for type in types:
                i.write('''
<li>
    <div class=chbox>
        <div class="eph-num">
            <a href="Books{TYPE}.html">
                <span>Type{TYPE}</span>
            </a>
        </div>
    </div>
</li>
'''.format(TYPE=type))

            i.write('</div>\n')
            i.write('</body>\n')
            i.write('</html>\n')

    def output_book_type(self, books, type):
        with open('Books{TYPE}.html'.format(TYPE=type), mode='w') as f:
            # HTMLヘッダ出力
            f.write(HEADER)

            # HTMLボディ出力
            f.write('<body>\n')

            for book in books:
                path = os.path.join('img{TYPE}'.format(TYPE=book[DB.BOOK_TYPE]), book[DB.BOOK_KEY])
                f.write('''
<a href="{CHAPTER_URL}.html">
    <img src="{THUMB}" width="211" height="auto">
</a>
'''.format(CHAPTER_URL=os.path.join(path, book[DB.BOOK_KEY]), THUMB=book[DB.THUMB]))

            f.write('</body>\n')
            f.write('</html>\n')


    def output_chapter_top(self, book, path, chapters):
        with open(os.path.join(path, book[DB.BOOK_KEY] + '.html'), mode='w') as f:
            # HTMLヘッダ出力
            f.write(HEADER)

            # HTMLボディ出力
            f.write('<body>\n')
            f.write('<div><ul class="clstyle">')
            for chap in chapters:
                # print(chapters)
                # print(chap)
                f.write('''
<li>
<div class=chbox>
    <div class="eph-num">
    <a href="{CHAPTER_URL}.html">
        <span class="chapternum">{NUM}</span>
        <span class="chapterdate">{DATE}</span>
    </a>
    </div>
</div>
</li>
                '''.format(
                    CHAPTER_URL=book[DB.BOOK_KEY] + '_' + chap[DB.CHAPTER_KEY],
                    CHAPTER=chap[DB.CHAPTER_KEY],
                    NUM=chap[DB.CHAPTER_NUM],
                    DATE=chap[DB.CHAPTER_DATE].strftime('%Y年%m月%d日')
                ))

            f.write('</ul></div>')
            f.write('</body>\n')
            f.write('</html>\n')

    def output_chapter(self, book, path, chapters):
        max = len(chapters)
        for index, chapter in enumerate(chapters):
            with open(os.path.join(path, book[DB.BOOK_KEY] + '_' + chapter[DB.CHAPTER_KEY] + '.html'), mode='w') as f:
                    # HTMLヘッダ出力
                f.write(HEADER)

                # HTMLボディ出力
                f.write('<body>\n')

                # 画面上のヘッダ出力
                f.write('<div class="Header">\n')

                # 前チャプター移動
                chap = chapters[index - 1]
                f.write('<a href="{CHAPTER_URL}.html">{CHAPTER}</a>\n'.format(
                                CHAPTER_URL=book[DB.BOOK_KEY] + '_' + chap[DB.CHAPTER_KEY], CHAPTER=chap[DB.CHAPTER_KEY]
                            ))

                # チャプター選択
                f.write('<select onChange="location.href=value;">\n')
                cur = 0
                for chap in chapters:
                    cur = cur + 1
                    f.write('<option value="{CHAPTER}.html"{SELECT}>{CUR}/{MAX}</option>\n'.format(
                            CHAPTER=book[DB.BOOK_KEY] + '_' + chap[DB.CHAPTER_KEY], CUR=cur, MAX=max, SELECT=' selected' if chap[DB.CHAPTER_KEY] == chapter[DB.CHAPTER_KEY] else '' ))
                f.write('</select>\n')

                    # 次チャプター移動
                chap = chapters[index + 1] if index + 1 != max else chapters[0]
                f.write('<a href="{CHAPTER_URL}.html">{CHAPTER}</a>\n'.format(
                                CHAPTER_URL=book[DB.BOOK_KEY] + '_' + chap[DB.CHAPTER_KEY], CHAPTER=chap[DB.CHAPTER_KEY]
                            ))

                f.write('</div>\n')

                f.write('<div id="content" class="Contents">\n')

                pages = self.db.select_page(chapter[DB.CHAPTER_ID])
                for page in pages:
                    f.write('<img loading="lazy" src="{URL}">\n'.format(URL=page[DB.PAGE_URL]))

                f.write('</div>')

                    # 画面上フッター 次チャプター移動
                chap = chapters[index + 1] if index + 1 != max else chapters[0]
                f.write('<div class="Footer"><a href="{CHAPTER_URL}.html">{CHAPTER}</a></div>\n'.format(
                                CHAPTER_URL=book[DB.BOOK_KEY] + '_' + chap[DB.CHAPTER_KEY], CHAPTER=chap[DB.CHAPTER_KEY]
                            ))
                f.write('</body>\n')
                f.write('</html>\n')

#
# メイン
#

if __name__ == '__main__':
    if len(sys.argv) > 1:
        url = sys.argv[1]

        print(url)
        kuma = MkKuma2Html()
        kuma.tohtml()
