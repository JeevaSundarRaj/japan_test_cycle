import pytest

from pages.accounts_page import AccountsPage
from pages.login_page import LoginPage

ACCOUNTS_URL = "https://dialpadbeta.com/accounts"
TEAM_MEMBER = "漢字 ひらがな"


@pytest.mark.parametrize("keyword", ["漢", "ひ"])
def test_search_team_member(browser, credentials, keyword):
    context = browser.new_context()
    page = context.new_page()
    try:
        creds = credentials["admin_user"]
        LoginPage(page).login(creds["email"], creds["password"])

        accounts = AccountsPage(page, ACCOUNTS_URL)
        accounts.open()
        accounts.search(keyword)
        accounts.expect_single_match(TEAM_MEMBER)
    finally:
        context.close()
