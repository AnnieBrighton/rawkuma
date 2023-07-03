#!/usr/bin/env python3

from datetime import datetime, timedelta
import re
from booksHTML import HTMLinterface, getHTML
from zoneinfo import ZoneInfo


class kingrawHTML(getHTML, HTMLinterface):
    def __init__(self, chrome) -> None:
        super().__init__(chrome)

    # URLが自身とマッチ判定
    def isMatchURL(url):
        return re.match(r"^https?://rawpromax\.com/", url)

    # 漫画リストURLからbookeyを取得
    def getBookKey(url):
        """
        「https://rawpromax.com/manga/556/」 → 「king@556」
        「https://rawpromax.com/title/556/」 → 「king@556」
        「https://rawpromax.com/comic/1122/」 → 「king@1122」
        """
        types = [
            r"^https?://rawpromax.com/manga/([^/]+)/?$",
            r"^https?://rawpromax.com/title/([^/]+)/?$",
            r"^https?://rawpromax.com/comic/([^/]+)/?$",
        ]

        for type in types:
            lists = re.search(type, url)
            if lists is not None:
                return "king@" + lists[1]

        return None

    # 漫画リストページURLリスト取得
    def getUpdateListUrl(limit):
        return [
            f"https://rawpromax.com/manga/page/{page}/?m_orderby=latest"
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
        # 'https://rawpromax.com/manga/556/chapter-1/  or  'https://rawpromax.com/title/556/chapter-1/
        chapter = "0000.00"
        list = re.search(
            r"^https?://[^/]+/(manga|title|comic)/[0-9-]+/chapter-([0-9]+)-([0-9]+)/$",
            url,
        )
        if list:
            chapter = "%04d.%02d" % (int(list.group(2)), int(list.group(3)))
        else:
            list = re.search(
                r"^https?://[^/]+/(manga|title|comic)/[0-9-]+/chapter-([0-9]+)/$", url
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
