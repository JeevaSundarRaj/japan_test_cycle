from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, expect


class AdminSettingsPage:
    def __init__(self, page: Page):
        self.page = page
        self.admin_link = page.get_by_role("link", name="管理者設定")
        self.delete_pairing = page.locator("#assistant-forwarding-admin").get_by_role("button", name="削除")
        self.setup_pairing = page.get_by_role("button", name="ペアリングを設定")
        self.executive_input = page.get_by_placeholder("エグゼクティブを選択")
        self.assistant_input = page.get_by_placeholder("アシスタントを選択")
        self.add_button = page.get_by_role("button", name="追加")
        self.checkboxes = page.get_by_role("checkbox")
        self.save_button = page.get_by_role("button", name="保存", exact=True)

    def open(self) -> None:
        self.admin_link.click()

    def remove_existing_pairing(self) -> None:
        self.setup_pairing.wait_for()
        delete = self.delete_pairing
        confirm = self.page.get_by_role("dialog").get_by_role("button", name="削除")
        # Existing pairings render after the page shell; give them a moment before concluding there are none.
        try:
            delete.first.wait_for(timeout=5000)
        except PlaywrightTimeoutError:
            return
        while delete.count():
            remaining = delete.count()
            delete.first.click()
            try:
                confirm.first.click(timeout=2000)
            except PlaywrightTimeoutError:
                pass
            expect(delete).to_have_count(remaining - 1)

    def add_pairing(self, executive: str, assistant: str) -> None:
        self.setup_pairing.click()
        self.executive_input.fill(executive)
        self.page.get_by_title(executive, exact=False).first.click()
        self.assistant_input.fill(assistant)
        self.page.get_by_title(assistant, exact=False).first.click()
        self.add_button.click()

    def enable_permissions(self, permission_indexes=(3, 4, 5)) -> None:
        for i in permission_indexes:
            self.checkboxes.nth(i).check()
        self.save_button.click()
