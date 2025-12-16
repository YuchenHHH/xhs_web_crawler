"""
Pinterest crawler strategy implementation
"""
from typing import List, Dict
from playwright.async_api import Page

from config.base_site import CrawlerStrategy


class PinterestCrawlerStrategy(CrawlerStrategy):
    """
    Pinterest crawler strategy implementation
    """

    @property
    def platform_name(self) -> str:
        return "pinterest"

    @property
    def home_url(self) -> str:
        return "https://www.pinterest.com/"

    @property
    def search_input_selectors(self) -> List[str]:
        return [
            "[data-test-id='search-box-input']",
            "input[name='searchBoxInput']",
            "input[aria-label*='Search']",
            "input[placeholder*='Search']",
            "#searchBoxInput",
            "input[type='text'][autocomplete='off']"
        ]

    @property
    def note_card_selectors(self) -> List[str]:
        return [
            "[data-test-id='pin']",
            "[data-test-id='pin-visual-wrapper']",
            "[data-test-id='pinWrapper']",
            "a[href*='/pin/']"
        ]

    @property
    def note_detail_selectors(self) -> Dict[str, str]:
        return {
            "title": "[data-test-id='pin-title'], h1",
            "author": "[data-test-id='user-profile-link'], [data-test-id='creator-profile']",
            "content": "[data-test-id='pin-description']",
            "likes": "[data-test-id='reaction-count']"
        }

    @property
    def note_image_selectors(self) -> List[str]:
        return [
            "[data-test-id='pin-visual-wrapper'] img",
            "[data-test-id='visual-content-container'] img",
            "img[alt*='Pin']",
            ".mainContainer img"
        ]

    async def detect_login_status(self, page: Page) -> bool:
        """
        Pinterest-specific login detection:
        Primary method: Check for absence of login/signup buttons (if no login button = logged in)
        """
        try:
            # Wait for page to stabilize
            import asyncio
            await asyncio.sleep(1.5)

            current_url = page.url
            print(f"   - [Pinterest] 当前URL: {current_url}")

            # If redirected to login page, definitely not logged in
            if "/login" in current_url or "/auth" in current_url:
                print(f"   - [Pinterest] 检测到登录页面URL - 未登录")
                return False

            # Primary check: Look for login/signup buttons (visible = NOT logged in)
            login_btn = page.locator(
                "button:has-text('Log in'), "
                "a:has-text('Log in'), "
                "button:has-text('Sign up'), "
                "[data-test-id='simple-login-button'], "
                "[data-test-id='simple-signup-button']"
            ).first

            try:
                is_login_visible = await login_btn.is_visible(timeout=3000)
                if is_login_visible:
                    print(f"   - [Pinterest] 检测到登录按钮 - 未登录")
                    return False
                else:
                    print(f"   - [Pinterest] 未检测到登录按钮 - 已登录")
                    return True
            except:
                # Timeout means login button not found = likely logged in
                print(f"   - [Pinterest] 登录按钮查询超时（未找到） - 已登录")
                return True

        except Exception as e:
            print(f"⚠️  Pinterest登录检测异常: {e}")
            # If error occurs, assume not logged in to be safe
            return False
