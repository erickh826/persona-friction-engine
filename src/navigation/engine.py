import os
import time
import uuid
from pathlib import Path
from urllib.parse import unquote, urljoin

from playwright.sync_api import Page, sync_playwright

from src.navigation.dom_extractor import extract_dom_summary, serialize_dom_summary
from src.navigation.models import NavigationState


class NavigationEngine:
    def __init__(self, headless: bool = True, screenshots_dir: str = "screenshots/"):
        self.headless = headless
        self.screenshots_dir = screenshots_dir
        Path(self.screenshots_dir).mkdir(parents=True, exist_ok=True)
        self._playwright = None
        self._browser = None
        self._page: Page | None = None

    def _ensure_browser(self) -> Page:
        if self._page is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._page = self._browser.new_page()
        return self._page

    def _to_navigation_url(self, url: str) -> str:
        if url.startswith("file://"):
            return url
        path = Path(url)
        if path.exists():
            return path.resolve().as_uri()
        return url

    def _capture_state(self) -> NavigationState:
        page = self._ensure_browser()
        dom_tree_json = serialize_dom_summary(page)
        screenshot_path = os.path.join(
            self.screenshots_dir,
            f"screenshot_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}.png",
        )
        page.screenshot(path=screenshot_path, full_page=True)

        try:
            visible_text = page.inner_text("body")
        except Exception:
            visible_text = ""
        visible_text_sample = visible_text[:500]

        return NavigationState(
            current_url=page.url,
            dom_tree_json=dom_tree_json,
            screenshot_path=screenshot_path,
            page_title=page.title(),
            visible_text_sample=visible_text_sample,
        )

    def navigate_to(self, url: str) -> NavigationState:
        page = self._ensure_browser()
        target = self._to_navigation_url(url)
        page.goto(target, wait_until="networkidle")
        return self._capture_state()

    def perform_action(
        self, action: str, selector: str, value: str | None = None
    ) -> NavigationState:
        page = self._ensure_browser()
        action_lower = action.lower()

        if action_lower == "click":
            page.click(selector)
        elif action_lower == "fill":
            page.fill(selector, value or "")
        elif action_lower == "scroll":
            if selector:
                page.locator(selector).scroll_into_view_if_needed()
            else:
                page.evaluate("window.scrollBy(0, window.innerHeight)")
        else:
            raise ValueError(
                f"Unsupported action {action!r}. Use 'click', 'fill', or 'scroll'."
            )

        page.wait_for_load_state("networkidle")
        return self._capture_state()

    def close(self) -> None:
        if self._page is not None:
            self._page.close()
            self._page = None
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
