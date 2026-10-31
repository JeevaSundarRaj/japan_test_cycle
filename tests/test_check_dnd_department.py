from playwright.sync_api import expect

from pages.dialer_page import DialerPage
from tests.test_search_and_message import _end_calls, _logged_in_page, _screenshot_all

USERS = ("lite_1_user", "admin_user", "test_support_user")


def test_check_dnd_department(browser, credentials, test_data):
    app_url = test_data["app_url"]
    number = test_data["mainline_number"]
    pages = {k: _logged_in_page(browser, credentials[k], app_url) for k in USERS}
    dialers = {k: DialerPage(p) for k, p in pages.items()}
    lite_1, user_3, support = (dialers[k] for k in USERS)
    try:
        # JP user 3 starts with the main line operator active
        user_3.open_operator_tab(test_data["mainline_name"])
        user_3.set_operator_active(True)

        # Lite 1 calls the main line; the R&D department routes it to JP user 3
        lite_1.call_number(number)
        user_3.expect_incoming_call_for(test_data["mainline_name"], timeout=30000)
        user_3.answer()
        expect(lite_1.hangup_button).to_be_visible(timeout=30000)
        expect(user_3.hangup_button).to_be_visible(timeout=15000)
        user_3.hang_up()
        expect(lite_1.hangup_button).to_be_hidden(timeout=15000)

        # JP user 3 sets the main line operator to inactive
        user_3.open_operator_tab(test_data["mainline_name"])
        user_3.set_operator_active(False)

        # Lite 1 calls again; the call now routes to Test Support (test cc)
        lite_1.call_number(number)
        support.expect_cc_incoming_call(test_data["cc_name"], test_data["mainline_name"])
        support.expect_answer_and_decline()
        support.answer()
        expect(lite_1.hangup_button).to_be_visible(timeout=30000)
        support.hang_up()
        expect(lite_1.hangup_button).to_be_hidden(timeout=15000)
    except Exception:
        _screenshot_all(pages, "failure_rnd_department")
        raise
    finally:
        _end_calls(dialers)
