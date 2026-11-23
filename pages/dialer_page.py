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

    def set_caller_id(self, persona: str) -> None:
        """Switch the persona (caller ID) shown in the call dialog."""
        button = self.page.get_by_role("button", name=re.compile("現在のペルソナは"))
        # Already selected: opening the dropdown would only cover the label.
        if persona in (button.get_attribute("aria-label") or button.inner_text()):
            return
        button.click()
        # The button's own label matches the text too; the dropdown option is the last match.
        self.page.get_by_text(persona, exact=True).last.click()

    def restore_caller_id(self, persona: str) -> None:
        self.make_call_button.click()
        self.set_caller_id(persona)
        self.close_new_call_overlay()

    def close_new_call_overlay(self) -> None:
        """The new-call search overlay intercepts clicks (e.g. on the incoming-call Answer button)."""
        overlay = self.page.locator("#overlay.app-overlay-newcall")
        for _ in range(3):
            if not overlay.count() or not overlay.is_visible():
                return
            self.page.keyboard.press("Escape")
            try:
                overlay.wait_for(state="hidden", timeout=2000)
                return
            except PlaywrightTimeoutError:
                pass
        expect(overlay).to_be_hidden(timeout=5000)

    def expect_ai_on(self, timeout: int = 30000) -> None:
        expect(self.ai_button).to_have_text(re.compile(r"^\s*AI\s*$", re.I), timeout=timeout)

    def ensure_ai_on(self) -> None:
        """Turn AI on from the call bar if it reads 'AI OFF', then confirm it reads 'AI'."""
        expect(self.ai_button).to_be_visible(timeout=30000)
        if not self.is_ai_on():
            self.ai_button.click()
            enable = self.page.locator(LOCATORS["aiEnableButton"]).first
            try:
                enable.click(timeout=5000)
            except PlaywrightTimeoutError:
                switch = self.page.get_by_role("switch", name=re.compile("Aiが有効"))
                if switch.count() and not switch.first.is_checked():
                    switch.first.click()
        self.expect_ai_on()

    def expect_transcribing(self, timeout: int = 60000) -> None:
        # The AI dialog's トランスクリプト tab panel fills with text once audio is transcribed.
        panel = self.page.get_by_role("tabpanel", name="トランスクリプト")
        # Click the AI button to open the AI dialog (skip if ensure_ai_on left it open).
        if not panel.is_visible():
            self.ai_button.click()
            expect(panel).to_be_visible(timeout=15000)
        expect(panel).to_have_text(re.compile(r"\S{5,}"), timeout=timeout)

    def call(self, name: str, locator: str = "callResult", caller_id: str | None = None) -> None:
        # Pages sharing a browser are throttled in the background; focus this one first.
        self.page.bring_to_front()
        self.dismiss_wrap_up(timeout=1500)
        self.make_call_button.click()
        if caller_id:
            self.set_caller_id(caller_id)
        # The first DOM match can be a hidden duplicate row; click the visible one.
        result = self.page.locator(LOCATORS[locator].format(name if locator == "callResult" else name.lower()))
        for attempt in range(3):
            self.call_search.click()
            self.call_search.fill("")
            self.call_search.press_sequentially(name, delay=50)
            try:
                result.filter(visible=True).first.click(timeout=10000)
                return
            except PlaywrightTimeoutError:
                if attempt == 2:
                    raise

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
        self.close_new_call_overlay()
        # Backgrounded/occluded headed windows stop rendering frames, which hangs Playwright's
        # scroll-into-view step; focus the page first and fall back to a DOM click.
        self.page.bring_to_front()
        try:
            self.answer_button.click(timeout=5000)
        except PlaywrightTimeoutError:
            self.answer_button.dispatch_event("click")
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

    def dismiss_wrap_up(self, timeout: int = 5000) -> None:
        """Close the post-call wrap-up modal if it shows; it blocks the call button."""
        modal = self.page.locator("dialog.post-call-wrap-up-modal[open]")
        try:
            modal.wait_for(state="visible", timeout=timeout)
        except PlaywrightTimeoutError:
            return
        self.page.keyboard.press("Escape")
        if modal.is_visible():
            # The form is rendered inside an iframe ("document" in the aria tree), so try both roots.
            for root in (modal, modal.frame_locator("iframe")):
                self._fill_wrap_up_call_type(root)
                close = root.locator("button:not([disabled])").filter(
                    has_text=re.compile("閉じる|キャンセル|スキップ|完了|保存|Close|Skip|Done|Save", re.I))
                try:
                    close.first.click(timeout=3000)
                    break
                except PlaywrightTimeoutError:
                    pass
            if modal.is_visible():
                # Last resort: the dialog's own X button ("Click to close").
                x_btn = modal.get_by_role("button", name=re.compile("close", re.I)).or_(
                    modal.locator("[data-qa='dt-modal-close']"))
                try:
                    x_btn.first.click(timeout=3000, force=True)
                except PlaywrightTimeoutError:
                    pass
        expect(modal).to_be_hidden(timeout=10000)

    def _fill_wrap_up_call_type(self, modal) -> None:
        """通話タイプ is required; 完了 stays disabled until one is picked."""
        done = modal.get_by_role("button", name="完了")
        try:
            # Quick pick from the "最もよく使用" suggestions, else choose the first dropdown option.
            suggestion = modal.get_by_text("最もよく使用").locator("xpath=..").locator("a, button, [role=button], [role=link]").first
            suggestion.click(timeout=2000)
            expect(done).to_be_enabled(timeout=2000)
            return
        except (PlaywrightTimeoutError, AssertionError):
            pass
        try:
            field = modal.get_by_placeholder("2個まで入力できます")
            field.click(timeout=2000)
            modal.get_by_role("option").first.click(timeout=3000)
            expect(done).to_be_enabled(timeout=2000)
        except (PlaywrightTimeoutError, AssertionError):
            pass

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

    def set_muted(self, muted: bool) -> None:
        """Mute/unmute the mic from the call bar (no-op if already in the wanted state)."""
        wanted, current = ("ミュート解除", "ミュート") if muted else ("ミュート", "ミュート解除")
        if self.callbar_button(current).is_visible():
            self.callbar_button(current).click()
        expect(self.callbar_button(wanted)).to_be_visible(timeout=10000)

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
