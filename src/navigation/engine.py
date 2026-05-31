from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from src.navigation.dom_extractor import extract_dom_summary
from src.navigation.models import NavigationState


class NavigationEngine:
    def __init__(self, headless: bool = True, screenshots_dir: str = "screenshots/"):
        self.headless = headless
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._step_counter = 0

    def navigate_to(self, url: str) -> NavigationState:
        page = self._ensure_page()
        page.goto(url, wait_until="networkidle")
        return self._capture_state()

    def perform_action(
        self, action: str, selector: str, value: str | None = None
    ) -> NavigationState:
        page = self._require_page()
        normalized_action = action.lower()

        if normalized_action == "click":
            page.click(selector)
        elif normalized_action == "fill":
            if value is None:
                raise ValueError("value is required for fill actions.")
            page.fill(selector, value)
        elif normalized_action == "scroll":
            self._scroll(selector, value)
        else:
            raise ValueError(f"Unsupported navigation action: {action}")

        page.wait_for_load_state("networkidle")
        return self._capture_state()

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
            self._context = None
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
        self._page = None

    def _ensure_page(self) -> Page:
        if self._page is not None:
            return self._page

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context()
        self._page = self._context.new_page()
        return self._page

    def _require_page(self) -> Page:
        if self._page is None:
            raise RuntimeError("navigate_to must be called before perform_action.")
        return self._page

    def _capture_state(self) -> NavigationState:
        page = self._require_page()
        self._step_counter += 1
        screenshot_path = self.screenshots_dir / f"step_{self._step_counter:03}.png"
        page.screenshot(path=str(screenshot_path), full_page=True)

        dom_summary = extract_dom_summary(page)
        visible_text = page.evaluate("() => document.body ? document.body.innerText : ''")

        return NavigationState(
            current_url=page.url,
            dom_tree_json=json.dumps(dom_summary, sort_keys=True),
            screenshot_path=str(screenshot_path),
            page_title=page.title(),
            visible_text_sample=visible_text[:500],
        )

    def _scroll(self, selector: str, value: str | None) -> None:
        page = self._require_page()
        if selector:
            page.locator(selector).scroll_into_view_if_needed()

        if value is None:
            return

        delta_y = self._parse_scroll_delta(value)
        if delta_y:
            page.mouse.wheel(0, delta_y)

    def _parse_scroll_delta(self, value: str) -> int:
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError("scroll value must be an integer pixel delta.") from exc
