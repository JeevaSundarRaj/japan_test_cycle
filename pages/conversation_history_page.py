import re
from datetime import datetime

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, expect

TABS = ("トランスクリプト", "抜粋", "品質", "要約")
EMPTY_TEXT = re.compile("AI要約はありません|データがありません|まだありません")


ROW_TIME = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*(午前|午後)(\d{1,2})時(\d{1,2})分(\d{1,2})秒")


def parse_row_time(text: str) -> datetime | None:
    m = ROW_TIME.search(text)
    if not m:
        return None
    y, mo, d, ampm, h, mi, sec = m.groups()
    hour = int(h) % 12 + (12 if ampm == "午後" else 0)
    return datetime(int(y), int(mo), int(d), hour, int(mi), int(sec))


class ConversationHistoryPage:
    def __init__(self, page: Page):
        self.page = page

    def open(self, *groups: str) -> None:
        """Admin settings > 会話履歴, filtered to the given offices/call centers."""
        self.page.get_by_role("link", name="管理者設定").click()  # shown on the post-login landing page, not /app
        self.page.get_by_role("link", name="会話履歴").click()
        self.page.get_by_role("button", name="オフィス | グループフィルター").click()
        for group in groups:
            self.page.get_by_role("checkbox", name=group).check()
        self.page.get_by_role("button", name="適用").click()

    def open_summaries_between(self, start: datetime, end: datetime, expected: int) -> list[Page]:
        """Open the summary popup of every call whose start time is within [start, end] (rows are newest first)."""
        links = self.page.get_by_role("link", name="通話サマリーを表示")
        expect(links.first).to_be_visible(timeout=30000)
        matches = []
        for i in range(links.count()):
            row = links.nth(i).locator("xpath=ancestor::*[self::tr or @role='row'][1]")
            when = parse_row_time(row.inner_text())
            if when and start <= when <= end:
                matches.append(i)
        assert len(matches) == expected, f"Expected {expected} calls between {start} and {end}, found {len(matches)}"
        summaries = []
        for i in matches:
            with self.page.expect_popup() as popup:
                links.nth(i).click()
            summaries.append(popup.value)
            popup.value.wait_for_load_state()
        return summaries


def tab_text(summary: Page, tab: str) -> str:
    summary.get_by_role("tab", name=tab).click()
    panel = summary.get_by_role("tabpanel", name=tab)
    expect(panel).to_be_visible(timeout=10000)
    return panel.inner_text().strip()


def tab_has_content(summary: Page, tab: str) -> bool:
    text = tab_text(summary, tab)
    return bool(text) and not EMPTY_TEXT.search(text)


def deep_summary_has_content(summary: Page) -> bool:
    """Summary tab: the 詳細サマリー (deep summary) button must exist and open non-empty content."""
    summary.get_by_role("tab", name="要約").click()
    button = summary.get_by_role("button", name="詳細サマリー")
    if not button.count() or not button.first.is_visible():
        return False
    button.first.click()
    panel = summary.get_by_role("tabpanel", name="要約")
    text = panel.inner_text().strip()
    return bool(text) and not EMPTY_TEXT.search(text)


def empty_summary_and_transcript(summary: Page) -> list[str]:
    """Names of the checks that fail: summary (+ deep summary) and transcript (no deep summary there)."""
    empty = []
    if not tab_has_content(summary, "要約"):
        empty.append("要約")
    if not deep_summary_has_content(summary):
        empty.append("要約 > 詳細サマリー")
    if not tab_has_content(summary, "トランスクリプト"):
        empty.append("トランスクリプト")
    return empty


def wait_for_summary_and_transcript(summary: Page, timeout: int = 300000, poll: int = 15000) -> None:
    """AI output is generated after the call ends; reload until summary and transcript have content."""
    waited = 0
    empty: list[str] = []
    while waited <= timeout:
        empty = empty_summary_and_transcript(summary)
        if not empty:
            return
        summary.wait_for_timeout(poll)
        summary.reload()
        waited += poll
    raise AssertionError(f"Still empty after {timeout // 1000}s: {empty}")


def wait_for_all_tabs_filled(summary: Page, timeout: int = 300000, poll: int = 15000) -> None:
    """AI output is generated after the call ends; reload until every tab has content."""
    waited = 0
    empty = list(TABS)
    while waited <= timeout:
        empty = [t for t in TABS if not tab_has_content(summary, t)]
        if not empty:
            return
        summary.wait_for_timeout(poll)
        summary.reload()
        waited += poll
    raise AssertionError(f"Call summary tabs still empty after {timeout // 1000}s: {empty}")
