#!/usr/bin/env python3

from datetime import datetime
import re
from urllib.parse import unquote
from booksHTML import HTMLinterface, getHTML
from zoneinfo import ZoneInfo


class rawkumaHTML(getHTML, HTMLinterface):
    def __init__(self, chrome) -> None:
        super().__init__(chrome)

    # URLが自身とマッチ判定
    def isMatchURL(url):
        return re.match(r"^https?://rawkuma\.com/", url)

    # 漫画リストURLからbookeyを取得
    def getBookKey(url):
        """
        「https://rawkuma.com/manga/oshi-no-ko/」 → 「oshi-no-ko」
        """
        types = [
            r"^https?://rawkuma.com/manga/([^/]+)/?$",
        ]

        for type in types:
            lists = re.search(type, url)
            if lists is not None:
                return lists[1]

        return None

    # 漫画リストページURLリスト取得
    def getUpdateListUrl(limit):
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
        list = re.search(
            r"^https?://[^/]+/[^/]+-chapter-([0-9]+)-([0-9]+)[^0-9]*/$", url
        )
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
