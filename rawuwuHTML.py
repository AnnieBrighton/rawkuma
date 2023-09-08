#!/usr/bin/env python3

from datetime import datetime, timedelta
import re
from booksHTML import HTMLinterface, getHTML
from zoneinfo import ZoneInfo
from Chrome import ChromeTab
from lxml import etree
import asyncio


class rawuwuHTML(getHTML, HTMLinterface):
    def __init__(self, chrome) -> None:
        super().__init__(chrome)

    async def getTEXT4HTML(self, url) -> None:
        tab = ChromeTab(self.chrome)
        await tab.open()
        await tab.get(url)
        self.text = await tab.getDOM()
        self.html = etree.HTML(self.text)

        # チャプター表示時に、画面に以下が出ていたら、continueをクリック
        # You are viewing hidden content "xxxxx". Please click the 'continue' button to proceed.
        goto = self.html.xpath(
            '//div[@class="continue-hidden"]/a[@title="Continue" and @href="#goto"]'
        )

        if len(goto):
            await tab.evaluate("""document.querySelector("a[href='#goto']").click();""")
            await asyncio.sleep(2)

            self.text = await tab.getDOM()
            self.html = etree.HTML(self.text)

        # ブックのチャプター一覧表示時に、Show allが画面に以下が出ていたら、continueをクリック
        show = self.html.xpath(
            '//div[@class="show-all-chapters"]/a[@title="Show all chapters" and @href="#show"]'
        )

        if len(show):
            await tab.evaluate("""document.querySelector("a[href='#show']").click();""")
            await asyncio.sleep(2)

            self.text = await tab.getDOM()
            self.html = etree.HTML(self.text)

        await tab.close()
        return

    # URLが自身とマッチ判定
    def isMatchURL(url):
        return re.match(r"^https?://rawuwu\.com/", url)

    # 漫画リストURLからbookeyを取得
    def getBookKey(url):
        """
        「https://rawuwu.com/haru-ni-fureru-c8982/」 → 「uwu@haru-ni-fureru-c8982」
        「https://rawuwu.com/read/haru-ni-fureru-c8982/」 → 「uwu@haru-ni-fureru-c8982」
        「https://rawuwu.com/en/haru-ni-fureru-c8982/」 → 「uwu@haru-ni-fureru-c8982」
        「https://rawuwu.com/en/read/haru-ni-fureru-c8982/」 → 「uwu@haru-ni-fureru-c8982」
        """
        types = [
            r"^https?://rawuwu.com/([^/]+)/?$",
            r"^https?://rawuwu.com/read/([^/]+)/?$",
            r"^https?://rawuwu.com/en/([^/]+)/?$",
            r"^https?://rawuwu.com/en/read/([^/]+)/?$",
        ]

        for type in types:
            lists = re.search(type, url)
            if lists is not None:
                return "uwu@" + lists[1]

        return None

    # 漫画リストページURLリスト取得
    def getUpdateListUrl(limit):
        return [
            f"https://rawuwu.com/latest?page={page}" for page in range(1, limit + 1)
        ]

    # イメージリストを取得
    def getImageList(self):
        # //*[@id="page0"]/div/canvas
        # //div[contains(@class, "chapter-imgs")]/div[contains(@class, "page-wrapper")]/div[@class="chapter-img"]/canvas/@data-srcset
        lists = self.html.xpath(
            '//div[contains(@class, "chapter-imgs")]/div[contains(@class, "page-wrapper")]/div[contains(@class, "chapter-img")]/canvas/@data-srcset'
        )
        return [str(var).strip() for var in lists]

    # URLリストを取得
    def getURLlists(self):
        # /html/body/div[2]/div[7]/div/div/div[8]/ul/li[2]/div[1]/a
        # //div[@class="manga-chapters"]/ul[@class="clearfix"]/li[div/a/@class="__link"]

        lists = self.html.xpath(
            '//div[@class="manga-chapters"]/ul[@class="clearfix"]/li[a/@class="__link"]'
        )

        vals = []
        for list in lists:
            href = list.xpath("./a/@href")
            nums = list.xpath('./a/div/div[@class="chaptern"]/text()')
            dates = list.xpath(
                './a/div/div[@class="time"]/text() | ./a/div/time[@class="time"]/text()'
            )
            vals.append(
                (
                    "https://rawuwu.com" + href[0] if href else None,
                    nums[0] if nums else None,
                    self._getTimeStamp(dates[0]).replace(tzinfo=None)
                    if dates
                    else None,
                )
            )
        return vals

    # TAGリストを取得
    def getTAGlist(self):
        # Genres:情報を取得
        # '//div[@class="manga-detail"]/ul/li[div[@class="md-title"]/text()="Genres:"]/div[@class="md-content"]/a/text()'
        return self.html.xpath(
            '//div[@class="manga-detail"]/ul/li[div[@class="md-title"]/text()="Genres:"]/div[@class="md-content"]/a/text()'
        )

    # artistリストを取得
    def getARTIST(self):
        return []

    # Titleを取得
    def getTitle(self):
        # /html/body/div[2]/div[7]/div/div/div[4]/div/p
        # //div[@class="manga-others-name"]/div[@class="inner"]/p
        lists = self.html.xpath(
            '//div[@class="manga-others-name"]/div[@class="inner"]/p/text()'
        )
        titles = str(lists[0]).split(",") if lists else []
        return [val.strip() for val in titles]

    # 明細取得
    def getDescription(self):
        # /html/body/div[2]/div[7]/div/div/div[6]/div/p
        # //div[@class="manga-description"]/div[@class="inner"]/p
        lists = self.html.xpath(
            '//div[@class="manga-description"]/div[@class="inner"]/p/text()'
        )
        return "\n".join([str(var).strip() for var in lists])

    # 登録時刻を取得
    def getPostedOn(self):
        return None

    # 更新時刻を取得
    def getUpdatedOn(self):
        # /html/body/div[2]/div[7]/div/div/article/time
        # 「[ Updated : 9:32 8/17/2023 ]」
        lists = self.html.xpath(
            '//div[@class="row"]/article/time[@class="time"]/@datetime'
        )

        return (
            datetime.strptime(lists[0], "%Y-%m-%dT%H:%M:%S%z")
            .astimezone(ZoneInfo("Asia/Tokyo"))
            .replace(minute=0, second=0, microsecond=0)
            if lists
            else None
        )

    # サムネイルイメージ取得
    def getThumbnail(self):
        # /html/body/div[2]/div[7]/div/div/div[2]/div[1]/div[1]/img
        # //div[@class="manga-img"]/div[@class="img-holder"]/img
        src = self.html.xpath(
            '//div[@class="manga-img"]/div[@class="img-holder"]/img/@src'
        )
        return src[0] if src else None

    # URLからチャプター番号を生成
    def getURL2Chapter(self, url):
        # https://rawuwu.com/read/tefuda-ga-oume-no-victoria-c19436/chapter-3.1/
        chapter = "0000.00"
        list = re.search(
            r"^https?://[^/]+/read/[^/]+/(en/)?(read/)?chapter-([0-9]+)\.([0-9]+)/?$",
            url,
        )
        if list:
            chapter = "%04d.%02d" % (int(list.group(3)), int(list.group(4)))
        else:
            # https://rawuwu.com/read/tefuda-ga-oume-no-victoria-c19436/chapter-2
            # https://rawuwu.com/en/read/tokidoki-bosotto-roshiago-de-dereru-tonari-no-alya-san-c16480/chapter-15
            list = re.search(
                r"^https?://[^/]+/(en/)?(read/)?[^/]+/chapter-([0-9]+)/?$", url
            )
            if list:
                chapter = "%04d.00" % int(list.group(3))

        return chapter

    # 検索ページからのURL取得
    def getLatestPage(self):
        # /html/body/div[2]/div[7]/div/div/div[3]/div[1]/div/div[1]/a
        return [
            "https://rawuwu.com" + val + "/"
            for val in self.html.xpath(
                '//div[@class="m-item"]/div[@class="clearfix"]/div[@class="m-img"]/a/@href'
            )
        ]

    def _getTimeStamp(self, timestamp):
        # 「10 minutes ago」「2 hours ago」「1 days ago」「05-04-2023」

        date = None

        m = re.search(r"(\d+) minutes ago", timestamp)
        h = re.search(r"(\d+) hours ago", timestamp)
        d = re.search(r"(\d+) days ago", timestamp)

        if m is None and h is None and d is None:
            date = datetime.strptime(timestamp, "%d-%m-%Y").astimezone(
                ZoneInfo("Asia/Tokyo")
            )
        else:
            hours_ago = (
                int(h.group(1))
                if h is not None
                else (int(d.group(1)) * 24 if d is not None else 0)
            )
            current_datetime = datetime.now(ZoneInfo("Asia/Tokyo")).replace(
                minute=0, second=0, microsecond=0
            )
            date = current_datetime - timedelta(hours=hours_ago)

        return date
