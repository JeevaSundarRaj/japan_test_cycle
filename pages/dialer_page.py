import json
import re
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

    def call(self, name: str, locator: str = "callResult") -> None:
        self.make_call_button.click()
        self.call_search.fill(name)
        # The first DOM match can be a hidden duplicate row; click the visible one.
        result = self.page.locator(LOCATORS[locator].format(name if locator == "callResult" else name.lower()))
        result.filter(visible=True).first.click()

    def call_number(self, number: str) -> None:
        """Dial a raw phone number (e.g. a main line) from the call search box."""
        self.make_call_button.click()
        self.call_search.fill(number)
        self.call_search.press("Enter")

    def open_operator_tab(self, mainline_name: str) -> None:
        self.page.get_by_role("link", name=re.compile(re.escape(mainline_name))).first.click()
        self.page.get_by_role("tab", name="オペレーター").click()

    def set_operator_active(self, active: bool) -> None:
        """Toggle the mainline operator switch to the wanted state and check the 対応可能 label."""
        toggle = self.page.get_by_role("switch", name="オペレーターの状態を切り替え")
        expect(toggle).to_be_visible(timeout=15000)
        if toggle.is_checked() != active:
            toggle.click()
        if active:
            expect(toggle).to_be_checked()
        else:
            expect(toggle).not_to_be_checked()
        expect(self.page.get_by_text("対応可能").first).to_be_visible()

    def call_from_conversation(self, name: str) -> None:
        """Open the contact's conversation from the sidebar and use its header call button."""
        self.page.locator(LOCATORS["sidebarLink"].format(name.lower())).first.click()
        self.page.locator(LOCATORS["conversationCallButton"]).first.click()

    def expect_notification(self, text: str, timeout: int = 30000) -> None:
        expect(self.page.get_by_text(text).first).to_be_visible(timeout=timeout)

    def expect_incoming_call_for(self, name: str, timeout: int = 30000) -> None:
        """The incoming-call popup reads '<name> への着信' for calls routed via a department/main line."""
        expect(self.page.get_by_text(f"{name} への着信").first).to_be_visible(timeout=timeout)

    def expect_answer_and_decline(self) -> None:
        expect(self.answer_button).to_be_visible(timeout=15000)
        expect(self.page.get_by_role("button", name="拒否", exact=True).first).to_be_visible(timeout=15000)

    def expect_cc_incoming_call(self, cc_name: str, mainline_name: str, timeout: int = 30000) -> None:
        """Contact-center popup: first line '<cc> への着信', second line the main line name."""
        expect(self.page.get_by_text(f"{cc_name} への着信").first).to_be_visible(timeout=timeout)
        popup = self.page.locator("div").filter(has_text=f"{cc_name} への着信").filter(
            has=self.page.get_by_text(mainline_name, exact=True)
        ).last
        expect(popup).to_be_visible(timeout=timeout)

    def answer(self) -> None:
        self.answer_button.click()
        expect(self.active_call.or_(self.hangup_button).first).to_be_visible(timeout=15000)

    def merge(self) -> None:
        # The incoming-call popup and the side panel both show 統合; either works.
        self.page.get_by_role("button", name="統合").first.click(timeout=15000)

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

    def hang_up_group_call(self) -> None:
        # The first hang-up only drops the added user; the original 2-party call remains.
        self.hangup_button.click()
        expect(self.callbar_button("転送")).to_be_visible(timeout=15000)
        self.hang_up()

    def close_add_call_dialog(self) -> None:
        # After the added user connects, a "connected" dialog blocks the call bar until 完了 is clicked.
        # The 完了 control isn't exposed as role=button, so match by text instead.
        done = self.page.get_by_text("完了", exact=True).last
        done.click(timeout=15000)
        expect(done).to_be_hidden(timeout=10000)

    def callbar_button(self, label: str):
        return self.page.locator(LOCATORS["callbarButton"].format(label))

    @property
    def ai_button(self):
        # Reads "AI OFF" while disabled and "AI" while enabled.
        return self.page.locator(LOCATORS["aiCallbarButton"]).first

    def is_ai_on(self) -> bool:
        return self.ai_button.inner_text().strip().upper() == "AI"

    def expect_callbar_buttons(self, labels: list[str]) -> None:
        for label in labels:
            expect(self.callbar_button(label)).to_be_visible(timeout=15000)

    def toggle_callbar_button(self, label: str, toggled_label: str) -> None:
        """Click a toggle button, check its label flips, then click back."""
        self.callbar_button(label).click()
        expect(self.callbar_button(toggled_label)).to_be_visible(timeout=10000)
        # The first click after a toggle can be swallowed while the button
        # re-renders, so retry until the original label comes back.
        for _ in range(3):
            self.callbar_button(toggled_label).click()
            try:
                expect(self.callbar_button(label)).to_be_visible(timeout=4000)
                return
            except AssertionError:
                if not self.callbar_button(toggled_label).is_visible():
                    break
        expect(self.callbar_button(label)).to_be_visible(timeout=10000)

    def add_user_to_call(self, search: str, name: str) -> None:
        self.callbar_button("追加").click()
        add_input = self.page.locator(LOCATORS["addCallerInput"])
        expect(add_input).to_be_visible(timeout=15000)
        add_input.press_sequentially(search, delay=50)
        self.page.locator(LOCATORS["addCallerResult"].format(name)).first.click()
        self.page.locator(LOCATORS["addCallerConfirm"]).click()
