#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import asyncio
from typing import Optional, List, TYPE_CHECKING, Literal, Union
from playwright.async_api import async_playwright, BrowserContext, Page, Locator, ElementHandle

if TYPE_CHECKING:
    import logging


class Chrome:
    """
    PlaywrightベースのChrome制御クラス
    """

    user_dir: str = os.path.join(
        os.environ.get("TEMP", "/tmp"),
        f"google-chrome_{os.getpid():08d}",
    )

    chrome_app: Optional[str] = (
        # "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        "/Applications/Google Chrome Dev.app/Contents/MacOS/Google Chrome Dev"
    )

    def __init__(self, logging: logging.Logger) -> None:
        self.logging = logging
        self.ctx: Optional[BrowserContext] = None
        self._pw = None
        self.idling_tabs: List[Page] = []

    async def start(self, headless: bool = False) -> None:
        """Chromeを起動"""
        self.logging.info("Starting Playwright Chrome session")
        os.makedirs(self.user_dir, exist_ok=True)
        self._pw = await async_playwright().start()

        launch_kwargs = dict(
            user_data_dir=self.user_dir,
            headless=headless,
            args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--window-size=1600,900",
                "--disable-extensions",                             # 自動操作拡張を無効化
            ],
        )
        if self.chrome_app:
            launch_kwargs["executable_path"] = self.chrome_app

        self.ctx = await self._pw.chromium.launch_persistent_context(**launch_kwargs)
        self.idling_tabs = list(self.ctx.pages)
        self.logging.info("Chrome started successfully")

    async def stop(self) -> None:
        """Chromeを停止して一時ファイル削除"""
        self.logging.info("Stopping Chrome")
        if self.ctx:
            await self.ctx.close()
        if self._pw:
            await self._pw.stop()
        shutil.rmtree(self.user_dir, ignore_errors=True)
        self.logging.info("Chrome stopped and temp dir cleaned")

    async def open_tab(self) -> Page:
        """新しいタブを開く（または再利用）"""
        if self.idling_tabs:
            return self.idling_tabs.pop()
        assert self.ctx is not None
        return await self.ctx.new_page()

    async def close_tab(self, page: Page) -> None:
        """タブを閉じる代わりにプールに戻す"""
        if page and not page.is_closed():
            try:
                await page.goto("about:blank", wait_until="load", timeout=10_000)
            except Exception:
                pass
        self.idling_tabs.append(page)


class ChromeTab:
    """
    Chromeの1タブを扱うクラス
    """

    class By:
        XPATH: Literal["xpath"] = "xpath"
        CSS: Literal["css"] = "css"
        TEXT: Literal["text"] = "text"
        ID: Literal["id"] = "id"
        NAME: Literal["name"] = "name"

    def __init__(self, browser: Chrome) -> None:
        self._browser = browser
        self._page: Optional[Page] = None

    async def open(self) -> None:
        """タブを開く"""
        self._page = await self._browser.open_tab()

    async def close(self) -> None:
        """タブを閉じる（再利用へ）"""
        if self._page:
            await self._browser.close_tab(self._page)
            self._page = None

    async def get(self, url: str, timeout: int = 60_000) -> None:
        """URLを開き、ページ読み込み完了を待機"""
        if not self._page:
            raise RuntimeError("Tab is not opened.")
        await self._page.goto(url, wait_until="load", timeout=timeout)

    async def getDOM(self) -> Optional[str]:
        """ページのHTML全体を取得"""
        if not self._page:
            return None
        try:
            return await self._page.content()
        except Exception:
            return None

    async def evaluate(self, script: str) -> None:
        """JavaScriptを実行"""
        if not self._page:
            raise RuntimeError("Tab is not opened.")
        await self._page.evaluate(script)

    # ====================================================
    # クリック処理 (標準クリック + JSクリック)
    # ====================================================

    def _build_selector(self, path: str, by: str) -> str:
        """By指定からPlaywrightセレクタ文字列に変換"""
        By = self.By
        if by == By.XPATH:
            return f"xpath={path}"
        if by == By.TEXT:
            return f"text={path}"
        if by == By.ID:
            pid = path[1:] if path.startswith("#") else path
            return f"css=#{pid}"
        if by == By.NAME:
            return f"[name='{path}']"
        # デフォルトCSS
        return path

    async def click(
        self,
        path: str,
        by: Optional[str] = None,
        timeout: int = 10,
        js: bool = False,
    ) -> None:
        if not self._page:
            raise RuntimeError("Tab is not opened.")
        ms = max(0, int(timeout * 1000))
        By = self.By

        # JavaScriptクリック時のXPath対応
        if js and by == By.XPATH:
            script = f"""
            const el = document.evaluate('{path}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            if (el) el.click();
            """
            print(f"{script=}")
            await self._page.evaluate(script)
            return

        # 通常のXPathクリック
        if not js and by == By.XPATH:
            await self._page.locator(f"xpath={path}").click(timeout=ms)
            return

        # 通常CSS / JSクリック（従来どおり）
        selector = self._build_selector(path, by or By.CSS)
        if js:
            await self._page.evaluate(
                f"document.querySelector(`{selector.replace('css=', '')}`).click()"
            )
        else:
            await self._page.click(selector, timeout=ms)

    async def find_elements(
        self,
        path: str,
        by: Optional[str] = None,
        timeout: int = 0,
    ) -> List[ElementHandle]:
        """
        指定パスで一致するすべての要素を取得
        """
        if not self._page:
            raise RuntimeError("Tab is not opened.")
        By = self.By
        selector = self._build_selector(path, by or By.XPATH)

        # 待機オプション
        if timeout > 0:
            await self._page.wait_for_selector(selector, timeout=timeout * 1000)

        # Playwrightはlocatorで要素集合を扱う
        locator = self._page.locator(selector)
        return await locator.all()  # → List[ElementHandle]

    async def input_text(
        self,
        xpath: str,
        text: str,
        enter: bool = False,
        timeout: int = 10,
    ) -> None:
        """
        XPathで指定したinputタグに文字列を入力する。
        - clear=True の場合は既存の入力値をクリアしてから入力
        - Seleniumの send_keys() に相当
        """
        if not self._page:
            raise RuntimeError("Tab is not opened.")
        selector = f"xpath={xpath}"
        ms = max(0, int(timeout * 1000))

        # 入力要素が出現するまで待機
        await self._page.wait_for_selector(selector, timeout=ms)

        locator = self._page.locator(selector)
        await locator.click()
        await locator.type(text, delay=50)  # 既存値の末尾にタイプ

        if enter:
            await locator.press("Enter") # 入力後にEnterキーを押す場合
