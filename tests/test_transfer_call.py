from playwright.sync_api import expect

from tests.test_search_and_message import _end_calls, _screenshot_all, _start_call


def test_transfer_call(browser, credentials, test_data):
    pages, dialers = _start_call(browser, credentials, test_data["app_url"], extra_users=["admin_user"])
    lite_2, user_3 = dialers["lite_2_user"], dialers["admin_user"]
    try:
        # Lite 2 (on the call with lite 1) transfers it to user 3 (softbank).
        lite_2.transfer_to("user 3 JP softbank")

        # The transferred call rings as a plain incoming call (caller name + 応答/拒否).
        expect(user_3.answer_button).to_be_visible(timeout=30000)
        user_3.answer()
        expect(user_3.hangup_button).to_be_visible(timeout=30000)

        user_3.hang_up()
    except Exception:
        _screenshot_all(pages, "failure_transfer")
        raise
    finally:
        _end_calls(dialers)
