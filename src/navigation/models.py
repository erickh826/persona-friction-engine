from pydantic import BaseModel, Field


class NavigationState(BaseModel):
    current_url: str
    dom_tree_json: str = Field(
        description="Serialized DOM summary JSON from extract_dom_summary"
    )
    screenshot_path: str
    page_title: str
    visible_text_sample: str = Field(
        max_length=500,
        description="First 500 characters of visible page text",
    )
