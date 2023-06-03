#!/usr/bin/env python3

import asyncio
from datetime import datetime
import re
from booksHTML import HTMLinterface, getHTML
from zoneinfo import ZoneInfo
from Chrome import ChromeTab
from lxml import etree


class senmangaHTML(getHTML, HTMLinterface):
    def __init__(self, chrome) -> None:
        super().__init__(chrome)

    # 漫画リストURLからbookeyを取得
    def getBookKey(url):
        """
        「https://raw.senmanga.com/next-life/」 → 「sen@next-life」
        """
        types = [
            r"^https?://raw.senmanga.com/([^/]+)/?$",
        ]

        for type in types:
            lists = re.search(type, url)
            if lists is not None:
                return "sen@" + lists[1]

        return url

    # 漫画リストページURLリスト取得
    def getUpdateListUrl(limit):
        return []

    async def getTEXT4HTML(self, url) -> None:
        tab = ChromeTab(self.chrome)
        await tab.open()
        await tab.get(url)
        text = await tab.getDOM()
        self.html = etree.HTML(text)

        selects = self.html.xpath('//select[@id="viewer"]/option[@value="2"]')

        if len(selects) > 0:
            # select要素のIDが "viewer" の場合、値が "2" のオプションを選択する例
            script = 'document.getElementById("viewer").value = "1"'
            # Chrome DevTools ProtocolのRuntime.evaluateメソッドを使用してJavaScriptを実行する
            await tab.evaluate(script)

            script = """
                var event = document.createEvent('HTMLEvents');
                event.initEvent('change', true, false);
                document.getElementById('viewer').dispatchEvent(event);
            """
            await tab.evaluate(script)

            await asyncio.sleep(5)

            text = await tab.getDOM()
            self.html = etree.HTML(text)

        await tab.close()

        return

    # イメージリストを取得
    def getImageList(self):
        # /html/body/div[4]/a/img/@src
        # div[@class="reader text-center"]/a[@class="clearfix text-center"]/img[@class="picture"]
        lists = self.html.xpath(
            #'div[contains(@class, "text-center")]/a[contains(@class, "text-center")]/img[@class="picture"]/@src'
            # '//div[contains(@class, "text-center")]/a[contains(@class, "text-center")]/img[@class="picture"]/@src'
            # /html/body/div[4]/img[1]
            '//div[contains(@class, "text-center")]/img[@class="picture"]/@src'
        )
        return lists

    # URLリストを取得
    def getURLlists(self):
        # /html/body/div[2]/div/div[1]/div[4]/div[4]/ul/li[1]
        # div[@class="widget-body"]/ul[@class="chapter-list"]/li
        lists = self.html.xpath(
            '//div[@class="widget-body"]/ul[@class="chapter-list"]/li'
        )

        vals = []
        for list in lists:
            href = list.xpath("./a/@href")
            nums = list.xpath("./a/text()")
            date = list.xpath("./span/time/@datetime")
            vals.append(
                (
                    href[0] if href else None,
                    nums[0].replace("\n", "").replace("\t", "").strip()
                    if nums
                    else None,
                    datetime.strptime(
                        date[0] + "+00:00",
                        "%Y-%m-%d %H:%M:%S%z",
                    )
                    .astimezone(ZoneInfo("Asia/Tokyo"))
                    .replace(tzinfo=None)
                    if date
                    else None,
                )
            )
        return vals

    # TAGリストを取得
    def getTAGlist(self):
        return []

    # artistリストを取得
    def getARTIST(self):
        return []

    # Titleを取得
    def getTitle(self):
        # /html/body/div[2]/div/div[1]/div[1]/div[2]/div[2]/div[2]
        # div[@class="series-desc grid md:flex md:flex-wrap"]div[@class="desc"]/div[@class="alt-name"]
        lists = self.html.xpath(
            '//div[contains(@class, "series-desc")]/div[@class="desc"]/div[@class="alt-name"]/text()'
        )
        titles = str(lists[0]).split(",") if lists else []
        return [val.strip() for val in titles]

    # 明細取得
    def getDescription(self):
        # /html/body/div[2]/div/div[1]/div[2]/div[2]/div/p[1]
        # div[@class="series-info"]/div[@class="summary"]/p
        lists = self.html.xpath(
            '//div[@class="series-info"]/div[@class="summary"]/p/text()'
        )
        return "\n".join([str(var).strip() for var in lists])

    # 登録時刻を取得
    def getPostedOn(self):
        return None

    # 更新時刻を取得
    def getUpdatedOn(self):
        # /html/body/div[2]/div/div[1]/div[1]/div[2]/div[2]/div[3]/div[6]/time
        #
        lists = self.html.xpath(
            '//div[@class="item" and strong/text()="Updated On"]/time/@datetime'
        )
        return (
            datetime.strptime(
                lists[0] + "+00:00",
                "%Y-%m-%d %H:%M:%S%z",
            ).astimezone(ZoneInfo("Asia/Tokyo"))
            if lists
            else None
        )

    # サムネイルイメージ取得
    def getThumbnail(self):
        # /html/body/div[2]/div/div[1]/div[1]/div[2]/div[1]/div[1]/img
        # div[@class="thumbook grid gap-2"]/div[@class="cover"]/img[@class="img-responsive"]
        lists = self.html.xpath(
            '//div/div[@class="cover"]/img[@class="img-responsive"]/@src'
        )
        return lists[0] if lists else None

    # URLからチャプター番号を生成
    def getURL2Chapter(self, url):
        chapter = None
        list = re.search(r"^https?://[^/]+/[^/]+/([0-9]+)[\.-]([0-9]+)$", url)
        if list:
            chapter = "%04d.%02d" % (int(list.group(1)), int(list.group(2)))
        else:
            list = re.search(r"^https?://[^/]+/[^/]+/([0-9]+)$", url)
            if list:
                chapter = "%04d.00" % int(list.group(1))

        return chapter

    # 検索ページからのURL取得
    def getLatestPage(self):
        return []
