from playwright.sync_api import expect

from tests.test_search_and_message import _end_calls, _screenshot_all, _start_call


def test_add_user_to_call(browser, credentials, test_data):
    pages, dialers = _start_call(browser, credentials, test_data["app_url"], extra_users=["admin_user"])
    lite_1, user_3 = dialers["lite_1_user"], dialers["admin_user"]
    try:
        # Add user 3 (softbank) to the call and have them answer
        lite_1.add_user_to_call("user", "user 3 JP softbank")
        user_3.expect_notification("Lite", timeout=30000)
        user_3.answer()
        expect(user_3.hangup_button).to_be_visible(timeout=30000)

        # Dismiss the "user 3 connected" dialog, which blocks the hang-up button
        lite_1.close_add_call_dialog()
        lite_1.hang_up_group_call()
    except Exception:
        _screenshot_all(pages, "failure_add_user")
        raise
    finally:
        _end_calls(dialers)
