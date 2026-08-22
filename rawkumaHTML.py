#!/usr/bin/env python3

import asyncio
import re
from urllib.parse import unquote
from booksHTML import HTMLinterface, getHTML
from zoneinfo import ZoneInfo
from Chrome import ChromeTab
from lxml import etree
from datetime import datetime, timedelta
from typing import Dict, List

class rawkumaHTML(getHTML, HTMLinterface):
    def __init__(self, chrome) -> None:
        super().__init__(chrome)
        self.html2 = None

    async def getTEXT4HTML(self, url) -> None:
        tab = ChromeTab(self.chrome)
        await tab.open()
        await tab.get(url, timeout=120000)

        self.html = etree.HTML(await tab.getDOM())
        self.html2 = None

        await asyncio.sleep(2)

        # Synopsis, Chapters, Reviews, GalleryのTabが存在するか確認するために、Chaptersの存在を確認
        elements = await tab.find_elements(path='//button[@id="tab-description" and @data-key="chapters"]')
        if elements:
            # Chaptersが存在すれば、Chaptersをクリックし画面を更新
            await tab.click(path='//button[@id="tab-description" and @data-key="chapters"]', by = tab.By.XPATH)

            # Chapter Listが表示されることを確認
            try:
                await tab.find_elements(path='//div[@id="chapter-list"]/div/a', timeout=180)
                self.html2 = etree.HTML(await tab.getDOM())
            except Exception:
                pass

        await tab.close()
        return

    # URLが自身とマッチ判定
    def isMatchURL(url):
        return re.match(r"^https?://rawkuma\.(com|net)/", url)

    # 漫画リストURLからbookeyを取得
    def getBookKey(url):
        """
        「https://rawkuma.com/manga/oshi-no-ko/」 → 「oshi-no-ko」
        """
        types = [
            r"^https?://rawkuma.com/manga/([^/]+)/?$",
            r"^https?://rawkuma.net/manga/([^/]+)/?$",
        ]

        for type in types:
            lists = re.search(type, url)
            if lists is not None:
                return lists[1]

        return None

    # 漫画リストページURLリスト取得
    def getUpdateListUrl(limit):
        return [
            f"https://rawkuma.net/latest-update/?the_page={page}"
            for page in range(1, limit + 1)
        ]

    #
    def getImageList(self):
        # イメージリストを取得
        # /html/body/main/div[1]/div/div[4]/section/section/img
        return self.html.xpath('//div[@class="relative"]/section/section/img/@src')

    # URLリストを取得
    def getURLlists(self):
        if self.html2 is None:
            # チャプター情報未取得の場合、空リストを返す
            return []

        # チャプターリストを取得
        # //*[@id="chapter-list"]/div
        lists = self.html2.xpath(
            '//*[@id="chapter-list"]/div'
        )

        vals = []
        for list in lists:
            href = list.xpath("./a/@href")
            nums = list.xpath('./a/div[1]/div[2]/div[1]/span/text()')
            dates = list.xpath('./a/div[1]/div[2]/div[2]/time/@datetime')
            vals.append(
                (
                    unquote(href[0]) if href else None,
                    nums[0] if nums else None,
                    datetime.strptime(dates[0], "%Y-%m-%dT%H:%M:%SZ").astimezone(ZoneInfo("Asia/Tokyo")) if dates else None,
                )
            )
        return vals

    # TAGリストを取得
    def getTAGlist(self):
        # Genres:情報を取得
        # //*[@id="tabpanel-description"]/div/div/div[2]/div/a/span
        return self.html.xpath(
            '//*[@id="tabpanel-description"]/div/div/div[2]/div/a/span/text()'
        )

    # artistリストを取得
    def getARTIST(self):
        # Artist
        return []

    # Titleを取得
    def getTitle(self):
        # Alternative Titles
        # /html/body/main/article/section/div/div[2]/div[1]/div
        lists = self.html.xpath(
            '//article/section/div/div//h1[contains(@itemprop,"name")]/../div/text()'
        )
        titles = str(lists[0]).split(",") if lists else []
        return [val.strip() for val in titles]

    def getDescription(self):
        # Synopsis Strategic Lovers
        # //*[@id="tabpanel-description"]/div/div/div/div/p
        lists = self.html.xpath(
            '//*[@id="tabpanel-description"]/div/div/div/div/p/text()'
        )
        return "\n".join([str(var).strip() for var in lists])

    # 登録時刻を取得
    def getPostedOn(self) -> datetime | None:
        # Posted On
        return None

    # 更新時刻を取得
    def getUpdatedOn(self) -> datetime | None:
        # Updated On
        # /html/body/main/article/section/div/div[1]/div[5]/div[8]/div/p
        lists = self.html.xpath('//div[h1/span/text()="Last Updates"]/div[contains(@class, "inline")]/p[contains(@class, "inline")]/text()')
        if lists:
            return self._getTimeStamp("%Y-%m-%dT%H:%M:%S%z", lists[0].strip())
        else:
            return None

    def getThumbnail(self):
        # //main/article/section/div/div[1]/div[1]/img/@src
        lists = self.html.xpath('//main/article/section/div/div/div[contains(@class, "contents")]/img/@src')
        return re.sub(r"^//", r"https://", lists[0]) if lists else None

    def getURL2Chapter(self, url) -> List[str]:
        chapter = "0000.000.000"
        list = re.search(r"^https?://.*/chapter-([0-9]+)\.([0-9]+)\.([0-9]+)\.[0-9]*/$", url)
        if list:
            chapter = "%04d.%03d.%03d" % (int(list.group(1)), int(list.group(2)), int(list.group(3)))
        else:
            # https://rawkuma.net/manga/kuse-tsuyo-kanojo-wa-toko-ni-izanau/chapter-15.3.217773/
            list = re.search(r"^https?://.*/chapter-([0-9]+)\.([0-9]+)\.[0-9]*/$", url)
            if list:
                chapter = "%04d.%03d.000" % (int(list.group(1)), int(list.group(2)))
            else:
                # https://rawkuma.net/manga/tokidoki-bosotto-roshiago-de-dereru-tonari-no-alya-san/chapter-67.225248/
                list = re.search(r"^https?://.*/chapter-([0-9]+)\.[0-9]*/$", url)
                if list:
                    chapter = "%04d.000.000" % int(list.group(1))

        return chapter

    # 検索ページからのURL取得
    def getLatestPage(self) -> List[Dict[str, List]]:
        # //*[@id="search-results"]/div/div[1]/div[1]/a/@href
        search_lists = self.html.xpath('//div[@id="search-results"]/div/div')
        
        results = []
        for list in search_lists:
            if list.xpath('./div[contains(@class, "overflow-hidden")]/a/@href'):
                a = {}
                a['url'] = list.xpath('./div[contains(@class, "overflow-hidden")]/a/@href')[0]

                a['chapter'] = []
                for chap in list.xpath('./a'):
                    if chap.xpath('./@href'):
                        a['chapter'].append({'url': chap.xpath('./@href')[0],
                                             'num': chap.xpath('./div/p/text()')[0].strip(),
                                             'date': datetime.strptime(chap.xpath('./div/time/@datetime')[0], "%Y-%m-%dT%H:%M:%S%z").astimezone(ZoneInfo("Asia/Tokyo"))})

                results.append(a)

        return results

    def _getTimeStamp(self, timefmt: str, timestamp: str) -> datetime | None:
        # 「10 minutes ago」「2 hours ago」「1 days ago」「05-04-2023」

        if timestamp == "Just now":
            return datetime.now(ZoneInfo("Asia/Tokyo")).replace(hour=0,minute=0, second=0, microsecond=0)

        date = None

        s = re.search(r"(\d+) secs? ago", timestamp)
        m = re.search(r"(\d+) minu?t?e?s? ago", timestamp)
        h = re.search(r"(\d+) hours? ago", timestamp)
        d = re.search(r"(\d+) days? ago", timestamp)
        mo = re.search(r"(\d+) months? ago", timestamp)

        if s is None and m is None and h is None and d is None and mo is None:
            date = datetime.strptime(timestamp, timefmt).astimezone(ZoneInfo("Asia/Tokyo"))
        else:
            date = datetime.now(ZoneInfo("Asia/Tokyo")) - timedelta(
                seconds=int(s.group(1)) if s is not None else 0,
                minutes=int(m.group(1)) if m is not None else 0,
                hours=int(h.group(1)) if h is not None else 0,
                days=int(d.group(1)) if d is not None else int(mo.group(1)) * 30 if mo is not None else 0,
            )

        return date.replace(minute=0, second=0, microsecond=0)
