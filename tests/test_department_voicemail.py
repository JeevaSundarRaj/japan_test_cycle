from playwright.sync_api import expect

from pages.dialer_page import DialerPage
from tests.test_search_and_message import _end_calls, _logged_in_page, _screenshot_all

USERS = ("admin_user", "test_support_user")
DEPARTMENT_NUMBER = "050-1749-9615"
VOICEMAIL_TEXT = (
    "発信音の後にメッセージを録音してください。"
    "録音が終了したら電話を切るか、 1 を押して他のオプションを選択してください"
)


def test_departent_voicemail(browser, credentials, test_data):
    app_url = test_data["app_url"]
    pages = {k: _logged_in_page(browser, credentials[k], app_url) for k in USERS}
    dialers = {k: DialerPage(p) for k, p in pages.items()}
    user_3, support = (dialers[k] for k in USERS)
    try:
        # User 3 calls the test department number
        user_3.call_number(DEPARTMENT_NUMBER)

        # Test Support receives the call and declines it
        expect(support.answer_button).to_be_visible(timeout=30000)
        support.page.get_by_role("button", name="拒否", exact=True).first.click()

        # The voicemail greeting shows up in the transcription on user 3
        expect(user_3.page.get_by_text(VOICEMAIL_TEXT).first).to_be_visible(timeout=60000)
    except Exception:
        _screenshot_all(pages, "failure_department_voicemail")
        raise
    finally:
        _end_calls(dialers)
