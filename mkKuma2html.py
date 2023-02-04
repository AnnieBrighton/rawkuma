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
        .HeaderPage {
            position: sticky;
            /* ヘッダーを固定する */
            top: 0;
            /* 上部から配置の基準位置を決める */
            left: 0;
            /* 左から配置の基準位置を決める */
            width: 100%;
            /* ヘッダーの横幅を指定する */
            /* height: 15px; */
            /* ヘッダーの高さを指定する */
            padding: 2px;
            /* ヘッダーの余白を指定する(上下左右) */
            background-color: #31a9ee;
            /* ヘッダーの背景色を指定する */
            color: #000000;
            /* フォントの色を指定する */
            font-family:  "ヒラギノ角ゴ ProN W3", HiraKakuProN-W3, 游ゴシック, "Yu Gothic", メイリオ, Meiryo, Verdana, Helvetica, Arial, sans-serif;
            display: flex;
        }

        .HeaderBook {
            position: sticky;
            /* ヘッダーを固定する */
            top: 0;
            /* 上部から配置の基準位置を決める */
            left: 0;
            /* 左から配置の基準位置を決める */
            width: 100%;
            /* ヘッダーの横幅を指定する */
            height: auto;
            /* ヘッダーの高さを指定する */
            padding: 10px;
            /* ヘッダーの余白を指定する(上下左右) */
            background-color: #31a9ee;
            /* ヘッダーの背景色を指定する */
            color: #000000;
            /* フォントの色を指定する */
        }

        /*左と右を囲う全体のエリア*/
        .wrapper{
            position: relative;/*position stickyの基点にするため relativeをかける*/
            display: flex;/*左エリア、右エリア横並び指定*/
            flex-wrap: wrap;/*ボックスの折り返し可*/
        }

        .ChapterHeader {
            /*左固定記述*/
            position: -webkit-sticky;/*Safari用*/
            position: sticky;
            /* ヘッダーを固定する */
            top: 0;
            /* 上部から配置の基準位置を決める */
            left: 0;
            /* 左から配置の基準位置を決める */
            width: 47%;
            /* ヘッダーの横幅を指定する */
            height: 100%;
            /* ヘッダーの高さを指定する */
            padding: 10px;
            /* ヘッダーの余白を指定する(上下左右) */
            background-color: #31a9ee;
            /* ヘッダーの背景色を指定する */
            color: #000000;
            /* フォントの色を指定する */
            float:left;
        }

        .ChapterList {
            position: -webkit-sticky;/*Safari用*/
            position: sticky;
            /* ヘッダーを固定する */
            top: 0;
            /* 上部から配置の基準位置を決める */
            left: 0;
            /* 左から配置の基準位置を決める */
            width: 47%;
            /* ヘッダーの横幅を指定する */
            height: 100%;
            /* ヘッダーの高さを指定する */
            padding: 10px;
            /* ヘッダーの余白を指定する(上下左右) */
            background-color: #31a9ee;
            /* ヘッダーの背景色を指定する */
            color: #000000;
            /* フォントの色を指定する */
            float:right;
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
            font-size: 24px;
            margin: 0 5px;
            margin-bottom: 10px;
            position: relative;
            border-radius: 5px;
            font-family:  "ヒラギノ角ゴ ProN W3", HiraKakuProN-W3, 游ゴシック, "Yu Gothic", メイリオ, Meiryo, Verdana, Helvetica, Arial, sans-serif;
        }

        .clstyle {
            margin-left: 0;
        }

        .eph-num {
            width: 100%;
        }
        span.chapternum {
            font-weight: 400;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        span.chapterdate {
           font-size: 18px;
        }

        ul {
            padding: 0;
            list-style: none;
            margin: 0;
            margin-left: -5px;
            overflow: auto;
        }

        a img {
            vertical-align: top;
        }

        div.title {
            width: 70%; /* 要素の横幅を指定 */
            white-space: nowrap; /* 横幅のMAXに達しても改行しない */
            overflow: hidden; /* ハミ出した部分を隠す */
            text-overflow: ellipsis; /* 「…」と省略 */
            -webkit-text-overflow: ellipsis; /* Safari */
            -o-text-overflow: ellipsis; /* Opera */            
        }
        
        select {
            font-size: 14px;
        }
    </style>
</head>
'''


class MkKuma2Html:
    def __init__(self) -> None:
        self.db = DB(logging)        

    def tohtml(self) -> None:
        """ HTML出力
        """
        lists = self.db.select_book(**{DB.BOOK_TYPE: None})
        types = sorted(set([ val[DB.BOOK_TYPE] for val in lists ]))

        # タイプリストHTML出力
        self.output_book(types)

        for type in types:
            books = self.db.select_book(**{DB.BOOK_KEY: None, DB.TITLE: None, DB.BOOK_TYPE: type, DB.THUMB: None})

            # ブック一覧HTML出力
            self.output_book_type(books, types, type)

            for book in books:
                chapters = self.db.select_chapter(book[DB.BOOK_ID])

                path = os.path.join('img{TYPE}'.format(TYPE=book[DB.BOOK_TYPE]), book[DB.BOOK_KEY])
                # print(os.path.join(path, book[DB.BOOK_KEY] + '.html'))

                # チャプター格納ディレクトリ作成
                os.makedirs(path, exist_ok=True)

                # チャプター一覧HTML出力
                self.output_chapter_top(type, book, path, chapters)

                # チャプターHTML出力
                self.output_chapter(book, path, chapters)

    def output_book(self, types):
        """ トップの Books.html を作成

        Args:
            types ( list ): タイプのリスト
        """
        with open('Books.html', mode='w') as f:
            # HTMLヘッダ出力
            f.write(HEADER)

            # HTMLボディ出力
            f.write('<body>\n')
            f.write('<div class="chbox">')
            f.write('<ul class="clstyle">')

            for type in types:
                f.write('''
<li>
    <div class=chbox>
        <div class="eph-num">
            <a href="Books{TYPE}.html">
                <span> Type{TYPE} </span>
            </a>
        </div>
    </div>
</li>
'''.format(TYPE=type))

            f.write('</div>\n')
            f.write('</body>\n')
            f.write('</html>\n')

    def output_book_type(self, books, types, type):
        """ タイプのブック一覧表示

        Args:
            books (_type_): ブックリスト
            types (_type_): タイプリスト
            type (_type_): タイプ
        """
        with open('Books{TYPE}.html'.format(TYPE=type), mode='w') as f:
            # HTMLヘッダ出力
            f.write(HEADER)

            # HTMLボディ出力
            f.write('<body>\n')

            # 画面上のヘッダ出力
            f.write('<div class="HeaderBook">\n')
            f.write('<div class="chbox">\n')
            f.write('<tr>\n')

            for t in types:
                f.write('''<th><a href="Books{TYPE}.html">Type{TYPE}</a></th>'''.format(TYPE=t))

            f.write('</tr>\n')
            f.write('</div>\n')
            f.write('</div>\n')

            f.write('<div>')

            for book in books:
                path = os.path.join('img{TYPE}'.format(TYPE=book[DB.BOOK_TYPE]), book[DB.BOOK_KEY])
                f.write('''
<a href="{CHAPTER_URL}.html">
    <img src="{THUMB}" width="200" height="auto">
</a>
'''.format(CHAPTER_URL=os.path.join(path, book[DB.BOOK_KEY]), THUMB=book[DB.THUMB]))

            f.write('</div>')
            f.write('</body>\n')
            f.write('</html>\n')


    def output_chapter_top(self, type, book, path, chapters):
        """_summary_

        Args:
            type (_type_): _description_
            book (_type_): _description_
            path (_type_): _description_
            chapters (_type_): _description_
        """
        with open(os.path.join(path, book[DB.BOOK_KEY] + '.html'), mode='w') as f:
            # HTMLヘッダ出力
            f.write(HEADER)

            # HTMLボディ出力
            f.write('<body">\n')
            f.write('''
  <script type="text/javascript">
    function setStyle() {{
        const item = localStorage.getItem("{KEY}");
        var tags = document.getElementsByClassName("type-" + item);
        len = tags.length|0;
        for (i = 0; i < len; i = i + 1) {{
            tags[i].style.background = "#A09080";
        }}
    }}
  </script>'''.format(KEY=book[DB.BOOK_KEY]))

            # 画面上のヘッダ出力
            f.write('<div class="HeaderPage">\n')
            f.write('<a href="../../Books{TYPE}.html"><span>ブックリストに戻る</span></a>\n'.format(TYPE=type))
            f.write('</div>\n')

            f.write('<div class="wrapper">')
            f.write('<div class="ChapterHeader">')
            f.write('<img src="{THUMB}" width="80%"><br><span class="chbox"> {TITLE} </span>\n'.format(THUMB=book[DB.THUMB], TITLE=book[DB.TITLE]))
            f.write('</div>')

            f.write('<div class="ChapterList">')
            f.write('<ul class="clstyle">')
            for chap in sorted(chapters, key=lambda x: x[DB.CHAPTER_KEY], reverse=True):
                # print(chapters)
                # print(chap)
                f.write('''
<li>
<div class="chbox type-{CCS}">
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
                    CCS=chap[DB.CHAPTER_KEY].replace('.', '-'),
                    NUM=chap[DB.CHAPTER_NUM],
                    DATE=chap[DB.CHAPTER_DATE].strftime('%Y年%m月%d日')
                ))

            f.write('</ul></div>')
            f.write('</div>')
            f.write('<script type="text/javascript">setStyle();</script>')
            f.write('</body>\n')
            f.write('</html>\n')

    def output_chapter(self, book, path, chapters):
        """_summary_

        Args:
            book (_type_): _description_
            path (_type_): _description_
            chapters (_type_): チャプターリスト
        """
        max = len(chapters)
        for index, chapter in enumerate(chapters):
            with open(os.path.join(path, book[DB.BOOK_KEY] + '_' + chapter[DB.CHAPTER_KEY] + '.html'), mode='w') as f:
                    # HTMLヘッダ出力
                f.write(HEADER)

                # HTMLボディ出力
                f.write('<body>\n')

                # 画面上のヘッダ出力
                f.write('<div class="HeaderPage">\n')

                # 前チャプター移動
                chap = chapters[index - 1]
                f.write('<div>\n')
                f.write('<a href="{CHAPTER_URL}.html">{CHAPTER}</a>\n'.format(
                                CHAPTER_URL=book[DB.BOOK_KEY] + '_' + chap[DB.CHAPTER_KEY], CHAPTER=chap[DB.CHAPTER_KEY]
                            ))
                f.write('</div>\n')

                # チャプター選択
                f.write('<div>\n')
                f.write('<select onChange="location.href=value;">\n')
                f.write('<option value="{CHAPTER}.html">Cahpter List</option>\n'.format(CHAPTER=book[DB.BOOK_KEY]))
                for chap in chapters:
                    f.write('<option value="{CHAPTER}.html"{SELECT}>{NUM}</option>\n'.format(
                            CHAPTER=book[DB.BOOK_KEY] + '_' + chap[DB.CHAPTER_KEY],
                            NUM=chap[DB.CHAPTER_NUM],
                            SELECT=' selected' if chap[DB.CHAPTER_KEY] == chapter[DB.CHAPTER_KEY] else '' ))
                f.write('</select>\n')
                f.write('</div>\n')

                f.write('<div class="title">\n')
                f.write('<span> {TITLE} </span>\n'.format(TITLE=book[DB.TITLE]))
                f.write('</div>\n')

                # 次チャプター移動
                chap = chapters[index + 1] if index + 1 != max else chapters[0]
                f.write('<div>\n')
                f.write('<a href="{CHAPTER_URL}.html">{CHAPTER}</a>\n'.format(
                                CHAPTER_URL=book[DB.BOOK_KEY] + '_' + chap[DB.CHAPTER_KEY], CHAPTER=chap[DB.CHAPTER_KEY]
                            ))
                f.write('</div>\n')
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
                # ブラウザlocalStrageにチャプターキーを保存
                f.write('''
<script type="text/javascript">
    localStorage.setItem("{BOOK_KEY}", "{CHAPTER_KEY}");
</script>'''.format(BOOK_KEY=book[DB.BOOK_KEY], CHAPTER_KEY=chapter[DB.CHAPTER_KEY].replace('.', '-')))

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
