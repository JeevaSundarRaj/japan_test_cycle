from playwright.sync_api import Page, expect


class AccountsPage:
    def __init__(self, page: Page, accounts_url: str):
        self.page = page
        self.accounts_url = accounts_url
        self.search_input = page.get_by_placeholder("ユーザーを検索")
        self.rows = page.locator("tr")

    def open(self) -> None:
        self.page.goto(self.accounts_url)
        expect(self.search_input).to_be_visible(timeout=30000)

    def search(self, text: str) -> None:
        self.search_input.click()
        self.search_input.fill("")
        self.search_input.press_sequentially(text, delay=50)
        self.search_input.press("Enter")

    def expect_single_match(self, title: str, timeout: int = 15000) -> None:
        row = self.page.locator("//tbody[@id='accounts-list']//tr")
        expect(row).to_have_count(1, timeout=timeout)
        expect(row.locator(f"xpath=.//div[@title='{title}']")).to_have_count(1, timeout=timeout)
