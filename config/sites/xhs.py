"""
Xiaohongshu (小红书) crawler strategy implementation
"""
from typing import List, Dict
from playwright.async_api import Page

from config.base_site import CrawlerStrategy


class XHSCrawlerStrategy(CrawlerStrategy):
    """
    Xiaohongshu (小红书) crawler strategy implementation
    """

    @property
    def platform_name(self) -> str:
        return "xiaohongshu"

    @property
    def home_url(self) -> str:
        return "https://www.xiaohongshu.com/explore"

    @property
    def search_input_selectors(self) -> List[str]:
        return [
            "input#search-input",
            "[placeholder='搜索小红书']",
            "input[type='text'].search-input"
        ]

    @property
    def note_card_selectors(self) -> List[str]:
        return [
            "a[href*='/explore/']",
            ".note-item",
            "[class*='note-card']",
            ".feeds-container > div > a",
        ]

    @property
    def note_detail_selectors(self) -> Dict[str, str]:
        return {
            "title": ".note-title, .title, [class*='title']",
            "author": ".author-name, .user-name, [class*='author']",
            "content": ".note-content, .content-text, [class*='content']",
            "likes": "[class*='like-count'], .like-wrapper",
        }

    @property
    def note_image_selectors(self) -> List[str]:
        return [
            ".carousel img",
            ".note-slider img",
            "[class*='swiper'] img",
            ".note-detail img",
            "img[src*='sns-img']",
            ".note-content img",
        ]

    async def detect_login_status(self, page: Page) -> bool:
        """
        XHS-specific login detection:
        1. Check for login/register buttons (visible = not logged in)
        2. Check for user avatar (visible = logged in)
        """
        try:
            login_button = page.locator("text=登录").or_(page.locator("text=注册"))
            if await login_button.is_visible(timeout=3000):
                return False

            user_avatar = page.locator(".user-avatar, .avatar, [class*='user']").first
            if await user_avatar.is_visible(timeout=3000):
                return True

        except Exception as e:
            print(f"⚠️  登录检测异常: {e}")

        return False
