import json
from pathlib import Path

import pytest

from src.navigation.dom_extractor import extract_dom_summary
from src.navigation.engine import NavigationEngine
from src.navigation.models import NavigationState

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MOCK_PAGE = FIXTURES_DIR / "mock_page.html"


@pytest.fixture
def mock_page_url() -> str:
    return MOCK_PAGE.resolve().as_uri()


@pytest.fixture
def nav_engine(tmp_path) -> NavigationEngine:
    engine = NavigationEngine(
        headless=True, screenshots_dir=str(tmp_path / "screenshots")
    )
    yield engine
    engine.close()


def test_navigate_to_returns_valid_navigation_state(nav_engine, mock_page_url):
    state = nav_engine.navigate_to(mock_page_url)

    assert isinstance(state, NavigationState)
    assert state.screenshot_path
    assert Path(state.screenshot_path).is_file()
    assert state.page_title == "Mock Navigation Test Page"
    assert state.current_url.startswith("file://")
    assert len(state.visible_text_sample) > 0

    dom = json.loads(state.dom_tree_json)
    assert "elements" in dom
    assert len(dom["elements"]) >= 1


def test_perform_action_click_updates_state(nav_engine, mock_page_url):
    before = nav_engine.navigate_to(mock_page_url)
    after = nav_engine.perform_action("click", "#learn-more")

    assert after.current_url != before.current_url or after.dom_tree_json != before.dom_tree_json
    assert Path(after.screenshot_path).is_file()


def test_perform_action_fill_updates_input(nav_engine, mock_page_url):
    nav_engine.navigate_to(mock_page_url)
    after = nav_engine.perform_action("fill", "#email", "test@example.com")

    dom = json.loads(after.dom_tree_json)
    email_nodes = [e for e in dom["elements"] if e.get("tag") == "input"]
    assert email_nodes


def test_extract_dom_summary_includes_interactive_elements(nav_engine, mock_page_url):
    nav_engine.navigate_to(mock_page_url)
    page = nav_engine._page
    summary = extract_dom_summary(page)

    tags = {el["tag"] for el in summary["elements"]}
    assert "button" in tags
    assert "a" in tags
    assert "h1" in tags

    for el in summary["elements"]:
        assert "tag" in el
        assert "text" in el
        assert "aria_label" in el
        assert "href" in el
        assert "bounding_box" in el
