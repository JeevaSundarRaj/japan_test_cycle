import time
from pathlib import Path

from playwright.sync_api import expect

from pages.admin_settings_page import AdminSettingsPage
from pages.assistant_app_page import AssistantAppPage
from pages.dialer_page import DialerPage
from pages.login_page import LoginPage
from pages.messaging_page import MessagingPage

MMS_IMAGE = Path(__file__).resolve().parent.parent / "red rose.jpg"


def _logged_in_page(browser, creds, app_url=None):
    context = browser.new_context(permissions=["microphone", "camera", "notifications"])
    page = context.new_page()
    LoginPage(page).login(creds["email"], creds["password"])
    if app_url:
        page.goto(app_url)
    return page


SCREENSHOT_DIR = Path(__file__).resolve().parent.parent / "screenshots"


def _screenshot_pages(pages_by_name):
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    for name, page in pages_by_name.items():
        try:
            page.screenshot(path=str(SCREENSHOT_DIR / f"failure_{name}.png"))
        except Exception:
            pass


def _end_leftover_calls(*pages):
    # A failed earlier run can leave a call up, which blocks the next incoming call.
    for page in pages:
        hangup = DialerPage(page).hangup_button
        while hangup.count() and hangup.first.is_visible():
            hangup.first.click()
            page.wait_for_timeout(1000)


def test_executive_assistant_pairing_and_call(browser, credentials, test_data):
    # One browser context per user, so no logout/login switching.
    admin_page = _logged_in_page(browser, credentials["admin_user"])
    lite_1_page = _logged_in_page(browser, credentials["lite_1_user"], test_data["app_url"])
    lite_2_page = _logged_in_page(browser, credentials["lite_2_user"], test_data["app_url"])
    pages = (admin_page, lite_1_page, lite_2_page)

    _end_leftover_calls(*pages)
    try:
        _run_flow(test_data, admin_page, lite_1_page, lite_2_page)
    except Exception:
        _screenshot_pages({"admin": admin_page, "lite_1": lite_1_page, "lite_2": lite_2_page})
        raise
    finally:
        _end_leftover_calls(*pages)


def _run_flow(test_data, admin_page, lite_1_page, lite_2_page):
    executive, assistant = test_data["executive"], test_data["assistant"]
    app_url = test_data["app_url"]

    admin = AdminSettingsPage(admin_page)
    admin.open()
    admin.remove_existing_pairing()
    admin.add_pairing(executive, assistant)

    # Lite 2 sees lite 1's tabs before the permissions are granted.
    assistant_app = AssistantAppPage(lite_2_page, app_url)
    tabs_before = assistant_app.tab_count(executive, expect_tabs=False)

    admin.enable_permissions()

    # The 3 permissions must add tabs under lite 1 for lite 2.
    assert assistant_app.tab_count(executive) > tabs_before

    # Admin calls lite 1; lite 2 gets the notification and answers on lite 1's behalf.
    admin_page.goto(app_url)
    admin_dialer = DialerPage(admin_page)
    admin_dialer.call_from_conversation(executive)

    lite_2_dialer = DialerPage(lite_2_page)
    lite_2_dialer.expect_notification(test_data["assistant_notification_text"])
    lite_2_dialer.answer()

    # Lite 2 accepts the call, then transfers to lite 1, who answers.
    lite_2_dialer.accept()
    lite_2_dialer.transfer_to(executive)

    lite_1_dialer = DialerPage(lite_1_page)
    # The transferred call rings as a plain incoming call (caller name + 応答/拒否).
    expect(lite_1_dialer.answer_button).to_be_visible(timeout=30000)
    lite_1_dialer.answer()
    expect(lite_1_dialer.hangup_button).to_be_visible()

    lite_1_dialer.hang_up()

