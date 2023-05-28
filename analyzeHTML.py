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
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from difflib import SequenceMatcher
import re
from lxml import etree
from requests import session, exceptions
from time import sleep
import traceback
import unicodedata
from Chrome import ChromeTab
import logging

from urllib.parse import quote, unquote


class analyzeHTML:
    def __init__(self, url=None, chrome=None) -> None:
        self.html = None
        if url is not None:
            if re.match(r"^https?://rawkuma.com/", url):
                self.html = rawkumaHTML(chrome)
            elif re.match(r"^https?://kingraw.co/", url):
                self.html = kingrawHTML(chrome)
            elif re.match(r"^https?://rawuwu.com/", url):
                self.html = rawuwuHTML(chrome)
            elif re.match(r"^https?://raw.senmanga.com/", url):
                self.html = senmangaHTML(chrome)
            else:
                logging.info("マッチするドメインが見つかりません。url={url}".format(url=url))

    def getHTML(self):
        return self.html

    def getBookKey(self, url):
        """
        「https://rawkuma.com/manga/oshi-no-ko/」 → 「oshi-no-ko」
        「https://kingraw.co/manga/556/」 → 「king@556」
        「https://rawuwu.com/haru-ni-fureru-c8982/」 → 「uwu@haru-ni-fureru-c8982」
        「https://raw.senmanga.com/next-life/」 → 「sen@next-life」
        """
        types = [
            {"keyword": r"^https?://rawkuma.com/manga/([^/]+)/?$", "pre": ""},
            {"keyword": r"^https?://kingraw.co/manga/([^/]+)/?$", "pre": "king@"},
            {"keyword": r"^https?://kingraw.co/title/([^/]+)/?$", "pre": "king@"},
            {"keyword": r"^https?://rawuwu.com/([^/]+)/?$", "pre": "uwu@"},
            {"keyword": r"^https?://rawuwu.com/en/([^/]+)/?$", "pre": "uwu@"},
            {"keyword": r"^https?://raw.senmanga.com/([^/]+)/?$", "pre": "sen@"},
        ]

        for type in types:
            lists = re.search(type["keyword"], url)
            if lists is not None:
                return type["pre"] + lists[1]

        return url

    def getUpdateListUrl(self, limit):
        lists = []
        lists.extend(rawkumaHTML(None).getUpdateListUrl(limit))
        lists.extend(kingrawHTML(None).getUpdateListUrl(limit))
        lists.extend(rawuwuHTML(None).getUpdateListUrl(limit))
        lists.extend(senmangaHTML(None).getUpdateListUrl(limit))

        return lists


class getHTML:
    def __init__(self, chrome) -> None:
        self.chrome = chrome
        self.html = None

    async def getTEXT4HTML(self, url) -> None:
        tab = ChromeTab(self.chrome)
        await tab.open()
        await tab.get(url)
        self.text = await tab.getDOM()
        await tab.close()
        self.html = etree.HTML(self.text)
        return


class kingrawHTML(getHTML):
    def __init__(self, chrome) -> None:
        super().__init__(chrome)

    def getUpdateListUrl(self, limit):
        return [
            f"https://kingraw.co/manga/page/{page}/?m_orderby=latest"
            for page in range(1, limit + 1)
        ]

    # イメージリストを取得
    def getImageList(self):
        # //*[@id="image-0"]
        # /html/body/div[3]/div/div/div/div/div/div/div/div/div[1]/div[2]/div/div/div[2]/div[1]/img
        lists = self.html.xpath(
            '//div[@class="reading-content"]/div[contains(@class, "page-break")]/img[contains(@id, "image-")]/@src'
        )
        return [str(var).replace("\n", "").replace("\t", "").strip() for var in lists]

    # URLリストを取得
    def getURLlists(self):
        # /html/body/div[3]/div/div/div/div[2]/div/div/div/div[1]/div/div[1]/div/div[2]/div/ul/li[1]/a
        lists = self.html.xpath(
            '//ul[contains(@class, "main")]/li[contains(@class, "wp-manga-chapter")]'
        )

        vals = []
        for list in lists:
            href = list.xpath("./a/@href")
            nums = list.xpath("./a/text()")
            date = self._getTimeStamp(list)
            vals.append(
                (
                    href[0] if href else None,
                    re.sub(
                        r"^.* ",
                        "",
                        nums[0]
                        .replace("\n", "")
                        .replace("\t", "")
                        .replace("【", "")
                        .replace("】", ""),
                    )  # '【第1.1話】'
                    if nums
                    else None,
                    date.replace(tzinfo=None) if date is not None else None,
                )
            )
        return vals

    # TAGリストを取得
    def getTAGlist(self):
        # /html/body/div[3]/div/div/div/div[1]/div/div/div/div[3]/div[2]/div/div/div[4]/div[2]/div/a[1]
        lists = self.html.xpath(
            '//div[@class="summary-content"]/div[@class="genres-content"]/a/text()'
        )
        return [str(var).strip() for var in lists]

    # artistリストを取得
    def getARTIST(self):
        return []

    # Titleを取得
    def getTitle(self):
        lists = self.html.xpath('//meta[@property="og:title"]/@content')
        titles = str(lists[0]).split(",") if lists else []
        return [val.strip().replace(" (Raw – Free)", "") for val in titles]

    #
    def getDescription(self):
        # /html/body/div[3]/div/div/div/div[1]/div/div/div/div[3]/div[2]/div/div/div[6]/p
        lists = self.html.xpath(
            '//div[@class="post-content"]/div[@class="manga-excerpt"]/p/text()'
        )
        return "\n".join([str(var).strip() for var in lists])

    # 登録時刻を取得
    def getPostedOn(self):
        lists = self.html.xpath('//meta[@property="article:modified_time"]/@content')
        # 「2023-03-28T17:26:57+00:00」
        return (
            datetime.strptime(lists[0], "%Y-%m-%dT%H:%M:%S%z").astimezone(
                ZoneInfo("Asia/Tokyo")
            )
            if lists
            else None
        )

    # 更新時刻を取得
    def getUpdatedOn(self):
        # /html/body/div[3]/div/div/div/div[2]/div/div/div/div[1]/div/div[1]/div/div[2]/div/ul/li[1]/a
        lists = self.html.xpath(
            '//ul[contains(@class, "main")]/li[contains(@class, "wp-manga-chapter")]'
        )
        return self._getTimeStamp(lists[0]) if lists else None

    # サムネイルイメージ取得
    def getThumbnail(self):
        # /html/body/div[3]/div/div/div/div[1]/div/div/div/div[3]/div[1]/a/img
        src = self.html.xpath(
            '//div[@class="summary_image"]/a/img[@class="img-responsive"]/@src'
        )
        return src[0] if src else None

    # URLからチャプター番号を生成
    def getURL2Chapter(self, url):
        # 'https://kingraw.co/manga/556/chapter-1/  or  'https://kingraw.co/title/556/chapter-1/
        chapter = "0000.00"
        list = re.search(
            r"^https?://[^/]+/(manga|title)/[0-9]+/chapter-([0-9]+)-([0-9]+)/$", url
        )
        if list:
            chapter = "%04d.%02d" % (int(list.group(2)), int(list.group(3)))
        else:
            list = re.search(
                r"^https?://[^/]+/(manga|title)/[0-9]+/chapter-([0-9]+)/$", url
            )
            if list:
                chapter = "%04d.00" % int(list.group(2))

        return chapter

    # 検索ページからのURL取得
    def getLatestPage(self):
        # //*[@id="manga-item-4032"]/a
        # /html/body/div[3]/div/div/div[2]/div/div/div/div[1]/div/div/div[2]/div[2]/div/div[1]/div[1]/div/div[1]/div/div[1]/a
        return self.html.xpath(
            '//div[contains(@class, "page-item-detail")]/div[contains(@class, "item-thumb")]/a/@href'
        )

    def _getTimeStamp(self, list):
        date = None
        dates = list.xpath("./span/i/text()")  # '2023年4月16日'
        if len(dates) != 0:
            date = datetime.strptime(dates[0], "%Y年%m月%d日").astimezone(
                ZoneInfo("Asia/Tokyo")
            )
        else:
            dates = list.xpath("./span/a/@title")  # '13時間 ago'  '2日 ago'
            if (len(dates)) > 0:
                h = re.search(r"(\d+)時間", dates[0])
                d = re.search(r"(\d+)日", dates[0])
                hours_ago = (
                    int(h.group(1))
                    if h != None
                    else (int(d.group(1)) * 24 if d != None else 0)
                )
                current_datetime = datetime.now(ZoneInfo("Asia/Tokyo")).replace(
                    minute=0, second=0, microsecond=0
                )
                date = current_datetime - timedelta(hours=hours_ago)
        return date


class rawkumaHTML(getHTML):
    def __init__(self, chrome) -> None:
        super().__init__(chrome)

    def getUpdateListUrl(self, limit):
        return [
            f"https://rawkuma.com/manga/?page={page}&type=manga&order=update"
            for page in range(1, limit + 1)
        ]

    #
    def getImageList(self):
        # イメージリストを取得
        # <img class="ts-main-image curdown" data-index="0" src="https://kumacdn.club/images/s/spy-x-family/chapter-62-3/1-6281c0b1e24d0.jpg"
        #      data-server="Server1" onload="ts_reader_control.singleImageOnload();" onerror="ts_reader_control.imageOnError();">
        # //*[@id="readerarea"]/img[1]
        return self.html.xpath('//*[@id="readerarea"]/img/@src')

    # URLリストを取得
    def getURLlists(self):
        # チャプターリストを取得
        # //*[@id="chapterlist"]/ul/li/div/div[1]/a
        # //*[@id="chapterlist"]/ul/li/div/div[@class="eph-num"]/a
        lists = self.html.xpath(
            '//*[@id="chapterlist"]/ul/li/div/div[@class="eph-num"]'
        )

        vals = []
        for list in lists:
            href = list.xpath("./a/@href")
            nums = list.xpath('./a/span[@class="chapternum"]/text()')
            dates = list.xpath('./a/span[@class="chapterdate"]/text()')
            vals.append(
                (
                    unquote(href[0]) if href else None,
                    nums[0] if nums else None,
                    datetime.strptime(dates[0], "%B %d, %Y") if dates else None,
                )
            )
        return vals

    # TAGリストを取得
    def getTAGlist(self):
        # Genres:情報を取得
        # //*[@id="post-920"]/div[2]/div[1]/div[2]/div[8]/span/a
        # //*[@id="post-920"]/div[2]/div[1]/div[2]/div[@class="wd-full"]/span/a/text()
        # //*[@id="post-5342"]/div[2]/div[1]/div[2]/div[7]/span/a[1]
        # //*div[@id="content"]/div/div[@class="postbody"]/article/div[2]/div[1]/div[2]/div[@class="wd-full"]/span/a
        return self.html.xpath(
            '//*[@class="infox"]/div[@class="wd-full"]/span[@class="mgen"]/a/text()'
        )

    # artistリストを取得
    def getARTIST(self):
        # Artist
        lists = self.html.xpath(
            '//div[@class="fmed" and b/text()="Artist"]/span/text()'
        )
        titles = str(lists[0]).split(",") if lists else []
        return [val.strip() for val in titles]

    # Titleを取得
    def getTitle(self):
        # Alternative Titles
        lists = self.html.xpath(
            '//div[@class="wd-full" and b/text()="Alternative Titles"]/span/text()'
        )
        titles = str(lists[0]).split(",") if lists else []
        return [val.strip() for val in titles]

    def getDescription(self):
        # Synopsis Strategic Lovers
        lists = self.html.xpath(
            '//div[@class="wd-full"]/div[@itemprop="description"]/p/text()'
        )
        return "\n".join([str(var).strip() for var in lists])

    # 登録時刻を取得
    def getPostedOn(self):
        # Posted On
        lists = self.html.xpath('//time[@itemprop="datePublished"]/@datetime')
        return (
            datetime.strptime(
                re.sub(r"^([0-9]+-[0-9]+-[0-9]+)[A-Z]+", r"\1T", lists[0]),
                "%Y-%m-%dT%H:%M:%S%z",
            ).astimezone(ZoneInfo("Asia/Tokyo"))
            if lists
            else None
        )

    # 更新時刻を取得
    def getUpdatedOn(self):
        # Updated On
        lists = self.html.xpath('//time[@itemprop="dateModified"]/@datetime')
        return (
            datetime.strptime(
                re.sub(r"^([0-9]+-[0-9]+-[0-9]+)[A-Z]+", r"\1T", lists[0]),
                "%Y-%m-%dT%H:%M:%S%z",
            ).astimezone(ZoneInfo("Asia/Tokyo"))
            if lists
            else None
        )

    def getThumbnail(self):
        lists = self.html.xpath('//div[@class="thumbook"]/div[@class="thumb"]/img/@src')
        return re.sub(r"^//", r"https://", lists[0]) if lists else None

    def getURL2Chapter(self, url):
        chapter = "0000.00"
        list = re.search(r"^https?://[^/]+/[^/]+-chapter-([0-9]+)-([0-9]+)/$", url)
        if list:
            chapter = "%04d.%02d" % (int(list.group(1)), int(list.group(2)))
        else:
            list = re.search(r"^https?://[^/]+/[^/]+-chapter-([0-9]+)/$", url)
            if list:
                chapter = "%04d.00" % int(list.group(1))

        return chapter

    # 検索ページからのURL取得
    def getLatestPage(self):
        # //*[@id="content"]/div/div[1]/div[1]/div[2]/div[4]/div[1]/div/a
        return self.html.xpath(
            '//div[@class="listupd"]/div[@class="bs"]/div[@class="bsx"]/a/@href'
        )


class senmangaHTML(getHTML):
    def __init__(self, chrome) -> None:
        super().__init__(chrome)

    def getUpdateListUrl(self, page):
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


class rawuwuHTML(getHTML):
    def __init__(self, chrome) -> None:
        super().__init__(chrome)

    def getUpdateListUrl(self, limit):
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
            '//div[@class="manga-chapters"]/ul[@class="clearfix"]/li[div/a/@class="__link"]'
        )

        vals = []
        for list in lists:
            href = list.xpath("./div/a/@href")
            nums = list.xpath("./div/a/text()")
            dates = list.xpath('./div[contains(@class, "alr")]/text()')
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
        # /html/body/div[2]/div[7]/div/div/div[2]/div[2]/ul/li[4]/div[2]
        # //div[@class="manga-detail"]/ul/li[contains(div[@class="md-title"]/text(),"Updated")]/div[@class="md-content"]/text()
        # 「2 hours ago」「1 days ago」「05-04-2023」
        lists = self.html.xpath(
            '//div[@class="manga-detail"]/ul/li[contains(div[@class="md-title"]/text(),"Updated")]/div[@class="md-content"]/text()'
        )
        return self._getTimeStamp(lists[0]) if lists else None

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
        chapter = None
        list = re.search(
            r"^https?://[^/]+/read/[^/]+/chapter-([0-9]+)\.([0-9]+)/?$", url
        )
        if list:
            chapter = "%04d.%02d" % (int(list.group(1)), int(list.group(2)))
        else:
            # https://rawuwu.com/read/tefuda-ga-oume-no-victoria-c19436/chapter-2
            list = re.search(r"^https?://[^/]+/read/[^/]+/chapter-([0-9]+)/?$", url)
            if list:
                chapter = "%04d.00" % int(list.group(1))

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
