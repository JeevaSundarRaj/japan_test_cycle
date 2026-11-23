import json
import subprocess
import wave
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from playwright.sync_api import expect

from pages.conversation_history_page import ConversationHistoryPage, wait_for_summary_and_transcript
from pages.dialer_page import DialerPage
from pages.login_page import LoginPage

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "audio"
SCREENSHOT_DIR = ROOT / "screenshots"
WINDOW_FILE = ROOT / ".call_window.json"
CALLS_MADE = 4


def _now_jst() -> datetime:
    """Conversation history shows JST regardless of the machine's timezone."""
    return datetime.now(ZoneInfo("Asia/Tokyo")).replace(tzinfo=None)


def _to_wav(mp3: Path, tmp_dir: Path) -> Path:
    """Chromium's fake mic only plays WAV; convert with afconvert (macOS) or ffmpeg."""
    wav = tmp_dir / (mp3.stem + ".wav")
    try:
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@48000", str(mp3), str(wav)], check=True)
    except FileNotFoundError:
        subprocess.run(["ffmpeg", "-y", "-i", str(mp3), "-ar", "48000", "-ac", "1", str(wav)], check=True)
    return wav


@pytest.fixture(scope="module")
def wavs(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("wav")
    return (
        _to_wav(AUDIO_DIR / "japanese_conversation_1_smartphone.mp3", tmp),
        _to_wav(AUDIO_DIR / "japanese_conversation_2_software.mp3", tmp),
    )


def _launch(browser_type, launch_args, wav: Path):
    """The fake mic file is browser-wide, so each speaker group gets its own browser."""
    args = list(launch_args.get("args", [])) + [
        "--use-fake-ui-for-media-stream",
        "--use-fake-device-for-media-stream",
        f"--use-file-for-fake-audio-capture={wav}",
    ]
    return browser_type.launch(**{**launch_args, "args": args})


def _logged_in_page(browser, creds, app_url):
    context = browser.new_context(permissions=["microphone", "camera", "notifications"])
    page = context.new_page()
    LoginPage(page).login(creds["email"], creds["password"])
    page.goto(app_url)
    return page


def _end_calls(*dialers):
    for d in dialers:
        while d.hangup_button.count() and d.hangup_button.first.is_visible():
            d.hangup_button.first.click()
            d.page.wait_for_timeout(1000)
        d.dismiss_wrap_up(timeout=2000)


def _duration(wav: Path) -> int:
    with wave.open(str(wav)) as w:
        return int(w.getnframes() / w.getframerate())


def _talk_and_check_transcript(support: DialerPage, other: DialerPage, support_secs: int, other_secs: int):
    expect(support.hangup_button).to_be_visible(timeout=30000)
    expect(other.hangup_button).to_be_visible(timeout=15000)
    # AI must be on at the support user's end and the audio must get transcribed.
    support.ensure_ai_on()
    # Take turns so the two recordings don't overlap; each side plays its whole recording
    # so the transcript is long enough for the AI to produce a summary.
    other.set_muted(True)
    support.set_muted(False)
    support.page.wait_for_timeout((support_secs + 2) * 1000)
    support.set_muted(True)
    other.set_muted(False)
    support.page.wait_for_timeout((other_secs + 2) * 1000)
    support.expect_transcribing()
    support.hang_up()
    expect(other.hangup_button).to_be_hidden(timeout=15000)
    # Post-call wrap-up modals would block the next call button click.
    support.dismiss_wrap_up()
    other.dismiss_wrap_up(timeout=2000)


def test_call_and_transcription(browser_type, browser_type_launch_args, credentials, test_data, wavs):
    app_url, cc = test_data["app_url"], test_data["cc_name"]
    default_persona = test_data["support_default_persona"]
    support_secs, other_secs = _duration(wavs[0]), _duration(wavs[1])

    support_browser = _launch(browser_type, browser_type_launch_args, wavs[0])
    lite_browser = _launch(browser_type, browser_type_launch_args, wavs[1])
    pages = {
        "support": _logged_in_page(support_browser, credentials["test_support_user"], app_url),
        "lite_1": _logged_in_page(lite_browser, credentials["lite_1_user"], app_url),
        "lite_2": _logged_in_page(lite_browser, credentials["lite_2_user"], app_url),
    }
    support, lite_1, lite_2 = (DialerPage(pages[k]) for k in ("support", "lite_1", "lite_2"))
    _end_calls(support, lite_1, lite_2)
    started = _now_jst()
    try:
        # Support user calls lite 1 and lite 2 with caller ID "test cc"
        for lite, name in ((lite_1, "Lite 1"), (lite_2, "Lite 2")):
            support.call(name, "callResultCallBtn", caller_id=cc)
            lite.expect_notification(cc, timeout=30000)
            lite.answer()
            _talk_and_check_transcript(support, lite, support_secs, other_secs)

        # Caller ID back to the support user's own persona
        support.restore_caller_id(default_persona)

        # Lite 1 and lite 2 call test cc; support user answers
        for lite in (lite_1, lite_2):
            lite.call(cc, "callResultCallBtn")
            support.expect_incoming_call_for(cc, timeout=30000)
            support.answer()
            _talk_and_check_transcript(support, lite, support_secs, other_secs)
    except Exception:
        SCREENSHOT_DIR.mkdir(exist_ok=True)
        for name, page in pages.items():
            try:
                page.screenshot(path=str(SCREENSHOT_DIR / f"failure_transcription_{name}.png"))
            except Exception:
                pass
        raise
    finally:
        WINDOW_FILE.write_text(json.dumps({"start": started.isoformat(), "end": _now_jst().isoformat()}))
        _end_calls(support, lite_1, lite_2)
        support_browser.close()
        lite_browser.close()


def test_call_summary_tabs_not_empty(browser, credentials, test_data):
    """Run after test_call_and_transcription: each of the 4 calls it made must have fully populated tabs."""
    window = json.loads(WINDOW_FILE.read_text())
    start = datetime.fromisoformat(window["start"]) - timedelta(seconds=30)
    end = datetime.fromisoformat(window["end"]) + timedelta(seconds=30)
    context = browser.new_context()
    page = context.new_page()
    try:
        LoginPage(page).login(credentials["admin_user"]["email"], credentials["admin_user"]["password"])
        history = ConversationHistoryPage(page)
        history.open(test_data["mainline_name"], test_data["cc_name"])
        summaries = history.open_summaries_between(start, end, CALLS_MADE)
        for n, summary in enumerate(summaries, 1):
            try:
                wait_for_summary_and_transcript(summary)
            except AssertionError as e:
                raise AssertionError(f"Call {n}: {e}") from None
    except Exception:
        SCREENSHOT_DIR.mkdir(exist_ok=True)
        page.screenshot(path=str(SCREENSHOT_DIR / "failure_call_summary.png"))
        raise
    finally:
        context.close()
