import json
from typing import Any

from playwright.sync_api import Page

_INTERACTIVE_SELECTORS = (
    "button, input, a[href], select, textarea, "
    "h1, h2, h3, h4, h5, h6, img"
)


def extract_dom_summary(page: Page) -> dict[str, Any]:
    """Return a simplified DOM tree of interactive and structural elements."""
    raw_elements: list[dict[str, Any]] = page.evaluate(
        """(selector) => {
            const nodes = Array.from(document.querySelectorAll(selector));
            return nodes.map((el) => {
                const rect = el.getBoundingClientRect();
                const text = (el.innerText || el.textContent || "").trim().slice(0, 200);
                const aria = el.getAttribute("aria-label") || "";
                const href = el.tagName === "A" ? (el.getAttribute("href") || "") : "";
                return {
                    tag: el.tagName.toLowerCase(),
                    text,
                    aria_label: aria,
                    href,
                    bounding_box: {
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                    },
                };
            });
        }""",
        _INTERACTIVE_SELECTORS,
    )

    return {"elements": raw_elements}


def serialize_dom_summary(page: Page) -> str:
    return json.dumps(extract_dom_summary(page))
