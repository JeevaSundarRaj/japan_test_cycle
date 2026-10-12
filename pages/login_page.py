from playwright.sync_api import Page


class LoginPage:
    URL = "https://www.dialpadbeta.com/"

    def __init__(self, page: Page):
        self.page = page
        self.login_link = page.get_by_role("link", name="Login")
        self.email = page.get_by_role("textbox", name="Work Email")
        self.password = page.get_by_role("textbox", name="Password")
        self.submit = page.get_by_role("button", name="Log in to Dialpad")

    def login(self, email: str, password: str) -> None:
        self.page.goto(self.URL)
        self.login_link.click()
        self.email.fill(email)
        self.password.fill(password)
        self.submit.click()
