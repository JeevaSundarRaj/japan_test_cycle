from playwright.sync_api import expect

from pages.dialer_page import DialerPage
from tests.test_search_and_message import _end_calls, _logged_in_page, _screenshot_all

USERS = ("lite_1_user", "admin_user")


def test_outbound_call(browser, credentials, test_data):
    app_url = test_data["app_url"]
    pages = {k: _logged_in_page(browser, credentials[k], app_url) for k in USERS}
    dialers = {k: DialerPage(p) for k, p in pages.items()}
    lite_1, user_3 = (dialers[k] for k in USERS)
    try:
        # Lite 1 searches for user 3 and calls; user 3 answers, then the call is cut
        lite_1.call("user 3", "callResultCallBtn")
        user_3.expect_notification("Lite 1", timeout=30000)
        user_3.answer()
        expect(lite_1.hangup_button).to_be_visible(timeout=30000)
        expect(user_3.hangup_button).to_be_visible(timeout=15000)
        lite_1.page.wait_for_timeout(3000)
        lite_1.hang_up()
        expect(user_3.hangup_button).to_be_hidden(timeout=15000)

        # User 3 searches for Lite 1 and calls; Lite 1 answers, then the call is cut
        user_3.call("Lite 1", "callResultCallBtn")
        lite_1.expect_notification("user 3", timeout=30000)
        lite_1.answer()
        expect(user_3.hangup_button).to_be_visible(timeout=30000)
        expect(lite_1.hangup_button).to_be_visible(timeout=15000)
        user_3.page.wait_for_timeout(3000)
        user_3.hang_up()
        expect(lite_1.hangup_button).to_be_hidden(timeout=15000)
    except Exception:
        _screenshot_all(pages, "failure_outbound_call")
        raise
    finally:
        _end_calls(dialers)
