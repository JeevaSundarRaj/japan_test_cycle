import json
from pathlib import Path

from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

LOCATORS = json.loads((Path(__file__).parent / "locators.json").read_text())


class DialerPage:
    def __init__(self, page: Page):
        self.page = page
        self.make_call_button = page.locator(LOCATORS["makeCallButton"])
        self.call_search = page.locator(LOCATORS["callSearch"])
        self.hangup_button = page.get_by_role("button", name="終了", exact=True)
        self.answer_button = page.get_by_role("button", name="応答", exact=True)
        self.accept_button = page.locator(LOCATORS["acceptButton"]).or_(
            page.get_by_role("button", name="承諾")
        ).first
        self.active_call = page.locator(LOCATORS["activeCall"])
        self.transfer_button = page.locator(LOCATORS["transferButton"]).or_(
            page.get_by_role("button", name="転送", exact=True)
        ).first
        self.transfer_search = page.locator(LOCATORS["transferSearch"])
        self.transfer_confirm = page.get_by_role("button", name="そのまま転送")

    def call(self, name: str) -> None:
        self.make_call_button.click()
        self.call_search.fill(name)
        self.page.locator(LOCATORS["callResult"].format(name)).first.click()

    def expect_notification(self, text: str, timeout: int = 30000) -> None:
        expect(self.page.get_by_text(text).first).to_be_visible(timeout=timeout)

    def answer(self) -> None:
        self.answer_button.click()
        expect(self.active_call.or_(self.hangup_button).first).to_be_visible(timeout=15000)

    def accept(self) -> None:
        # The accept prompt doesn't always show after answering; carry on without it.
        try:
            self.accept_button.click(timeout=10000)
        except PlaywrightTimeoutError:
            pass

    def transfer_to(self, name: str) -> None:
        # The call bar's wrapper class changes; wait on the call controls instead.
        expect(self.hangup_button).to_be_visible(timeout=30000)
        self.hangup_button.hover()
        expect(self.transfer_button).to_be_visible(timeout=15000)
        self.transfer_button.click()
        self.transfer_search.fill(name)
        self.page.locator(LOCATORS["transferTarget"].format(name)).first.click()
        self.transfer_confirm.or_(self.page.get_by_role("button", name="そのまま転送")).first.click()

    def hang_up(self) -> None:
        self.hangup_button.click()
        expect(self.hangup_button).to_be_hidden()
