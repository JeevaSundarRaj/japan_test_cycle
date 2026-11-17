import json
from pathlib import Path

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

LOCATORS = json.loads((Path(__file__).parent / "locators.json").read_text())


class AssistantAppPage:
    """Dialpad app view of an assistant, showing an executive's conversation tabs."""

    def __init__(self, page: Page, app_url: str):
        self.page = page
        self.app_url = app_url
        self.tabs = page.locator(LOCATORS["conversationTabs"])

    def open_executive(self, executive: str, expect_tabs: bool = True) -> None:
        link_xpath = LOCATORS["executiveRow"].format(executive)
        # The pairing may not have propagated to this session yet, so reload until tabs show.
        for attempt in range(4 if expect_tabs else 1):
            self.page.goto(self.app_url)
            # Open the department section so the executive's row is visible.
            self.page.locator(LOCATORS["groupsButton"]).first.click()
            self.page.locator(link_xpath).first.click()
            if not expect_tabs:
                # Before permissions are granted there may be no tabs at all.
                self.page.wait_for_timeout(3000)
                return
            try:
                self.tabs.first.wait_for(state="visible", timeout=8000)
                return
            except PlaywrightTimeoutError:
                if attempt == 3:
                    raise

    def tab_count(self, executive: str, expect_tabs: bool = True) -> int:
        self.open_executive(executive, expect_tabs)
        return self.tabs.count()
