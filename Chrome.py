#!/usr/bin/env python3

from datetime import datetime
import os
from time import sleep
import shutil
from subprocess import Popen
from asyncinit import asyncinit
import aiochrome
import asyncio
import logging

def func_hook(func):
    def wrapper(*arg, **kwargs):
        #logging.info('call {CLASS}:{FUNC}'.format(CLASS=arg[0].__class__.__name__, FUNC=func.__name__))
        ret = func(*arg, **kwargs)
        #logging.info('return {CLASS}:{FUNC}'.format(CLASS=arg[0].__class__.__name__, FUNC=func.__name__))
        return ret
    return wrapper

class Chrome():
    """
    Chrome用ライブラリ
    """
    user_dir = os.path.join(os.environ.get('TEMP', '/tmp'), 'google-chrome_{0:08d}'.format(os.getpid()))

    chrome_app = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

    @func_hook
    def __init__(self, logging) -> None:
        """ コンストラクタ """
        logging.info('Chrome init')
        self.logging = logging
        self.browser = None
        self.proc = None
        self.idling_tabs = []

        # chromedriver_autoinstaller.install()    # Check if the current version of chromedriver exists
        # and if it doesn't exist, download it automatically,
        # then add chromedriver to path

    @func_hook
    async def start(self):
        try:
            # chrome用ユーザディレクトリの作成
            os.makedirs(self.user_dir, exist_ok=False)
        except FileExistsError:
            pass

        opt = [self.chrome_app]
        opt.append('--user-data-dir=' + self.user_dir)
        #opt.append('--window-size=800,600')
        opt.append('--window-size=1600,200')
        opt.append('--no-first-run')
        opt.append('--no-default-browser-check')

        opt.append('--remote-debugging-port=9222')
        # opt.append('--blink-settings=imagesEnabled=false')
        # https://senablog.com/python-selenium-chrome-option/#

        self.proc = Popen(opt)

        await asyncio.sleep(2)

        self.browser = aiochrome.Browser(url="http://127.0.0.1:9222")

        for tab in await self.browser.list_tab():
            await tab.start()
            await tab.Network.enable()
            self.idling_tabs.append(tab)


    @func_hook
    async def stop(self) -> None:
        for tab in await self.browser.list_tab():
            await tab.stop()

            # wait for loading
            await tab.wait(5)
        
            # close tab
            await self.browser.close_tab(tab)

        # chrome終了
        self.proc.kill()

        # 起動時に、user_dirが存在しなければ削除する
        shutil.rmtree(self.user_dir)

    @func_hook
    async def open_tab(self):
        if not self.idling_tabs:
            tab = await self.browser.new_tab()
            await tab.start()
            await tab.Network.enable()
        else:
            tab = self.idling_tabs.pop()

        return tab

    @func_hook
    async def close_tab(self, tab):
        self.idling_tabs.append(tab)

class ChromeTab():
    @func_hook
    def __init__(self, browser) -> None:
        self.__browser = browser
        self.__tab = None

    @func_hook
    async def open(self) -> None:
        self.__tab = await self.__browser.open_tab()

    @func_hook
    async def close(self) -> None:
        if self.__tab is not None:
            await self.__browser.close_tab(self.__tab)
            self.__tab = None

    @func_hook
    async def get(self, url: str) -> None: 
        # call method with timeout
        await self.__tab.Page.navigate(url=url, _timeout=10)
        await self.__tab.wait(5)

    @func_hook
    async def getDOM(self) -> str:
        for _ in range(0, 10):
            try:
                root = await self.__tab.DOM.getDocument()
                HTML = await self.__tab.DOM.getOuterHTML(nodeId=root['root']['nodeId']) 
                return HTML['outerHTML']
            except aiochrome.exceptions.CallMethodException:
                await asyncio.sleep(1)
        else:
            return None
