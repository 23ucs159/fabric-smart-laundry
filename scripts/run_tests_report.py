"""Run the test suite and write docs/TEST_RESULTS.md with the ACTUAL results (never hand-edited)."""
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = OrderedDict([
    ("Authentication", ["test_auth"]), ("Security (CSRF, authorization, XSS, file validation, encryption)", ["test_security"]),
    ("Database", ["test_database"]), ("ETL", ["test_etl"]), ("ML", ["test_ml"]), ("Recommendation", ["test_recommendation"]),
    ("RAG / assistant (incl. prompt injection)", ["test_rag"]), ("API flow / analytics / settings / seed", ["test_api_flow"]),
    ("Frontend smoke", ["test_frontend_smoke"]), ("Browser end-to-end (Playwright)", ["e2e"]),
])


def main():
    xml = ROOT / ".junit.xml"
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rs", f"--junitxml={xml}", "--cov=app", "--cov=ml",
                           "--cov-report=term"], cwd=ROOT, capture_output=True, text=True)
    out = proc.stdout
    cov = re.search(r"^TOTAL\s+\d+\s+\d+\s+(\d+)%", out, re.M)
    skips = re.findall(r"^SKIPPED \[\d+\] (.+)$", out, re.M)
    counts = OrderedDict((g, {"passed": 0, "failed": 0, "skipped": 0}) for g in GROUPS)
    for tc in ET.parse(xml).getroot().iter("testcase"):
        cls = tc.get("classname", "")
        state = "failed" if tc.find("failure") is not None or tc.find("error") is not None else \
                "skipped" if tc.find("skipped") is not None else "passed"
        for g, keys in GROUPS.items():
            if any(k in cls for k in keys):
                counts[g][state] += 1
                break
    tot = {k: sum(c[k] for c in counts.values()) for k in ("passed", "failed", "skipped")}
    summary = out.strip().splitlines()[-1] if out.strip() else ""
    lines = ["# Test results", "",
             "These numbers are produced by `python -m scripts.run_tests_report`, which runs pytest and writes this file. "
             "Nothing here is typed by hand.", "",
             f"- Run at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
             f"- Python {platform.python_version()} on {platform.system()}",
             f"- pytest summary line: `{summary}`",
             f"- Line coverage of `app/` and `ml/`: {cov.group(1) + '%' if cov else 'not measured'}", "",
             "| Area | Passed | Failed | Skipped |", "|---|---:|---:|---:|"]
    for g, c in counts.items():
        lines.append(f"| {g} | {c['passed']} | {c['failed']} | {c['skipped']} |")
    lines.append(f"| **Total** | **{tot['passed']}** | **{tot['failed']}** | **{tot['skipped']}** |")
    lines += ["", "## Skipped tests and limitations", ""]
    lines += [f"- {s}" for s in skips] or ["- None"]
    lines += ["",
              "The Playwright browser test (`tests/e2e/`) was **not executed** in the development environment used to produce this report: "
              "browser binaries could not be downloaded there. It is included and documented; run it locally as described in "
              "`tests/e2e/test_e2e_playwright.py`. Frontend behaviour is covered here only by the server-rendered smoke tests "
              "(page rendering, asset serving, element-id consistency between JavaScript and templates, no inline scripts/`innerHTML`). "
              "JavaScript was checked with `node --check` and, ad hoc during development, by rendering every page against real API data in a simulated browser (jsdom); that check is not part of this automated suite.", ""]
    if proc.returncode != 0:
        lines += ["## Failures", "", "```", out[-3000:], "```"]
    (ROOT / "docs" / "TEST_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    xml.unlink(missing_ok=True)
    print("\n".join(lines[:20]))
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
