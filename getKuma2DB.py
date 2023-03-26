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
import aiohttp
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
import logging
import re
import sys
from lxml import etree
from requests import session, exceptions
from time import sleep
import traceback
import unicodedata
from Chrome import Chrome, ChromeTab

from urllib.parse import quote
from DB import DB

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(threadName)s: %(message)s', filename='rawkuma.log')
console = logging.StreamHandler()
console.setFormatter(logging.Formatter('%(asctime)s %(threadName)s: %(message)s'))
logging.getLogger('').addHandler(console)

#


def func_hook(func):
    def wrapper(*arg, **kwargs):
        logging.info('call %s' % (func.__name__))
        ret = func(*arg, **kwargs)
        logging.info('return %s' % (func.__name__))
        return ret
    return wrapper


class getHTTP:
    # HTMLリストを取得
    def __getHTTP(self, url):
        """_summary_

        Args:
            url (_type_): _description_

        Returns:
            _type_: HTML
        """

        imgreq = session()
        imgreq.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'Accept-Encoding': 'gzip',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        }

        for _ in range(0, 10):
            try:
                # HTML情報取得
                response = imgreq.get(url)

                if response.status_code == 200:
                    # 取得HTMLパース
                    return response
                else:
                    print('Status Error ' + str(response.status_code) + ':' + url)
                    return None

            except exceptions.ConnectionError:
                print('ConnectionError:' + url)
            except exceptions.Timeout:
                print('Timeout:' + url)
            except Exception as e:
                print(e)
                print(traceback.format_exc())
                return None

            # リトライ前に2秒待つ
            sleep(2)

        return None

    # JSONを取得
    def getJSON(self, url):
        # 取得HTMLパース
        return self.__getHTTP(url).json()


class rawkumaHTML():
    def __init__(self, text=None) -> None:
        self.__html = etree.HTML(text)

    #
    def getImageList(self):
        # イメージリストを取得
        # <img class="ts-main-image curdown" data-index="0" src="https://kumacdn.club/images/s/spy-x-family/chapter-62-3/1-6281c0b1e24d0.jpg"
        #      data-server="Server1" onload="ts_reader_control.singleImageOnload();" onerror="ts_reader_control.imageOnError();">
        # //*[@id="readerarea"]/img[1]
        return self.__html.xpath('//*[@id="readerarea"]/img/@src')

    # URLリストを取得
    def getURLlist(self):
        # チャプターリストを取得
        # //*[@id="chapterlist"]/ul/li/div/div[1]/a
        # //*[@id="chapterlist"]/ul/li/div/div[@class="eph-num"]/a
        return self.__html.xpath('//*[@id="chapterlist"]/ul/li/div/div[@class="eph-num"]/a/@href')

    # URLリストを取得
    def getURLlists(self):
        # チャプターリストを取得
        # //*[@id="chapterlist"]/ul/li/div/div[1]/a
        # //*[@id="chapterlist"]/ul/li/div/div[@class="eph-num"]/a
        lists = self.__html.xpath('//*[@id="chapterlist"]/ul/li/div/div[@class="eph-num"]')

        vals = []
        for list in lists:
            href = list.xpath('./a/@href')
            nums = list.xpath('./a/span[@class="chapternum"]/text()')
            dates = list.xpath('./a/span[@class="chapterdate"]/text()')
            vals.append((href[0] if len(href) != 0 else None,
                         nums[0] if len(nums) != 0 else None,
                         datetime.strptime(dates[0], '%B %d, %Y') if len(dates) != 0 else None))
        return vals

    # TAGリストを取得
    def getTAGlist(self):
        # Genres:情報を取得
        # //*[@id="post-920"]/div[2]/div[1]/div[2]/div[8]/span/a
        # //*[@id="post-920"]/div[2]/div[1]/div[2]/div[@class="wd-full"]/span/a/text()
        # //*[@id="post-5342"]/div[2]/div[1]/div[2]/div[7]/span/a[1]
        # //*div[@id="content"]/div/div[@class="postbody"]/article/div[2]/div[1]/div[2]/div[@class="wd-full"]/span/a
        return self.__html.xpath('//*[@class="infox"]/div[@class="wd-full"]/span[@class="mgen"]/a/text()')

    # artistリストを取得
    def getARTIST(self):
        # Artist
        lists = self.__html.xpath('//div[@class="fmed" and b/text()="Artist"]/span/text()')
        titles = str(lists[0]).split(',') if len(lists) > 0 else []
        return [val.strip() for val in titles]

    # Titleを取得
    def getTitle(self):
        # Alternative Titles
        lists = self.__html.xpath('//div[@class="wd-full" and b/text()="Alternative Titles"]/span/text()')
        titles = str(lists[0]).split(',') if len(lists) > 0 else []
        return [val.strip() for val in titles]

    def getDescription(self):
        # Synopsis Strategic Lovers
        lists = self.__html.xpath('//div[@class="wd-full"]/div[@itemprop="description"]/p/text()')
        return '\n'.join([str(var).strip() for var in lists])

    # 登録時刻を取得
    def getPostedOn(self):
        # Posted On
        return datetime.strptime(self.__html.xpath('//time[@itemprop="datePublished"]/@datetime')[0],
                                 '%Y-%m-%dT%H:%M:%S%z').astimezone(timezone(timedelta(hours=9)))

    # 更新時刻を取得
    def getUpdatedOn(self):
        # Updated On
        return datetime.strptime(self.__html.xpath('//time[@itemprop="dateModified"]/@datetime')[0],
                                 '%Y-%m-%dT%H:%M:%S%z').astimezone(timezone(timedelta(hours=9)))

    def getThumbnail(self):
        return self.__html.xpath('//div[@class="thumbook"]/div[@class="thumb"]/img/@src')[0]


class getGooglBooks(getHTTP):
    def __init__(self) -> None:
        pass

    def getTitle(self, kuma_title):
        max = 0.0
        t = None
        a = []
        for val in kuma_title:
            if val == '':
                continue

            json = self.getJSON('https://www.googleapis.com/books/v1/volumes?q=intitle:' + quote(val))
            if 'items' in json:
                for item in json['items']:
                    if item['volumeInfo']['language'] == 'ja':
                        authors = item['volumeInfo']['authors'] if 'authors' in item['volumeInfo'] else []
                        title = item['volumeInfo']['title']
                        # 正規化形式:NFC に統一して比較
                        r = SequenceMatcher(None,
                                            unicodedata.normalize('NFC', val.strip()),
                                            unicodedata.normalize('NFC', re.sub(' [0-9]+ ?$', '', title.strip()))).ratio()
                        if r > max and r > 0.7:
                            t = val
                            a = authors
                            max = r

        return t, a


class getKuma2DB:
    BASE_PATH = 'Books'
    LIMITS = 15

    def __init__(self) -> None:
        self.db = DB(logging)
        self.chrome = None

    @func_hook
    def addbook(self, url, type) -> None:
        # urlが最後/で終わる場合、/を取り除く
        url = re.sub(r'/$', '', url)

        # 「https://rawkuma.com/manga/bakemonogatari/」の形式ならば、
        if re.search(r'^(https?://[^/]+/[^/]+/[^/]+)/?$', url) is None:
            # ダウンロードできるURLでないため終了
            logging.error('URL形式エラー:%s' % url)
            return

        book_key = re.search(r'^https?://[^/]+/[^/]+/([^/]+)/?$', url)[1]

        result = self.db.select_book(**{DB.BOOK_KEY: book_key, DB.BOOK_TYPE: None})
        logging.info(result)

        if len(result) == 0:
            self.db.insert_book(**{DB.BOOK_KEY: book_key, DB.URL: url, DB.BOOK_TYPE: type.upper(),
                                DB.USE_FLAG: DB.USE_FLAG_UPDATE, DB.KUMA_UPDATED: '1900-01-01 00:00:00+09:00'})
            self.db.commit()
        else:
            if result[0][DB.BOOK_TYPE] != type.upper():
                logging.info('{URL} はすでに登録済み。TYPE {OLD} -> {NEW}'.format(URL=url, OLD=result[0][DB.BOOK_TYPE], NEW=type.upper()))
                self.db.update_book(result[0][DB.BOOK_ID], **{DB.BOOK_TYPE: type.upper()})
                self.db.commit()

                # チャプター格納ディレクトリ作成
                os.makedirs(os.path.join(self.BASE_PATH, 'img{TYPE}'.format(TYPE=type.upper())), exist_ok=True)

                #
                olddir = os.path.join(self.BASE_PATH, 'img{TYPE}'.format(TYPE=result[0][DB.BOOK_TYPE]), result[0][DB.BOOK_KEY])
                if os.path.isdir(olddir):
                    newdir = os.path.join(self.BASE_PATH, 'img{TYPE}'.format(TYPE=type.upper()), result[0][DB.BOOK_KEY])

                    logging.info('{OLD} -> {NEW}'.format(OLD=olddir, NEW=newdir))
                    os.rename(olddir, newdir)

            else:
                logging.info('{URL} はすでに登録済み。'.format(URL=url))

    def close(self) -> None:
        self.db.close()

    @func_hook
    async def getTEXT4HTML(self, url) -> str:
        tab = ChromeTab(self.chrome)
        await tab.open()
        await tab.get(url)
        text = await tab.getDOM()
        await tab.close()
        return text

    # ダウンロード

    @func_hook
    async def updatedb2(self, val):
        """ 
        """
        book_id = val[DB.BOOK_ID]
        book_key = val[DB.BOOK_KEY]
        url = val[DB.URL]

        # チャプター情報取得
        logging.info('get book info {URL}'.format(URL=val[DB.URL]))
        html = rawkumaHTML(await self.getTEXT4HTML(val[DB.URL]))

        urls = html.getURLlists()

        kuma_tags = html.getTAGlist()
        kuma_artists = html.getARTIST()
        kuma_titles = html.getTitle()
        kuma_post = html.getPostedOn()
        kuma_update = html.getUpdatedOn()
        kuma_thumb = html.getThumbnail()
        kuma_description = html.getDescription()

        if kuma_update == val[DB.KUMA_UPDATED]:
            # 取得更新日付とDB上の更新日付が同じ
            logging.info('{BOOK}は更新が無い'.format(BOOK=book_key))
            return

        logging.info('{BOOK}更新'.format(BOOK=book_key))

        data = {
            DB.THUMB: kuma_thumb,
            DB.KUMA_TITLE: ','.join(kuma_titles),
            DB.KUMA_AUTHOR: ','.join(kuma_artists),
            DB.KUMA_TAG: ','.join(kuma_tags),
            DB.KUMA_DESCRIPTION: kuma_description,
            DB.KUMA_POSTED: kuma_post,
            DB.KUMA_UPDATED: kuma_update
        }

        if val[DB.TITLE] is None or val[DB.TITLE] == '':
            books = getGooglBooks()
            title, author = books.getTitle(kuma_titles)
            data[DB.TITLE] = title
            data[DB.AUTHOR] = ','.join(author)

        self.db.update_book(book_id, **data)

        page_vals = []
        for url in urls:
            # ファイルを展開するパスを作成 (最後に / を含む)
            list = re.search(r'^https?://[^/]+/[^/]+-chapter-([0-9]+)-([0-9]+)/$', url[0])
            if list:
                chapter = '%04d.%02d' % (int(list.group(1)), int(list.group(2)))
            else:
                list = re.search(r'^https?://[^/]+/[^/]+-chapter-([0-9]+)/$', url[0])
                if list:
                    chapter = '%04d.00' % int(list.group(1))
                else:
                    continue

            if self.db.check_chapter(book_id, chapter):
                # logging.info('すでに存在:{URL}'.format(URL=url[0]))
                continue

            # チャプターレコード作成
            data = {DB.BOOK_ID: book_id,
                    DB.CHAPTER_URL: url[0],
                    DB.CHAPTER_KEY: chapter,
                    DB.CHAPTER_NUM: url[1],
                    DB.CHAPTER_DATE: url[2]}
            chapter_id = self.db.insert_chapter(**data)

            page_vals.append({DB.CHAPTER_ID: chapter_id, DB.CHAPTER_URL: url[0]})

        @func_hook
        async def getChapterHTML(val):
            # ページ情報取得
            logging.info('get chapter info {URL}'.format(URL=val[DB.CHAPTER_URL]))
            html = rawkumaHTML(await self.getTEXT4HTML(val[DB.CHAPTER_URL]))

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

    @func_hook
    async def updatedb(self) -> None:
        """ DB更新
        """
        # DBの更新対象を、USEフラグがONで、かつ、更新日が7日より前のBOOK
        before_week = datetime.now(timezone(timedelta(hours=9), 'JST')) - timedelta(days=7)
        vals = self.db.select_book(
            **
            {DB.URL: None, DB.BOOK_KEY: None, DB.KUMA_UPDATED: before_week.date().strftime('%Y-%m-%d'),
             DB.TITLE: None, DB.USE_FLAG: DB.USE_FLAG_UPDATE})

        newvals = []
        self.chrome = Chrome(logging)
        await self.chrome.start()

        @func_hook
        async def getHTML(val):
            html = etree.HTML(await self.getTEXT4HTML(val[DB.URL]))

            update = datetime.strptime(html.xpath('//time[@itemprop="dateModified"]/@datetime')
                                       [0], '%Y-%m-%dT%H:%M:%S%z').astimezone(timezone(timedelta(hours=9)))
            logging.info(f'更新日時 {val[DB.BOOK_KEY]} {update} {val[DB.KUMA_UPDATED]}')

            # DBの更新日時とチャプターページの更新日時が異なるブックを更新対象に追加
            if update != val[DB.KUMA_UPDATED]:
                newvals.append(val)

        sem = asyncio.Semaphore(self.LIMITS)

        async def call(val):
            async with sem:
                return await getHTML(val)

        await asyncio.gather(*[call(val) for val in vals])

        for val in newvals:
            logging.info(f'新規更新 {val[DB.BOOK_KEY]}')
            await self.updatedb2(val)

        await asyncio.sleep(10)

        await self.chrome.stop()

    def get_id(self, url) -> str:
        lists = re.search(r'^https?://[^/]+/[^/]+/([^/]+)/?$', url)
        return url if lists is None else lists[1]

    # flag set
    @func_hook
    def flagset(self, url, type) -> None:
        """USEフラグ変更
        Args:
            url (_type_): BOOK URL
            type (_type_): 変更後のUSEフラグ
        """
        book_key = self.get_id(url)
        book_id = self.db.getBookID(book_key)

        if type.upper() == 'ON':
            flag = DB.USE_FLAG_UPDATE
        elif type.upper() == 'OFF':
            flag = DB.USE_FLAG_COMPLETED
        elif type.upper() == 'STOP':
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
        book_key = self.get_id(url)

        vals = self.db.select_book(**{DB.URL: None, DB.BOOK_KEY: book_key, DB.BOOK_TYPE: None, DB.TITLE: None, DB.USE_FLAG: None})
        for val in vals:
            print(f'{val[DB.BOOK_KEY]}={val[DB.BOOK_TYPE]} {val[DB.URL]} {val[DB.TITLE]}')

    @func_hook
    def clean(self, url) -> None:
        """チャプター、ページ情報削除
        Args:
            url (_type_): BOOK URL
        """
        book_key = self.get_id(url)
        vals = self.db.select_book(**{DB.URL: None, DB.BOOK_ID: None, DB.BOOK_KEY: book_key})

        for val in vals:
            self.db.delete_chapter(val[DB.BOOK_ID])
        self.db.commit()

    @func_hook
    def delete(self, url) -> None:
        """BOOK削除
        Args:
            url (_type_): BOOK URL
        """
        book_key = self.get_id(url)
        self.db.delete_book(book_key)
        self.db.commit()

    @func_hook
    async def update(self, url) -> None:
        """BOOK情報更新
        Args:
            url (_type_): BOOK URL
        """
        book_key = self.get_id(url)
        vals = self.db.select_book(**{DB.URL: None, DB.BOOK_KEY: book_key, DB.KUMA_UPDATED: None, DB.TITLE: None, DB.USE_FLAG: None})

        self.chrome = Chrome(logging)
        await self.chrome.start()

        for val in vals:
            logging.info(f'新規更新 {val[DB.BOOK_ID]} {val[DB.BOOK_KEY]}')
            val[DB.KUMA_UPDATED] = '1900-01-01 00:00:00+09:00'
            await self.updatedb2(val)

        await asyncio.sleep(10)
        await self.chrome.stop()

    @func_hook
    def update_title(self, url, title) -> None:
        """TITLE情報更新
        Args:
            url (_type_): BOOK URL
        """
        book_id = self.db.getBookID(self.get_id(url))

        self.db.update_book(book_id, **{DB.TITLE: title})

        self.db.commit()


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
        kuma = getKuma2DB()
        kuma.printinfo(sys.argv[1])
        kuma.close()

    elif len(sys.argv) >= 3:
        url = sys.argv[1]
        type = sys.argv[2]
        logging.info('URL={URL}, TYPE={TYPE}'.format(URL=url, TYPE=type))

        kuma = getKuma2DB()
        if type.upper() == 'ON' or type.upper() == 'OFF' or type.upper() == 'STOP':
            # USEフラグ変更
            kuma.flagset(url, type)
        elif len(type) == 1 and 'A' <= type[0].upper() and type[0].upper() <= 'Z':
            # テーブル登録
            kuma.addbook(url, type)
        elif type.upper() == 'CLEAN':
            kuma.clean(url)
        elif type.upper() == 'DELETE':
            kuma.delete(url)
        elif type.upper() == 'UPDATE':
            asyncio.run(kuma.update(url))
        elif type.upper() == 'TITLE' and len(sys.argv) == 4:
            kuma.update_title(url, sys.argv[3])
        else:
            logging.info('{TYPE} error'.format(TYPE=type))
        kuma.close()


if __name__ == '__main__':
    main()
