from playwright.sync_api import Page


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
        if self.delete_pairing.count():
            self.delete_pairing.first.click()

    def pair(self, executive: str, assistant: str, permission_indexes=(3, 4, 5)) -> None:
        self.setup_pairing.click()
        self.executive_input.fill(executive)
        self.page.get_by_title(executive, exact=False).first.click()
        self.assistant_input.fill(assistant)
        self.page.get_by_title(assistant, exact=False).first.click()
        self.add_button.click()
        for i in permission_indexes:
            self.checkboxes.nth(i).check()
        self.save_button.click()
