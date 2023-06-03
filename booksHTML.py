#!/usr/bin/env python3

from abc import ABC, abstractmethod
from Chrome import ChromeTab
from lxml import etree


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


class HTMLinterface(ABC):
    # URLが自身とマッチ判定
    @abstractmethod
    def isMatchURL(url):
        pass

    # 漫画リストURLからbookeyを取得
    @abstractmethod
    def getBookKey(url):
        pass

    # 漫画リストページURLリスト取得
    @abstractmethod
    def getUpdateListUrl(limit):
        pass

    # イメージリストを取得
    @abstractmethod
    def getImageList(self):
        pass

    # チャプターリストを取得
    @abstractmethod
    def getURLlists(self):
        pass

    # TAGリストを取得
    @abstractmethod
    def getTAGlist(self):
        pass

    # artistリストを取得
    @abstractmethod
    def getARTIST(self):
        pass

    # Titleを取得
    @abstractmethod
    def getTitle(self):
        pass

    # 詳細を取得
    @abstractmethod
    def getDescription(self):
        pass

    # 登録時刻を取得
    @abstractmethod
    def getPostedOn(self):
        pass

    # 更新時刻を取得
    @abstractmethod
    def getUpdatedOn(self):
        pass

    # サムネイルイメージ取得
    @abstractmethod
    def getThumbnail(self):
        pass

    # URLからチャプター番号を生成
    @abstractmethod
    def getURL2Chapter(self, url):
        pass

    # 検索ページからのURL取得
    @abstractmethod
    def getLatestPage(self):
        pass
