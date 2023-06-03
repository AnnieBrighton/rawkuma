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

from kingrawHTML import kingrawHTML
from rawkumaHTML import rawkumaHTML
from rawuwuHTML import rawuwuHTML
from senmangaHTML import senmangaHTML
from difflib import SequenceMatcher
import re
from requests import session, exceptions
from time import sleep
import traceback
import unicodedata
import logging

from urllib.parse import quote


class analyzeHTML:
    HTMLCLASS = [rawkumaHTML, kingrawHTML, rawuwuHTML, senmangaHTML]

    def __init__(self, url=None, chrome=None) -> None:
        self.html = None
        if url is not None:
            for html in self.HTMLCLASS:
                if html.isMatchURL(url):
                    self.html = html(chrome)
                    return

            logging.info("マッチするドメインが見つかりません。url={url}".format(url=url))

    def getHTML(self):
        return self.html

    def getBookKey(self, url):
        for html in self.HTMLCLASS:
            key = html.getBookKey(url)
            if key is not None:
                return key

        return url

    def getUpdateListUrl(self, limit):
        lists = []
        for html in self.HTMLCLASS:
            lists.extend(html.getUpdateListUrl(limit))

        return lists


class getGooglBooks:
    def __init__(self) -> None:
        pass

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
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Encoding": "gzip",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        }

        for _ in range(0, 10):
            try:
                # HTML情報取得
                response = imgreq.get(url)

                if response.status_code == 200:
                    # 取得HTMLパース
                    return response
                else:
                    print("Status Error " + str(response.status_code) + ":" + url)
                    return None

            except exceptions.ConnectionError:
                print("ConnectionError:" + url)
            except exceptions.Timeout:
                print("Timeout:" + url)
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

    def getTitle(self, kuma_title):
        max = 0.0
        t = None
        a = []
        for val in kuma_title:
            if val == "":
                continue

            json = self.getJSON(
                "https://www.googleapis.com/books/v1/volumes?q=intitle:" + quote(val)
            )
            if "items" in json:
                for item in json["items"]:
                    if item["volumeInfo"]["language"] == "ja":
                        authors = (
                            item["volumeInfo"]["authors"]
                            if "authors" in item["volumeInfo"]
                            else []
                        )
                        title = item["volumeInfo"]["title"]
                        # 正規化形式:NFC に統一して比較
                        r = SequenceMatcher(
                            None,
                            unicodedata.normalize("NFC", val.strip()),
                            unicodedata.normalize(
                                "NFC", re.sub(" [0-9]+ ?$", "", title.strip())
                            ),
                        ).ratio()
                        if r > max and r > 0.7:
                            t = val
                            a = authors
                            max = r

        return t, a
