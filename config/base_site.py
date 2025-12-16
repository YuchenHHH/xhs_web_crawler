"""
Platform-specific crawler strategies - Abstract base class
Defines standard interface for multi-platform support
"""
from abc import ABC, abstractmethod
from typing import List, Dict
from playwright.async_api import Page


class CrawlerStrategy(ABC):
    """
    Abstract base class for platform-specific crawler strategies
    Each platform (XHS, Pinterest, Instagram) implements this interface
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Platform identifier (e.g., 'xiaohongshu', 'pinterest')"""
        pass

    @property
    @abstractmethod
    def home_url(self) -> str:
        """Platform home URL"""
        pass

    @property
    @abstractmethod
    def search_input_selectors(self) -> List[str]:
        """CSS selectors for search input field (priority-ordered)"""
        pass

    @property
    @abstractmethod
    def note_card_selectors(self) -> List[str]:
        """CSS selectors for note cards (priority-ordered)"""
        pass

    @property
    @abstractmethod
    def note_detail_selectors(self) -> Dict[str, str]:
        """CSS selectors for note detail page elements"""
        pass

    @property
    @abstractmethod
    def note_image_selectors(self) -> List[str]:
        """CSS selectors for images in note detail page"""
        pass

    @abstractmethod
    async def detect_login_status(self, page: Page) -> bool:
        """
        Platform-specific login detection logic

        Args:
            page: Playwright Page object

        Returns:
            True if logged in, False otherwise
        """
        pass
