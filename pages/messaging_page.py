import json
import re
from pathlib import Path

from playwright.sync_api import Page, expect

LOCATORS = json.loads((Path(__file__).parent / "locators.json").read_text())


class MessagingPage:
    def __init__(self, page: Page, app_url: str):
        self.page = page
        self.app_url = app_url
        self.message_input = page.get_by_role("textbox", name="message-input").first
        self.image_button = page.locator(LOCATORS["messageImageButton"])
        self.send_button = page.locator(LOCATORS["messageSendButton"])
        self.mms_images = page.locator(LOCATORS["mmsImage"])

    def open_conversation(self, name: str) -> None:
        self.page.goto(self.app_url)
        self.page.locator(LOCATORS["sidebarLink"].format(name.lower())).first.click()
        expect(self.message_input).to_be_visible(timeout=15000)

    def search_and_open_contact(self, name: str) -> None:
        self.page.goto(self.app_url)
        self.page.get_by_text("検索 Dialpad").first.click()
        search_input = self.page.get_by_placeholder("連絡先、メッセージ、通話などを検索")
        expect(search_input).to_be_visible(timeout=15000)
        search_input.click()
        search_input.press_sequentially(name, delay=50)
        self.page.locator(LOCATORS["searchContactResult"].format(name.lower())).first.click()
        expect(self.message_input).to_be_visible(timeout=15000)

    def send_text(self, text: str) -> None:
        self.message_input.click()
        self.message_input.fill(text)
        self.send_button.click()

    def send_image(self, path: str) -> None:
        with self.page.expect_file_chooser() as chooser:
            self.image_button.click()
        chooser.value.set_files(path)
        self.send_button.click()

    def expect_text_received(self, text: str, timeout: int = 30000) -> None:
        expect(self.page.get_by_text(text).first).to_be_visible(timeout=timeout)

    def expect_image_received(self, previous_count: int = 0, timeout: int = 30000) -> None:
        self.page.wait_for_function(
            "([xpath, n]) => document.evaluate(`count(${xpath})`, document, null, XPathResult.NUMBER_TYPE, null).numberValue > n",
            arg=[LOCATORS["mmsImage"], previous_count],
            timeout=timeout,
        )

    def expect_last_message_time_in(self, allowed: list[str], timeout: int = 30000) -> None:
        """Latest message header time (HH:MM) must be one of `allowed`."""
        last_time = self.page.locator("time.dp-feed-item-row__header-time").last
        # The UI may drop the hour's leading zero (8:44 vs 08:44); accept both.
        hhmm = "|".join(re.escape(re.sub(r"^0", "", t)) for t in allowed)
        expect(last_time).to_have_text(re.compile(rf"^\s*0?({hhmm})\s*$"), timeout=timeout)
