"""
浏览器管理器
负责 Playwright 浏览器的启动、配置、Cookie 注入、反爬虫设置和资源清理
"""
import json
import os
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from config.settings import (
    HEADLESS,
    SLOW_MO,
    USER_AGENT,
    VIEWPORT,
    AUTH_FILE_PATH,
    DEFAULT_TIMEOUT
)


class BrowserManager:
    """
    封装 Playwright 浏览器的生命周期管理
    """

    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def start(self) -> Page:
        """
        启动浏览器并返回 Page 对象
        包含以下步骤：
        1. 启动 Playwright
        2. 创建 Browser 和 Context
        3. 注入反爬虫 JS
        4. 加载 Cookie（如果存在）
        5. 创建新页面

        Returns:
            Page: Playwright Page 对象
        """
        print("🚀 [BrowserManager] 正在启动浏览器...")

        # 1. 启动 Playwright
        self.playwright = await async_playwright().start()

        # 2. 启动 Chromium 浏览器
        self.browser = await self.playwright.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO
        )

        # 3. 创建浏览器上下文（Context）- 设置 User-Agent 和视口
        self.context = await self.browser.new_context(
            user_agent=USER_AGENT,
            viewport=VIEWPORT
        )

        # 4. 注入反爬虫 JS - 隐藏 navigator.webdriver 特征
        await self._inject_stealth_js()

        # 5. 加载本地 Cookie（如果存在）
        await self._load_cookies()

        # 6. 创建新页面
        self.page = await self.context.new_page()

        # 设置默认超时
        self.page.set_default_timeout(DEFAULT_TIMEOUT)

        print("✅ [BrowserManager] 浏览器启动成功")
        return self.page

    async def _inject_stealth_js(self):
        """
        注入反爬虫 JavaScript 代码
        主要用于绕过网站对 webdriver 的检测
        """
        stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        """
        await self.context.add_init_script(stealth_js)
        print("   - [Stealth] 已注入反爬虫 JS")

    async def _load_cookies(self):
        """
        从本地文件加载 Cookie
        如果文件不存在或格式错误，静默跳过
        """
        if not os.path.exists(AUTH_FILE_PATH):
            print(f"   - [Cookie] 未找到 Cookie 文件: {AUTH_FILE_PATH}")
            return

        try:
            with open(AUTH_FILE_PATH, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            if isinstance(cookies, list) and len(cookies) > 0:
                await self.context.add_cookies(cookies)
                print(f"   - [Cookie] 已加载 {len(cookies)} 条 Cookie")
            else:
                print("   - [Cookie] Cookie 文件为空或格式错误")

        except Exception as e:
            print(f"   - [Cookie] 加载失败: {e}")

    async def save_cookies(self, filepath: Optional[str] = None):
        """
        保存当前 Context 的 Cookie 到文件
        用于保持登录态

        Args:
            filepath: Cookie 保存路径，默认使用 AUTH_FILE_PATH
        """
        if not self.context:
            print("❌ [BrowserManager] Context 未初始化，无法保存 Cookie")
            return

        save_path = filepath or AUTH_FILE_PATH

        try:
            cookies = await self.context.cookies()
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            print(f"✅ [BrowserManager] Cookie 已保存到: {save_path}")

        except Exception as e:
            print(f"❌ [BrowserManager] Cookie 保存失败: {e}")

    async def close(self):
        """
        优雅地关闭浏览器资源
        按照 Page -> Context -> Browser -> Playwright 的顺序清理
        """
        print("🛑 [BrowserManager] 正在关闭浏览器...")

        try:
            if self.page:
                await self.page.close()

            if self.context:
                await self.context.close()

            if self.browser:
                await self.browser.close()

            if self.playwright:
                await self.playwright.stop()

            print("✅ [BrowserManager] 浏览器已关闭")

        except Exception as e:
            print(f"⚠️  [BrowserManager] 关闭时出现异常: {e}")

    async def __aenter__(self):
        """支持异步上下文管理器 (async with)"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """支持异步上下文管理器 (async with)"""
        await self.close()
