"""Per-test flow records with screenshots, written out as an HTML report."""

from __future__ import annotations

import datetime
import html
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import screen

LOG = logging.getLogger(__name__)


@dataclass
class Step:
    elapsed: float
    caption: str
    image: str | None = None  # relative to the report directory
    error: str | None = None
    torn: bool = False  # the screen changed during the capture


@dataclass
class TestRecord:
    nodeid: str
    slug: str
    #: what the test does, from its docstring
    doc: str = ""
    started: float = field(default_factory=time.monotonic)
    steps: list[Step] = field(default_factory=list)
    outcome: str = "unknown"
    duration: float = 0.0
    failure: str = ""
    log: str = ""


def _slug(nodeid: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", nodeid.split("::", 1)[-1]).strip("_")


class Recorder:
    """Collects steps for the running test; writes the report at the end."""

    def __init__(self, root: Path, screenshots: bool, title: str, context: dict):
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.dir = root / stamp
        self.screenshots = screenshots
        self.title = title
        self.context = context
        self.records: list[TestRecord] = []
        self.current: TestRecord | None = None

    def start(self, nodeid: str, doc: str = "") -> None:
        self.current = TestRecord(nodeid, _slug(nodeid), " ".join(doc.split()))
        self.records.append(self.current)

    def step(self, caption: str, screenshot: bool = True) -> None:
        rec = self.current
        if rec is None:
            return
        n = len(rec.steps) + 1
        step = Step(time.monotonic() - rec.started, caption)
        LOG.info("step %d: %s", n, caption)
        if not screenshot:
            step.error = "no screenshot (host-side, or the device is rebooting)"
        elif self.screenshots:
            rel = f"{rec.slug}/{n:02d}.png"
            try:
                step.torn = not screen.capture(self.dir / rel)
                step.image = rel
            except Exception as e:  # a missing picture never fails a test
                step.error = str(e)
                LOG.warning("screenshot for step %d failed: %s", n, e)
        rec.steps.append(step)

    def finish(self, outcome: str, duration: float, failure: str, log: str) -> None:
        if self.current is not None:
            self.current.outcome = outcome
            self.current.duration = duration
            self.current.failure = failure
            self.current.log = log
        self.current = None

    # --- HTML -------------------------------------------------------------

    def write(self) -> Path | None:
        if not self.records:
            return None
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.dir / "index.html"
        path.write_text(self._html())
        return path

    def _html(self) -> str:
        e = html.escape
        counts: dict[str, int] = {}
        for r in self.records:
            counts[r.outcome] = counts.get(r.outcome, 0) + 1
        summary = " · ".join(f"{n} {o}" for o, n in sorted(counts.items()))
        ctx = "".join(
            f"<tr><th>{e(k)}</th><td><code>{e(str(v))}</code></td></tr>"
            for k, v in self.context.items()
        )
        rows = "".join(
            f'<tr class="{e(r.outcome)}"><td><a href="#{e(r.slug)}" title="{e(r.doc)}">'
            f"{e(r.nodeid)}</a></td>"
            f"<td>{e(r.outcome)}</td><td>{r.duration:.0f} s</td><td>{len(r.steps)}</td></tr>"
            for r in self.records
        )
        sections = "".join(self._section(r) for r in self.records)
        return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{e(self.title)}</title>
<style>
:root {{ --bg:#f7f8fa; --fg:#10151c; --dim:#5b6676; --rule:#d7dde5;
  --pass:#3d7350; --fail:#a1373a; --skip:#9a6410; --card:#fff; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0e1218; --fg:#dfe5ec;
  --dim:#9aa5b4; --rule:#2a333f; --card:#151b23; --pass:#78b98d;
  --fail:#e08589; --skip:#d9a441; }} }}
body {{ background:var(--bg); color:var(--fg); margin:0;
  font:14px/1.5 system-ui, sans-serif; }}
main {{ max-width:1200px; margin:0 auto; padding:24px 16px 64px; }}
h1 {{ font-size:24px; margin:0 0 4px; }} h2 {{ font-size:17px; margin:0; }}
table {{ border-collapse:collapse; width:100%; margin:12px 0; }}
th, td {{ text-align:left; padding:5px 8px; border-bottom:1px solid var(--rule);
  vertical-align:top; }}
code {{ font:12px ui-monospace, monospace; }}
tr.passed td:nth-child(2) {{ color:var(--pass); }}
tr.failed td:nth-child(2) {{ color:var(--fail); font-weight:600; }}
tr.skipped td:nth-child(2) {{ color:var(--skip); }}
section {{ background:var(--card); border:1px solid var(--rule);
  border-left:4px solid var(--rule); padding:14px 16px; margin:18px 0; }}
section.passed {{ border-left-color:var(--pass); }}
section.failed {{ border-left-color:var(--fail); }}
section.skipped {{ border-left-color:var(--skip); }}
.meta {{ color:var(--dim); margin:2px 0 10px; }}
.doc {{ margin:6px 0 4px; max-width:75ch; }}
.steps {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(200px,1fr));
  gap:12px; }}
figure {{ margin:0; }} figure img {{ width:100%; max-width:190px;
  border:1px solid var(--rule); display:block; }}
figcaption {{ font-size:12.5px; margin-top:4px; }}
figcaption b {{ color:var(--dim); font-weight:500; }}
figcaption i {{ color:var(--skip); font-style:normal; }}
figure.torn img {{ border:1px dashed var(--skip); }}
.noimg {{ width:190px; height:60px; border:1px dashed var(--rule);
  color:var(--dim); font-size:11px; padding:6px; overflow:hidden; }}
pre {{ background:var(--bg); padding:10px; overflow-x:auto; font-size:12px;
  white-space:pre-wrap; }}
details summary {{ cursor:pointer; color:var(--dim); margin-top:10px; }}
</style></head><body><main>
<h1>{e(self.title)}</h1><p class="meta">{e(summary)}</p>
<table>{ctx}</table>
<table><tr><th>test</th><th>outcome</th><th>time</th><th>steps</th></tr>{rows}</table>
{sections}
</main></body></html>
"""

    def _section(self, r: TestRecord) -> str:
        e = html.escape
        figs = []
        for i, s in enumerate(r.steps, 1):
            if s.image:
                pic = f'<a href="{e(s.image)}"><img src="{e(s.image)}" alt=""></a>'
            else:
                pic = f'<div class="noimg">{e(s.error or "no screenshot")}</div>'
            torn = "<br><i>screen changing: may mix two frames</i>" if s.torn else ""
            figs.append(
                f'<figure class="{"torn" if s.torn else ""}">{pic}'
                f"<figcaption><b>{i} · {s.elapsed:.0f} s</b><br>"
                f"{e(s.caption)}{torn}</figcaption></figure>"
            )
        failure = f"<pre>{e(r.failure)}</pre>" if r.failure else ""
        log = (
            f"<details><summary>log</summary><pre>{e(r.log)}</pre></details>"
            if r.log
            else ""
        )
        return (
            f'<section id="{e(r.slug)}" class="{e(r.outcome)}">'
            f"<h2>{e(r.nodeid)}</h2>"
            + (f'<p class="doc">{e(r.doc)}</p>' if r.doc else "")
            + f'<p class="meta">{e(r.outcome)} · {r.duration:.0f} s</p>'
            f'<div class="steps">{"".join(figs)}</div>{failure}{log}</section>'
        )
