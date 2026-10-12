import json
from pathlib import Path

from playwright.sync_api import Page, expect

LOCATORS = json.loads((Path(__file__).parent / "locators.json").read_text())


class AssistantAppPage:
    """Dialpad app view of an assistant, showing an executive's conversation tabs."""

    def __init__(self, page: Page, app_url: str):
        self.page = page
        self.app_url = app_url
        self.tabs = page.locator(LOCATORS["conversationTabs"])

    def open_executive(self, executive: str) -> None:
        self.page.goto(self.app_url)
        self.page.locator(LOCATORS["sidebarLink"].format(executive)).first.click()
        expect(self.tabs.first).to_be_visible()

    def tab_count(self, executive: str) -> int:
        self.open_executive(executive)
        return self.tabs.count()
