"""
Click verifier to ensure a coordinate is on a note card before clicking.
"""
import math
from typing import Dict, List, Optional
from playwright.async_api import Page
from config.settings import XHS_NOTE_CARD_SELECTORS


class ClickVerifier:
    """
    Utilities to validate and adjust click coordinates so they land on note cards.
    """

    def __init__(self, selectors: Optional[List[str]] = None):
        self.selectors = selectors or XHS_NOTE_CARD_SELECTORS
        self.selector_str = ",".join(self.selectors)

    async def validate(
        self,
        page: Page,
        x: int,
        y: int,
        bounding_box: Optional[Dict] = None
    ) -> Dict:
        """
        Validate a click position and optionally suggest a safer coordinate.
        """
        viewport = page.viewport_size
        if not self._is_in_viewport(x, y, viewport):
            return {
                "is_valid": False,
                "click_x": x,
                "click_y": y,
                "reason": "coordinate outside viewport",
            }

        element_hit = await self._element_from_point(page, x, y)
        if element_hit.get("is_note"):
            return {
                "is_valid": True,
                "click_x": x,
                "click_y": y,
                "reason": "elementFromPoint matches note selector",
                "meta": element_hit,
            }

        # Collect note card rects for further checks
        note_rects = await self._collect_note_rects(page, x, y)
        inside_rect = next((r for r in note_rects if r.get("contains")), None)
        if inside_rect:
            # Adjust to center to reduce edge misses
            return {
                "is_valid": True,
                "click_x": int(inside_rect["center_x"]),
                "click_y": int(inside_rect["center_y"]),
                "reason": "within note card bounding box",
                "meta": inside_rect,
            }

        # If model provided bounding box, check it
        if bounding_box and self._point_in_bbox(x, y, bounding_box):
            return {
                "is_valid": True,
                "click_x": x,
                "click_y": y,
                "reason": "within vision bounding box",
                "meta": {"bounding_box": bounding_box},
            }

        # Use nearest note card center as fallback
        nearest = self._find_nearest(note_rects, x, y)
        if nearest:
            return {
                "is_valid": False,
                "click_x": int(nearest["center_x"]),
                "click_y": int(nearest["center_y"]),
                "reason": "no direct hit; suggesting nearest note card center",
                "meta": nearest,
            }

        return {
            "is_valid": False,
            "click_x": x,
            "click_y": y,
            "reason": "no note card found near coordinate",
            "meta": element_hit,
        }

    @staticmethod
    def _is_in_viewport(x: int, y: int, viewport: Dict) -> bool:
        return 0 <= x <= viewport["width"] and 0 <= y <= viewport["height"]

    @staticmethod
    def _point_in_bbox(x: int, y: int, bbox: Dict) -> bool:
        return (
            x >= bbox.get("x", 0)
            and y >= bbox.get("y", 0)
            and x <= bbox.get("x", 0) + bbox.get("width", 0)
            and y <= bbox.get("y", 0) + bbox.get("height", 0)
        )

    async def _element_from_point(self, page: Page, x: int, y: int) -> Dict:
        """
        Inspect the DOM element at the given coordinate and see if it matches note selectors.
        """
        return await page.evaluate(
            """({ x, y, selectorStr }) => {
                const el = document.elementFromPoint(x, y);
                const isNote = !!(el && (el.matches?.(selectorStr) || el.closest?.(selectorStr)));
                const target = isNote && el ? (el.closest?.(selectorStr) || el) : el;
                return {
                    is_note: isNote,
                    tag: target?.tagName || null,
                    class: target?.className || null,
                    text: target?.innerText ? target.innerText.slice(0, 80) : null
                };
            }""",
            {"x": x, "y": y, "selectorStr": self.selector_str},
        )

    async def _collect_note_rects(self, page: Page, x: int, y: int) -> List[Dict]:
        """
        Collect bounding boxes for candidate note cards to test containment and nearest center.
        """
        return await page.evaluate(
            """({ clickX, clickY, selectorStr }) => {
                const nodes = Array.from(document.querySelectorAll(selectorStr));
                return nodes.map((el) => {
                    const rect = el.getBoundingClientRect();
                    return {
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        center_x: rect.x + rect.width / 2,
                        center_y: rect.y + rect.height / 2,
                        contains: rect.x <= clickX && clickX <= rect.x + rect.width &&
                                  rect.y <= clickY && clickY <= rect.y + rect.height,
                        text: (el.innerText || "").slice(0, 80)
                    };
                });
            }""",
            {"clickX": x, "clickY": y, "selectorStr": self.selector_str},
        )

    @staticmethod
    def _find_nearest(note_rects: List[Dict], x: int, y: int) -> Optional[Dict]:
        """
        Find nearest note card center to the provided coordinate.
        """
        nearest = None
        min_dist = float("inf")
        for rect in note_rects:
            cx, cy = rect.get("center_x"), rect.get("center_y")
            if cx is None or cy is None:
                continue
            dist = math.hypot(cx - x, cy - y)
            if dist < min_dist:
                min_dist = dist
                nearest = rect | {"distance": dist}
        return nearest
