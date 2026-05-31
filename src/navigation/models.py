from pydantic import BaseModel


class NavigationState(BaseModel):
    current_url: str
    dom_tree_json: str
    screenshot_path: str
    page_title: str
    visible_text_sample: str
