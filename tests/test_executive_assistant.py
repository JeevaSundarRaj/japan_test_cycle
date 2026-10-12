import os

from pages.admin_settings_page import AdminSettingsPage
from pages.dialer_page import DialerPage
from pages.login_page import LoginPage

EXECUTIVE = "lite 1 JP"
ASSISTANT = "Lite 2 JP"


def test_executive_assistant_pairing_and_call(page, credentials):
    LoginPage(page).login(*credentials)

    admin = AdminSettingsPage(page)
    admin.open()
    admin.remove_existing_pairing()
    admin.pair(EXECUTIVE, ASSISTANT)

    dialer = DialerPage(page)
    dialer.call(os.environ.get("DIALPAD_CALL_NUMBER", "+81000000000"))
    dialer.expect_in_call()
    dialer.hang_up()
