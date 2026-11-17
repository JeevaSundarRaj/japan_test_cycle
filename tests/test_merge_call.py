from playwright.sync_api import expect

from tests.test_search_and_message import _end_calls, _screenshot_all, _start_call


def test_merge_call(browser, credentials, test_data):
    pages, dialers = _start_call(browser, credentials, test_data["app_url"], extra_users=["admin_user"])
    lite_1, lite_2, user_3 = dialers["lite_1_user"], dialers["lite_2_user"], dialers["admin_user"]
    try:
        # Lite 1 and Lite 2 are on a call; user 3 calls Lite 1
        user_3.call("Lite 1", "callResultCallBtn")

        # Lite 1 gets an incoming-call notification with a merge option
        lite_1.expect_notification("user 3", timeout=30000)
        lite_1.merge()
        expect(lite_1.hangup_button).to_be_visible(timeout=30000)
        expect(user_3.hangup_button).to_be_visible(timeout=15000)
        expect(lite_2.hangup_button).to_be_visible(timeout=15000)

        # End every leg of the merged call
        _end_calls(dialers)
        _end_calls(dialers)
        for d in dialers.values():
            expect(d.hangup_button).to_be_hidden(timeout=15000)
    except Exception:
        _screenshot_all(pages, "failure_merge")
        raise
    finally:
        _end_calls(dialers)
