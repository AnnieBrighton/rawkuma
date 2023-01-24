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

from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
import logging
import re
import sys
from lxml import etree
from requests import session, exceptions
from time import sleep
import traceback

from urllib.parse import quote
from DB import DB

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(threadName)s: %(message)s', filename='rawkuma.log')
console = logging.StreamHandler()
console.setFormatter(logging.Formatter('%(asctime)s %(threadName)s: %(message)s'))
logging.getLogger('').addHandler(console)

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

    # HTMLリストを取得
    def getHTML(self, url):
        # 取得HTMLパース
        return etree.HTML(self.__getHTTP(url).text)


    # JSONを取得
    def getJSON(self, url):
        # 取得HTMLパース
        return self.__getHTTP(url).json()

   

class getHTML(getHTTP):
    def __init__(self, url) -> None:
        self.__html = self.getHTML(url)

    #
    def getImageList(self):
        # イメージリストを取得
        # <img class="ts-main-image curdown" data-index="0" src="https://kumacdn.club/images/s/spy-x-family/chapter-62-3/1-6281c0b1e24d0.jpg"
        #      data-server="Server1" onload="ts_reader_control.singleImageOnload();" onerror="ts_reader_control.imageOnError();">
        # //*[@id="readerarea"]/img[1]
        # //*[@id="readerarea"]/img
        return self.__html.xpath('//*[@id="readerarea"]/noscript/p/img/@src')

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
        return [ val.strip() for val in titles ]

    # Titleを取得
    def getTitle(self):
        # Alternative Titles
        lists = self.__html.xpath('//div[@class="wd-full" and b/text()="Alternative Titles"]/span/text()')
        titles = str(lists[0]).split(',') if len(lists) > 0 else []
        return [ val.strip() for val in titles ]

    def getDescription(self):
        # Synopsis Strategic Lovers
        lists = self.__html.xpath('//div[@class="wd-full" and h2/text()="Synopsis Strategic Lovers"]/dev/p/text()')
        return str(lists[0]).strip() if len(lists) > 0 else ''

    # 登録時刻を取得
    def getPostedOn(self):
        # Posted On
        return datetime.strptime(self.__html.xpath('//time[@itemprop="datePublished"]/@datetime')[0],'%Y-%m-%dT%H:%M:%S%z').astimezone(timezone(timedelta(hours=9)))

    # 更新時刻を取得
    def getUpdatedOn(self):
        # Updated On
        return datetime.strptime(self.__html.xpath('//time[@itemprop="dateModified"]/@datetime')[0],'%Y-%m-%dT%H:%M:%S%z').astimezone(timezone(timedelta(hours=9)))

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
            if val != '':
                json = self.getJSON('https://www.googleapis.com/books/v1/volumes?q=' + quote(val))
                if 'items' in json:
                    for item in json['items']:
                        if item['volumeInfo']['language'] == 'ja':
                            authors = item['volumeInfo']['authors'] if 'authors' in item['volumeInfo'] else []
                            title = item['volumeInfo']['title']
                            r = SequenceMatcher(None, val.strip(), title.strip()).ratio()
                            if r > max and r > 0.7:
                                t = val
                                a = authors
                                max = r

        return t, a



class getKuma2DB:
    def __init__(self) -> None:
        self.db = DB(logging)

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
            self.db.insert_book(**{DB.BOOK_KEY: book_key, DB.URL: url, DB.BOOK_TYPE: type.upper(), DB.USE_FLAG: DB.USE_FLAG_ON})
            self.db.commit()
        else:
            if result[0][DB.BOOK_ID] != type.upper():
                logging.info('{URL} はすでに登録済み。TYPE {OLD} -> {NEW}'.format(URL=url, OLD=result[0][DB.BOOK_TYPE], NEW=type.upper()))
                self.db.update_book(result[0][DB.BOOK_ID], **{DB.BOOK_TYPE: type.upper()})
                self.db.commit()
            else:
                logging.info('{URL} はすでに登録済み。'.format(URL=url))

    def close(self) -> None:
        self.db.close()

    def updatedb(self) -> None:
        self.db.select_book()
        vals = self.db.select_book(**{DB.URL: None, DB.BOOK_KEY: None, DB.KUMA_UPDATED: None, DB.TITLE: None, DB.USE_FLAG: DB.USE_FLAG_ON})

        for val in vals:
            self.updatedb2(val)

    # ダウンロード
    def updatedb2(self, val):
        """ 
        """
        book_id = val[DB.BOOK_ID]
        book_key = val[DB.BOOK_KEY]
        url = val[DB.URL]

        # チャプター情報取得
        html = getHTML(url)
        urls = html.getURLlists()

        kuma_tags = html.getTAGlist()
        kuma_artists = html.getARTIST()
        kuma_title = html.getTitle()
        kuma_post = html.getPostedOn()
        kuma_update = html.getUpdatedOn()
        kuma_thumb = html.getThumbnail()

        # logging.info(url)
        # logging.info(book_key)
        # logging.info(urls)
        # logging.info(kuma_tags)
        # logging.info(kuma_artists)
        # logging.info(kuma_title)
        # logging.info(kuma_post)
        # logging.info(kuma_update)
        # logging.info(kuma_thumb)

        if kuma_update == val[DB.KUMA_UPDATED]:
            logging.info(book_key + 'は更新が無い')
            return

        books = getGooglBooks()
        title, author = books.getTitle(kuma_title)

        data = {
            DB.TITLE: title,
            DB.AUTHOR: ','.join(author),
            DB.THUMB: kuma_thumb,
            DB.KUMA_TITLE: kuma_title[0],
            DB.KUMA_AUTHOR: ','.join(kuma_artists),
            DB.KUMA_TAG: ','.join(kuma_tags),
            DB.KUMA_POSTED: kuma_post,
            DB.KUMA_UPDATED: kuma_update
        }
        self.db.update_book(book_id, **data)

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
                logging.info('すでに存在:{URL}'.format(URL=url[0]))
                continue

            # チャプターレコード作成
            data = {DB.BOOK_ID: book_id,
                    DB.CHAPTER_URL: url[0],
                    DB.CHAPTER_KEY: chapter,
                    DB.CHAPTER_NUM: url[1],
                    DB.CHAPTER_DATE: url[2]}
            chapter_id = self.db.insert_chapter(**data)

            # ページ情報取得
            html = getHTML(url[0])
            imgurls = html.getImageList()

            # ページ登録情報作成
            pagelists = []
            for page, page_url in enumerate(imgurls):
                pagelists.append((chapter_id, page_url, page + 1))

            # ページレコード作成
            self.db.insert_page(pagelists)

        self.db.commit()

        return

    # flag set
    def flagset(self, url, type):
        book_key = re.search(r'^https?://[^/]+/[^/]+/([^/]+)/?$', url)[1]

        book_id = self.db.getBookID(book_key)

        self.db.update_book(book_id, **{DB.USE_FLAG: DB.USE_FLAG_ON if type.upper() == 'ON' else DB.USE_FLAG_OFF})

        self.db.commit()

    # ダウンロード
    def updatedb3(self, book_id, url):
        """ 
        """
        # 「https://rawkuma.com/manga/bakemonogatari/」の形式ならばそのままリストを取得、各リストに対しダウンロードを実行
        # 「https://rawkuma.com/bakemonogatari-chapter-1/」の形式のリストを取得
        html = getHTML(url)
        urls = html.getURLlist()
        if urls is None:
            logging.error('URL取得エラー:%s' % url)
            return

        book_key = re.search(r'^https?://[^/]+/[^/]+/([^/]+)/?$', url)[1]

        kuma_tags = html.getTAGlist()
        kuma_artists = html.getARTIST()
        kuma_title = html.getTitle()
        kuma_post = html.getPostedOn()
        kuma_update = html.getUpdatedOn()
        kuma_thumb = html.getThumbnail()

        # logging.info(url)
        # logging.info(book_key)
        # logging.info(urls)
        # logging.info(kuma_tags)
        # logging.info(kuma_artists)
        # logging.info(kuma_title)
        # logging.info(kuma_post)
        # logging.info(kuma_update)
        # logging.info(kuma_thumb)

        book_id = self.db.getBookID(book_key)
        
        if (book_id is None):
            books = getGooglBooks()
            title, author = books.getTitle(kuma_title)

            data = {
                DB.BOOK_KEY: book_key,
                DB.USE_FLAG: DB.USE_FLAG_ON,
                DB.URL: url,
                DB.TITLE: title,
                DB.AUTHOR: ','.join(author),
                DB.THUMB: kuma_thumb,
                DB.KUMA_TITLE: kuma_title[0],
                DB.KUMA_AUTHOR: ','.join(kuma_artists),
                DB.KUMA_TAG: ','.join(kuma_tags),
                DB.KUMA_POSTED: kuma_post,
                DB.KUMA_UPDATED: kuma_update
            }
            book_id = self.db.insert_book(**data)

        for url in urls:
            # ファイルを展開するパスを作成 (最後に / を含む)
            list = re.search(r'^https?://[^/]+/[^/]+-chapter-([0-9]+)-([0-9]+)/$', url)
            if list:
                chapter = '%04d.%02d' % (int(list.group(1)), int(list.group(2)))
            else:
                list = re.search(r'^https?://[^/]+/[^/]+-chapter-([0-9]+)/$', url)
                if list:
                    chapter = '%04d.00' % int(list.group(1))
                else:
                    continue

            if self.db.check_chapter(book_id, chapter):
                logging.info('すでに存在:{URL}'.format(URL=url))
                continue

            # チャプターレコード作成
            chapter_id = self.db.insert_chapter(book_id, url, chapter)

            # ページ情報取得
            html = getHTML(url)
            imgurls = html.getImageList()

            # ページ登録情報作成
            pagelists = []
            for page, page_url in enumerate(imgurls):
                pagelists.append((chapter_id, page_url, page + 1))

            # ページレコード作成
            self.db.insert_page(pagelists)

        self.db.commit()

        return


#
# メイン
#

if __name__ == '__main__':
    if len(sys.argv) == 3:
        url = sys.argv[1]
        type = sys.argv[2]
        logging.info('URL={URL}, TYPE={TYPE}'.format(URL=url, TYPE=type))

        kuma = getKuma2DB()
        if type.upper() == 'ON' or type.upper() == 'OFF':
            kuma.flagset(url, type)
        else:
            kuma.addbook(url, type)
        kuma.close()

    elif len(sys.argv) == 1:
        kuma = getKuma2DB()
        kuma.updatedb()
        kuma.close()

    else:
        logging.info('引数誤り')
