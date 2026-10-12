from playwright.sync_api import Page, expect


class DialerPage:
    """TODO: selectors below are guesses; record the calling flow with codegen and adjust."""

    def __init__(self, page: Page):
        self.page = page
        self.number_input = page.get_by_placeholder("Enter a name or number")
        self.call_button = page.get_by_role("button", name="Call")
        self.hangup_button = page.get_by_role("button", name="End call")

    def call(self, number: str) -> None:
        self.number_input.fill(number)
        self.call_button.click()

    def expect_in_call(self) -> None:
        expect(self.hangup_button).to_be_visible()

    def hang_up(self) -> None:
        self.hangup_button.click()
