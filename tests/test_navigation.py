import json
from pathlib import Path

import pytest

from src.navigation.engine import NavigationEngine
from src.navigation.models import NavigationState


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mock_page.html"


@pytest.fixture
def engine(tmp_path):
    navigation_engine = NavigationEngine(
        headless=True, screenshots_dir=str(tmp_path / "screenshots")
    )
    try:
        yield navigation_engine
    finally:
        navigation_engine.close()


def test_navigate_to_returns_valid_navigation_state(engine):
    state = engine.navigate_to(FIXTURE_PATH.resolve().as_uri())

    assert isinstance(state, NavigationState)
    assert state.current_url.startswith("file://")
    assert state.page_title == "Mock Checkout Page"
    assert "Mock Store" in state.visible_text_sample
    assert Path(state.screenshot_path).is_file()

    dom_tree = json.loads(state.dom_tree_json)
    elements = dom_tree["elements"]
    assert any(el["tag"] == "button" and el["text"] == "Buy Now" for el in elements)
    assert all("bounding_box" in el for el in elements)


def test_perform_click_returns_updated_url_and_dom_state(engine):
    engine.navigate_to(FIXTURE_PATH.resolve().as_uri())

    state = engine.perform_action("click", "#buy-button")

    assert state.current_url.endswith("#checkout")
    assert Path(state.screenshot_path).is_file()
    assert "Buy Now" in state.dom_tree_json


def test_perform_fill_updates_input_value_in_dom_state(engine):
    engine.navigate_to(FIXTURE_PATH.resolve().as_uri())

    state = engine.perform_action("fill", "#search", "laptop")
    dom_tree = json.loads(state.dom_tree_json)

    assert any(el["tag"] == "input" and el["text"] == "laptop" for el in dom_tree["elements"])


def test_perform_scroll_returns_new_state(engine):
    engine.navigate_to(FIXTURE_PATH.resolve().as_uri())

    state = engine.perform_action("scroll", "#details")

    assert "Product Details" in state.dom_tree_json
    assert Path(state.screenshot_path).is_file()


def test_unsupported_action_raises_value_error(engine):
    engine.navigate_to(FIXTURE_PATH.resolve().as_uri())

    with pytest.raises(ValueError):
        engine.perform_action("drag", "#buy-button")
