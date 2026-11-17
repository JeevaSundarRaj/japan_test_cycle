import time
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import expect

from pages.dialer_page import DialerPage
from pages.login_page import LoginPage
from pages.messaging_page import MessagingPage

MMS_IMAGE = Path(__file__).resolve().parent.parent / "red rose.jpg"
SCREENSHOT_DIR = Path(__file__).resolve().parent.parent / "screenshots"


def _now_local():
    # The browser renders message times in the machine's local timezone
    return datetime.now()


def _minutes_between(start, end):
    """HH:MM labels from start's minute to end's minute (+1 for clock skew)."""
    start = start.replace(second=0, microsecond=0)
    labels, t = [], start
    while t <= end + timedelta(minutes=1):
        labels.append(t.strftime("%H:%M"))
        t += timedelta(minutes=1)
    return labels


def _logged_in_page(browser, creds, app_url):
    context = browser.new_context(permissions=["microphone", "camera", "notifications"])
    page = context.new_page()
    LoginPage(page).login(creds["email"], creds["password"])
    page.goto(app_url)
    return page


def test_search_user_and_send_message_with_image(browser, credentials, test_data):
    app_url = test_data["app_url"]
    lite_1_page = _logged_in_page(browser, credentials["lite_1_user"], app_url)
    lite_2_page = _logged_in_page(browser, credentials["lite_2_user"], app_url)

    sender = MessagingPage(lite_1_page, app_url)
    receiver = MessagingPage(lite_2_page, app_url)
    try:
        text = f"test {int(time.time())}"

        # Lite 1 searches for Lite 2 and sends SMS + MMS
        sender.search_and_open_contact("Lite 2")
        sent_from = _now_local()
        sender.send_text(text)
        sender.expect_text_received(text)

        sender_images_before = sender.mms_images.count()
        sender.send_image(str(MMS_IMAGE))
        sender.expect_image_received(sender_images_before)
        sent_to = _now_local()

        # Lite 2 searches for Lite 1 and verifies the messages arrived
        receiver.search_and_open_contact("Lite 1")
        receiver.expect_text_received(text)
        receiver.expect_image_received()
        receiver.expect_last_message_time_in(_minutes_between(sent_from, sent_to))
    except Exception:
        SCREENSHOT_DIR.mkdir(exist_ok=True)
        lite_1_page.screenshot(path=str(SCREENSHOT_DIR / "failure_lite_1.png"))
        lite_2_page.screenshot(path=str(SCREENSHOT_DIR / "failure_lite_2.png"))
        raise


def _start_call(browser, credentials, app_url, extra_users=()):
    """Lite 1 calls Lite 2 and Lite 2 answers. Returns pages and dialers keyed by user."""
    keys = ["lite_1_user", "lite_2_user", *extra_users]
    pages = {k: _logged_in_page(browser, credentials[k], app_url) for k in keys}
    dialers = {k: DialerPage(p) for k, p in pages.items()}

    try:
        dialers["lite_1_user"].call("Lite 2")
        dialers["lite_2_user"].expect_notification("Lite 1")
        dialers["lite_2_user"].answer()
        expect(dialers["lite_1_user"].hangup_button).to_be_visible(timeout=30000)
    except Exception:
        _end_calls(dialers)
        raise
    return pages, dialers


def _end_calls(dialers):
    """End any call still open so the next run starts clean."""
    for d in dialers.values():
        try:
            if d.hangup_button.is_visible():
                d.hangup_button.click()
                expect(d.hangup_button).to_be_hidden(timeout=10000)
        except Exception:
            pass


def _screenshot_all(pages, prefix):
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    for name, pg in pages.items():
        pg.screenshot(path=str(SCREENSHOT_DIR / f"{prefix}_{name}.png"))
