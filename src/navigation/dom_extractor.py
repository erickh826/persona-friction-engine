from __future__ import annotations

from typing import Any


def extract_dom_summary(page: Any) -> dict[str, list[dict[str, Any]]]:
    """Return a compact summary of visible interactive and semantic elements."""
    return page.evaluate(
        """
        () => {
          const selectors = [
            'button',
            'input',
            'select',
            'textarea',
            'a',
            'h1',
            'h2',
            'h3',
            'h4',
            'h5',
            'h6',
            'img',
            '[role="button"]',
            '[role="link"]'
          ];

          const seen = new Set();
          const elements = [];

          for (const element of document.querySelectorAll(selectors.join(','))) {
            if (seen.has(element)) {
              continue;
            }
            seen.add(element);

            const rect = element.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) {
              continue;
            }

            const tag = element.tagName.toLowerCase();
            const href = tag === 'a' ? element.href : null;
            const text = (
              element.innerText ||
              element.value ||
              element.getAttribute('alt') ||
              element.getAttribute('title') ||
              ''
            ).trim();

            elements.push({
              tag,
              text,
              aria_label: element.getAttribute('aria-label') || '',
              href,
              bounding_box: {
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                width: Math.round(rect.width),
                height: Math.round(rect.height)
              }
            });
          }

          return { elements };
        }
        """
    )
