"""Turn report.xml (JUnit) into a PASS/FAIL table (markdown) for the job summary."""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "report.xml")
if not path.exists():
    print("## Test report\n\nNo report.xml produced (tests did not finish).")
    sys.exit(0)

rows = []
for tc in ET.parse(path).getroot().iter("testcase"):
    name = tc.get("name")
    time = float(tc.get("time") or 0)
    if tc.find("failure") is not None:
        status, note = "❌ FAILED", (tc.find("failure").get("message") or "")[:400]
    elif tc.find("error") is not None:
        status, note = "❌ ERROR", (tc.find("error").get("message") or "")[:400]
    elif tc.find("skipped") is not None:
        status, note = "⏭️ SKIPPED", (tc.find("skipped").get("message") or "")[:400]
    else:
        status, note = "✅ PASSED", ""
    rows.append((name, status, time, note.replace("|", "\\|").replace("\n", " ")))

passed = sum(1 for r in rows if "PASSED" in r[1])
print("## Test report\n")
print(f"**Total: {len(rows)} | Passed: {passed} | Failed: {len(rows) - passed}**\n")
print("| # | Test case | Result | Time (s) | Details |")
print("|---|-----------|--------|----------|---------|")
for i, (n, s, t, note) in enumerate(rows, 1):
    print(f"| {i} | {n} | {s} | {t:.0f} | {note} |")
