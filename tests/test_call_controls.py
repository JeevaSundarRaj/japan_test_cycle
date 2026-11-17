from playwright.sync_api import expect

from pages.dialer_page import LOCATORS
from tests.test_search_and_message import _end_calls, _screenshot_all, _start_call

CALLBAR_BUTTONS = ["ミュート", "保留", "転送", "録音", "キーパッド", "追加", "共有", "パーク保留"]


def test_call_controls(browser, credentials, test_data):
    pages, dialers = _start_call(browser, credentials, test_data["app_url"])
    lite_1 = dialers["lite_1_user"]
    try:
        # All call bar buttons are present during the call
        lite_1.expect_callbar_buttons(CALLBAR_BUTTONS)

        # AI button is present on the call bar and opens the AI popover
        expect(lite_1.ai_button).to_be_visible(timeout=15000)
        lite_1.ai_button.click()
        enable_ai = lite_1.page.locator(LOCATORS["aiEnableButton"]).first
        expect(enable_ai).to_be_visible(timeout=15000)
        enable_ai.click()
        expect(lite_1.ai_button).to_have_text("AI", timeout=15000)
        lite_1.page.keyboard.press("Escape")

        # Toggle buttons flip their label and back
        lite_1.toggle_callbar_button("ミュート", "ミュート解除")
        lite_1.toggle_callbar_button("保留", "再開")
        lite_1.toggle_callbar_button("録音", "停止")

        # Keypad opens and closes without dropping the call
        lite_1.callbar_button("キーパッド").click()
        lite_1.callbar_button("キーパッド").click()
        expect(lite_1.hangup_button).to_be_visible()

        lite_1.hang_up()
    except Exception:
        _screenshot_all(pages, "failure_controls")
        raise
    finally:
        _end_calls(dialers)
