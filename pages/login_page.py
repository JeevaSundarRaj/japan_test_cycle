from playwright.sync_api import Page


class LoginPage:
    URL = "https://dialpadbeta.com/login"

    def __init__(self, page: Page):
        self.page = page
        self.email = page.get_by_role("textbox", name="Work Email")
        self.password = page.get_by_role("textbox", name="Password")
        self.submit = page.get_by_role("button", name="Log in to Dialpad")

    def login(self, email: str, password: str) -> None:
        self.page.goto(self.URL)
        self.email.fill(email)
        self.password.fill(password)
        self.submit.click()
        self.page.wait_for_url(lambda url: "/login" not in url, timeout=60000)
        self.page.wait_for_load_state("load")
