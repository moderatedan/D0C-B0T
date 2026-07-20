#!/usr/bin/env python3
"""
D0C-B0T — a self-hosted mental health *screening* companion.

Implements the PHQ-9 (depression) and GAD-7 (anxiety) screening instruments
with their published scoring rules, a calm web interface, printable reports,
optional score history, and privacy-first defaults.

IMPORTANT: PHQ-9 and GAD-7 are validated *screening* tools, not diagnostic
instruments. This application never diagnoses anyone. It computes standard
scores, maps them to the published severity bands, and encourages users to
discuss results with a qualified clinician. If item 9 of the PHQ-9 (thoughts
of self-harm) is endorsed at any level, crisis resources are shown
prominently regardless of the total score.

Both instruments were developed by Drs. Robert L. Spitzer, Janet B.W.
Williams, Kurt Kroenke and colleagues. They are in the public domain and may
be reproduced without permission.

Privacy model
-------------
* Nothing is stored unless the user explicitly clicks "Save to history".
* By default only scores are stored — never item-level answers
  (set STORE_ITEM_RESPONSES = True to change that, e.g. for clinician use).
* All data lives in ./data/results.json on the machine running the app.
* The app binds to 127.0.0.1 by default; no analytics, no third-party
  requests, no persistent cookies.
* One-click "Delete all history".

Run:  python3 app.py            → http://127.0.0.1:5000
License: MIT
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import secrets
import uuid
from datetime import datetime
from pathlib import Path

from flask import (Flask, Response, abort, redirect, render_template_string,
                   request, url_for)

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_FILE = DATA_DIR / "results.json"

# Privacy switches (see README → Privacy model)
STORE_ITEM_RESPONSES = False   # if True, saved records include per-item answers
DEFAULT_HOST = "127.0.0.1"     # localhost only unless you deliberately change it

DATE_FMT = "%Y-%m-%d %H:%M"

# --------------------------------------------------------------------------- #
# Instrument definitions — published wording and scoring rules
# --------------------------------------------------------------------------- #

ANSWER_OPTIONS = [
    (0, "Not at all"),
    (1, "Several days"),
    (2, "More than half the days"),
    (3, "Nearly every day"),
]

IMPAIRMENT_OPTIONS = [
    "Not difficult at all",
    "Somewhat difficult",
    "Very difficult",
    "Extremely difficult",
]

INSTRUMENTS = {
    "phq9": {
        "name": "PHQ-9",
        "long_name": "Patient Health Questionnaire-9",
        "stem": ("Over the last 2 weeks, how often have you been bothered "
                 "by any of the following problems?"),
        "questions": [
            "Little interest or pleasure in doing things",
            "Feeling down, depressed, or hopeless",
            "Trouble falling or staying asleep, or sleeping too much",
            "Feeling tired or having little energy",
            "Poor appetite or overeating",
            ("Feeling bad about yourself — or that you are a failure or have "
             "let yourself or your family down"),
            ("Trouble concentrating on things, such as reading the newspaper "
             "or watching television"),
            ("Moving or speaking so slowly that other people could have "
             "noticed? Or the opposite — being so fidgety or restless that "
             "you have been moving around a lot more than usual"),
            ("Thoughts that you would be better off dead or of hurting "
             "yourself in some way"),
        ],
        "max_score": 27,
        # (lower bound, upper bound, severity label) — published bands
        "bands": [
            (0, 4, "Minimal or none"),
            (5, 9, "Mild"),
            (10, 14, "Moderate"),
            (15, 19, "Moderately severe"),
            (20, 27, "Severe"),
        ],
        # Screening-language guidance aligned with the published
        # "proposed treatment actions" — deliberately non-diagnostic.
        "guidance": {
            "Minimal or none": (
                "Your responses suggest minimal depression symptoms over the "
                "past two weeks. The screen itself doesn't indicate any "
                "specific action — keep doing what supports you, and "
                "re-screen any time."),
            "Mild": (
                "Your responses fall in the mild range. The published "
                "guidance for this band suggests watchful waiting and "
                "repeating the screen in a few weeks. If symptoms persist or "
                "get in the way of daily life, it's worth mentioning them to "
                "a healthcare professional."),
            "Moderate": (
                "Your responses fall in the moderate range. A score of 10 or "
                "above is the commonly used cut-point at which the published "
                "guidance suggests a conversation with a doctor, therapist, "
                "or counselor, who can do a proper clinical assessment."),
            "Moderately severe": (
                "Your responses fall in the moderately severe range. The "
                "published guidance for this band recommends evaluation by a "
                "healthcare professional. Reaching out soon is a strong, "
                "practical next step — this report is designed to make that "
                "conversation easier."),
            "Severe": (
                "Your responses fall in the severe range. The published "
                "guidance for this band recommends prompt evaluation by a "
                "healthcare professional. Please consider contacting one "
                "soon — you deserve support, and effective help exists."),
        },
        "crisis_item_index": 8,  # zero-based index of the self-harm item
    },
    "gad7": {
        "name": "GAD-7",
        "long_name": "Generalized Anxiety Disorder-7",
        "stem": ("Over the last 2 weeks, how often have you been bothered "
                 "by the following problems?"),
        "questions": [
            "Feeling nervous, anxious, or on edge",
            "Not being able to stop or control worrying",
            "Worrying too much about different things",
            "Trouble relaxing",
            "Being so restless that it is hard to sit still",
            "Becoming easily annoyed or irritable",
            "Feeling afraid, as if something awful might happen",
        ],
        "max_score": 21,
        "bands": [
            (0, 4, "Minimal or none"),
            (5, 9, "Mild"),
            (10, 14, "Moderate"),
            (15, 21, "Severe"),
        ],
        "guidance": {
            "Minimal or none": (
                "Your responses suggest minimal anxiety symptoms over the "
                "past two weeks. Re-screen any time."),
            "Mild": (
                "Your responses fall in the mild range. Consider re-screening "
                "in a few weeks; if symptoms persist or interfere with daily "
                "life, mention them to a healthcare professional."),
            "Moderate": (
                "Your responses fall in the moderate range — a score of 10 or "
                "above is the commonly used cut-point for a follow-up "
                "conversation with a clinician, who can assess properly."),
            "Severe": (
                "Your responses fall in the severe range. The published "
                "guidance recommends evaluation by a healthcare professional. "
                "Reaching out soon is a strong next step."),
        },
        "crisis_item_index": None,
    },
}

# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #


def score(instrument_id: str, answers: list[int]) -> dict:
    """Score a completed instrument per the published rules.

    Returns total, severity band, guidance text, and (PHQ-9) whether the
    self-harm item was endorsed at any level.
    """
    inst = INSTRUMENTS[instrument_id]
    if len(answers) != len(inst["questions"]):
        raise ValueError("answer count does not match question count")
    if any(not isinstance(a, int) or a not in (0, 1, 2, 3) for a in answers):
        raise ValueError("answers must be integers 0-3")

    total = sum(answers)
    severity = next(label for lo, hi, label in inst["bands"]
                    if lo <= total <= hi)

    idx = inst["crisis_item_index"]
    crisis_flag = bool(idx is not None and answers[idx] > 0)

    return {
        "instrument": instrument_id,
        "name": inst["name"],
        "total": total,
        "max_score": inst["max_score"],
        "severity": severity,
        "guidance": inst["guidance"][severity],
        "crisis_flag": crisis_flag,
        "answers": answers,
    }


# --------------------------------------------------------------------------- #
# Storage (opt-in history)
# --------------------------------------------------------------------------- #


def load_results() -> list[dict]:
    if RESULTS_FILE.exists():
        with RESULTS_FILE.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    return []


def save_result(result: dict, impairment: str | None) -> str:
    DATA_DIR.mkdir(exist_ok=True)
    records = load_results()
    record = {
        "id": uuid.uuid4().hex[:12],
        "ts": datetime.now().strftime(DATE_FMT),
        "instrument": result["instrument"],
        "name": result["name"],
        "total": result["total"],
        "max_score": result["max_score"],
        "severity": result["severity"],
        "crisis_flag": result["crisis_flag"],
        "impairment": impairment,
    }
    if STORE_ITEM_RESPONSES:
        record["answers"] = result["answers"]
    records.append(record)
    with RESULTS_FILE.open("w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2)
    return record["id"]


def delete_all_results() -> None:
    if RESULTS_FILE.exists():
        RESULTS_FILE.unlink()


# --------------------------------------------------------------------------- #
# Templates (embedded so the whole app is a single reviewable file)
# --------------------------------------------------------------------------- #

BASE_TOP = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{title} · D0C-B0T</title>
<style>
  :root {{
    --bg: #f6f7f9; --card: #ffffff; --line: #dde2ea;
    --text: #23303f; --dim: #64748b;
    --accent: #2f6f6a; --accent-soft: #e3efee;
    --warn-bg: #fdf2f2; --warn-line: #e5484d; --warn-text: #7f1d1d;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #12181f; --card: #1a222c; --line: #2c3743;
      --text: #e6ebf1; --dim: #93a1b3;
      --accent: #57b3ab; --accent-soft: #1e3230;
      --warn-bg: #2c1a1c; --warn-line: #e5484d; --warn-text: #f5c2c4;
    }}
  }}
  * {{ box-sizing: border-box; margin: 0; }}
  body {{
    font: 16px/1.65 "Segoe UI", system-ui, -apple-system, sans-serif;
    background: var(--bg); color: var(--text);
    max-width: 720px; margin: 0 auto; padding: 24px 16px 64px;
  }}
  header {{ display: flex; justify-content: space-between; align-items: baseline;
           margin-bottom: 20px; flex-wrap: wrap; gap: 8px; }}
  header a {{ color: var(--text); text-decoration: none; font-weight: 700; }}
  header nav a {{ color: var(--dim); font-weight: 400; margin-left: 16px;
                 font-size: .9rem; }}
  header nav a:hover {{ color: var(--accent); }}
  .disclaimer {{
    font-size: .8rem; color: var(--dim); border: 1px solid var(--line);
    border-radius: 10px; padding: 10px 14px; margin-bottom: 22px;
    background: var(--card);
  }}
  .card {{
    background: var(--card); border: 1px solid var(--line);
    border-radius: 14px; padding: 26px; margin-bottom: 18px;
  }}
  h1 {{ font-size: 1.35rem; margin-bottom: 6px; }}
  h2 {{ font-size: 1.05rem; margin: 18px 0 8px; }}
  p.sub {{ color: var(--dim); font-size: .9rem; margin-bottom: 14px; }}
  a.button, button.button {{
    display: inline-block; background: var(--accent); color: #fff;
    border: none; border-radius: 9px; padding: 11px 20px;
    font: inherit; font-weight: 600; cursor: pointer; text-decoration: none;
  }}
  a.button.secondary, button.button.secondary {{
    background: none; color: var(--accent); border: 1px solid var(--accent);
  }}
  .crisis {{
    background: var(--warn-bg); border: 1.5px solid var(--warn-line);
    border-radius: 14px; padding: 20px 24px; margin-bottom: 18px;
    color: var(--warn-text);
  }}
  .crisis h2 {{ margin-top: 0; color: var(--warn-text); }}
  .crisis p {{ margin-bottom: 8px; font-size: .95rem; }}
  fieldset {{ border: none; border-top: 1px solid var(--line);
             padding: 18px 0; }}
  legend {{ font-weight: 600; padding-right: 10px; font-size: .97rem;
           float: left; margin-bottom: 10px; }}
  .opts {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
          margin-top: 12px; clear: both; }}
  @media (max-width: 560px) {{ .opts {{ grid-template-columns: 1fr 1fr; }} }}
  .opts label {{
    border: 1px solid var(--line); border-radius: 9px; padding: 9px 8px;
    font-size: .8rem; text-align: center; cursor: pointer; display: block;
    position: relative;
  }}
  .opts input {{ position: absolute; opacity: 0; }}
  .opts label:has(input:checked) {{
    border-color: var(--accent); background: var(--accent-soft);
    font-weight: 700;
  }}
  .opts label:focus-within {{ outline: 2px solid var(--accent); }}
  .score-hero {{ text-align: center; padding: 10px 0 4px; }}
  .score-hero .num {{ font-size: 3rem; font-weight: 700; }}
  .score-hero .band {{ font-size: 1.05rem; color: var(--accent);
                      font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
  th, td {{ text-align: left; padding: 9px 10px;
           border-bottom: 1px solid var(--line); }}
  th {{ color: var(--dim); font-weight: 600; font-size: .78rem;
       text-transform: uppercase; letter-spacing: .04em; }}
  .meter {{ height: 10px; border-radius: 5px; background: var(--line);
           overflow: hidden; margin: 14px auto 6px; max-width: 420px; }}
  .meter i {{ display: block; height: 100%; background: var(--accent); }}
  .actions {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px;
             align-items: center; }}
  footer {{ margin-top: 34px; font-size: .75rem; color: var(--dim);
           text-align: center; line-height: 1.8; }}
  @media print {{
    header nav, .actions, .disclaimer, footer {{ display: none; }}
    body {{ background: #fff; color: #000; }}
    .card {{ border: 1px solid #999; }}
  }}
</style>
</head>
<body>
<header>
  <a href="/">D0C-B0T</a>
  <nav>
    <a href="/screen/phq9">PHQ-9</a>
    <a href="/screen/gad7">GAD-7</a>
    <a href="/history">History</a>
    <a href="/privacy">Privacy</a>
  </nav>
</header>
<div class="disclaimer">
  D0C-B0T is a <b>screening companion, not a doctor</b>. It cannot diagnose
  any condition, and a score — high or low — is not a verdict on you. Results
  are a starting point for a conversation with a qualified healthcare
  professional. If you are in crisis, call or text <b>988</b> (US) or your
  local emergency number.
</div>
"""

BASE_BOTTOM = """
<footer>
  PHQ-9 &amp; GAD-7 developed by Drs. Spitzer, Kroenke, Williams and
  colleagues · public-domain instruments<br>
  D0C-B0T is MIT-licensed and self-hosted — your answers never leave this
  machine.
</footer>
</body>
</html>"""


def page(title: str, body_template: str, **ctx) -> str:
    """Render an embedded template inside the shared chrome."""
    body = render_template_string(body_template, **ctx)
    return BASE_TOP.format(title=title) + body + BASE_BOTTOM


INDEX_BODY = """
<div class="card">
  <h1>Check in with yourself</h1>
  <p class="sub">Two short, well-validated questionnaires used by clinicians
  worldwide. Each takes under two minutes. Nothing is saved unless you choose
  to save it.</p>

  <h2>PHQ-9 — depression screen</h2>
  <p class="sub">9 questions about the last two weeks, scored against the
  published severity bands (minimal → severe).</p>
  <a class="button" href="/screen/phq9">Start PHQ-9</a>

  <h2>GAD-7 — anxiety screen</h2>
  <p class="sub">7 questions about worry and restlessness over the last two
  weeks.</p>
  <a class="button" href="/screen/gad7">Start GAD-7</a>
</div>
<div class="card">
  <h2 style="margin-top:0">What this is — and isn't</h2>
  <p class="sub" style="margin-bottom:0">
    These questionnaires are <b>screening tools</b>: they estimate symptom
    severity so you and a clinician have somewhere to start. They are not a
    diagnosis, and a low score doesn't invalidate how you feel. If something
    is weighing on you, talking to a professional is worthwhile at any score.
  </p>
</div>
"""

SCREEN_BODY = """
<div class="card">
  <h1>{{ inst.name }} <span style="font-weight:400;color:var(--dim)">·
      {{ inst.long_name }}</span></h1>
  <p class="sub">{{ inst.stem }}</p>
  {% if error %}<p style="color:var(--warn-line);font-weight:600">
    {{ error }}</p>{% endif %}
  <form method="post" action="/screen/{{ inst_id }}">
    {% for q in inst.questions %}
    {% set qi = loop.index0 %}
    <fieldset>
      <legend>{{ loop.index }}. {{ q }}</legend>
      <div class="opts">
        {% for value, label in answer_options %}
        <label>
          <input type="radio" name="q{{ qi }}" value="{{ value }}" required
                 {% if prev and prev.get('q' ~ qi) == value|string %}checked{% endif %}>
          <span>{{ label }}</span>
        </label>
        {% endfor %}
      </div>
    </fieldset>
    {% endfor %}
    <fieldset>
      <legend>If you checked off <i>any</i> problems, how difficult have they
      made it for you to do your work, take care of things at home, or get
      along with other people?</legend>
      <div class="opts">
        {% for label in impairment_options %}
        <label><input type="radio" name="impairment" value="{{ label }}"
          {% if prev and prev.get('impairment') == label %}checked{% endif %}>
        <span>{{ label }}</span></label>
        {% endfor %}
      </div>
    </fieldset>
    <div class="actions">
      <button class="button" type="submit">See my score</button>
      <a class="button secondary" href="/">Cancel</a>
    </div>
  </form>
</div>
"""

RESULTS_BODY = """
{% if result.crisis_flag %}
<div class="crisis">
  <h2>Please read this first</h2>
  <p>You indicated having thoughts of self-harm or of being better off dead.
  Whatever the rest of your score says, that answer matters on its own — and
  support is available right now:</p>
  <p><b>988 Suicide &amp; Crisis Lifeline</b> — call or text <b>988</b>
  (US), 24/7.</p>
  <p><b>Crisis Text Line</b> — text <b>HOME</b> to <b>741741</b>
  (US/CA/UK).</p>
  <p><b>Outside the US</b> — findahelpline.com lists free helplines by
  country.</p>
  <p>If you are in immediate danger, call your local emergency number.
  Telling one trusted person how you're feeling is also a real, concrete
  step.</p>
</div>
{% endif %}

<div class="card">
  <h1>{{ result.name }} result</h1>
  <div class="score-hero">
    <div class="num">{{ result.total }}<span
      style="font-size:1.2rem;color:var(--dim)"> /
      {{ result.max_score }}</span></div>
    <div class="band">{{ result.severity }}</div>
    <div class="meter" aria-hidden="true">
      <i style="width: {{ (100 * result.total / result.max_score)
        | round | int }}%"></i>
    </div>
  </div>
  <p>{{ result.guidance }}</p>
  {% if impairment %}
  <p class="sub">Reported impact on daily life: <b>{{ impairment }}</b></p>
  {% endif %}

  <h2>Item breakdown</h2>
  <table>
    <tr><th>Question</th><th style="text-align:right">Score</th></tr>
    {% for q in questions %}
    <tr><td>{{ loop.index }}. {{ q }}</td>
        <td style="text-align:right">{{ result.answers[loop.index0] }}</td>
    </tr>
    {% endfor %}
  </table>

  <form method="post" action="/save" class="actions">
    <input type="hidden" name="payload" value='{{ payload }}'>
    <input type="hidden" name="impairment" value="{{ impairment or '' }}">
    <button class="button" type="submit">Save to history</button>
    <a class="button secondary" href="javascript:window.print()">Print / PDF
    report</a>
    <a class="button secondary" href="/">Done — don't save</a>
  </form>
  <p class="sub" style="margin-top:12px">Saving stores
  {% if store_items %}your scores <b>and</b> per-item answers{% else %}only
  your total score, severity band, date, and daily-impact answer — never your
  per-item answers{% endif %} — in a local file on this machine that you can
  delete at any time.</p>
</div>
"""

HISTORY_BODY = """
<div class="card">
  <h1>Score history</h1>
  <p class="sub">Saved locally in <code>data/results.json</code>. Trends
  matter more than single scores — clinicians track PHQ-9/GAD-7 over time,
  and a drop of 5 or more points is generally considered a meaningful
  improvement.</p>

  {% if not records %}
    <p class="sub">Nothing saved yet. Results are only stored when you click
    "Save to history" on a result page.</p>
  {% else %}
    {% for inst_id, points in sparks.items() %}
      {% if points|length >= 2 %}
      <h2>{{ instruments[inst_id].name }} trend</h2>
      <svg viewBox="0 0 300 60" width="100%" height="60"
           preserveAspectRatio="none" role="img"
           aria-label="{{ instruments[inst_id].name }} score trend">
        <polyline fill="none" stroke="var(--accent)" stroke-width="2"
          points="{% for x, y in points %}{{ x }},{{ y }} {% endfor %}"/>
      </svg>
      {% endif %}
    {% endfor %}
    <table>
      <tr><th>Date</th><th>Screen</th><th>Score</th><th>Severity</th>
          <th>Impact</th></tr>
      {% for r in records | reverse %}
      <tr>
        <td>{{ r.ts }}</td>
        <td>{{ r.name }}</td>
        <td>{{ r.total }} / {{ r.max_score }}</td>
        <td>{{ r.severity }}</td>
        <td>{{ r.impairment or "—" }}</td>
      </tr>
      {% endfor %}
    </table>
    <div class="actions">
      <a class="button secondary" href="/history.csv">Export CSV</a>
      <form method="post" action="/delete-all"
            onsubmit="return confirm('Delete ALL saved results? This cannot be undone.')">
        <button class="button secondary"
                style="border-color:var(--warn-line);color:var(--warn-line)"
                type="submit">Delete all history</button>
      </form>
    </div>
  {% endif %}
</div>
"""

PRIVACY_BODY = """
<div class="card">
  <h1>Privacy model</h1>
  <p class="sub">Short version: this app is self-hosted, offline-friendly,
  and forgetful by default.</p>
  <h2>What is collected</h2>
  <p>Nothing, unless you click <b>Save to history</b>. Completing a
  questionnaire and viewing your score stores nothing anywhere.</p>
  <h2>What saving stores</h2>
  <p>Date, instrument, total score, severity band, and your answer to the
  daily-impact question — written to <code>data/results.json</code> on the
  machine running this app.
  {% if store_items %}This deployment is configured to also store per-item
  answers (<code>STORE_ITEM_RESPONSES = True</code>).{% else %}Per-item
  answers (including the self-harm item) are <b>not</b> stored.{% endif %}</p>
  <h2>What never happens</h2>
  <p>No accounts, no analytics, no third-party requests, no fonts or scripts
  loaded from CDNs, no network transmission of answers, and responses are
  sent with <code>Cache-Control: no-store</code>. The app binds to localhost
  by default.</p>
  <h2>Your controls</h2>
  <p><b>Delete all history</b> on the History page removes the data file
  entirely. You can also simply delete the <code>data/</code> folder.</p>
</div>
"""

# --------------------------------------------------------------------------- #
# Flask app
# --------------------------------------------------------------------------- #

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)


@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/")
def index():
    return page("Home", INDEX_BODY)


@app.route("/screen/<instrument_id>", methods=["GET", "POST"])
def screen(instrument_id):
    inst = INSTRUMENTS.get(instrument_id)
    if not inst:
        abort(404)

    if request.method == "POST":
        try:
            answers = [int(request.form[f"q{i}"])
                       for i in range(len(inst["questions"]))]
            result = score(instrument_id, answers)
        except (KeyError, ValueError):
            return page(inst["name"], SCREEN_BODY, inst=inst,
                        inst_id=instrument_id, answer_options=ANSWER_OPTIONS,
                        impairment_options=IMPAIRMENT_OPTIONS,
                        error="Please answer every question.",
                        prev=request.form), 400

        impairment = request.form.get("impairment") or None
        payload = json.dumps({"instrument": instrument_id,
                              "answers": answers})
        return page(f"{inst['name']} result", RESULTS_BODY, result=result,
                    impairment=impairment, questions=inst["questions"],
                    payload=payload, store_items=STORE_ITEM_RESPONSES)

    return page(inst["name"], SCREEN_BODY, inst=inst, inst_id=instrument_id,
                answer_options=ANSWER_OPTIONS,
                impairment_options=IMPAIRMENT_OPTIONS, error=None, prev=None)


@app.route("/save", methods=["POST"])
def save():
    try:
        payload = json.loads(request.form["payload"])
        result = score(payload["instrument"], payload["answers"])
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        abort(400)
    save_result(result, request.form.get("impairment") or None)
    return redirect(url_for("history"))


@app.route("/history")
def history():
    records = load_results()
    # Sparkline coordinates per instrument, normalized to a 300x60 viewBox.
    sparks: dict[str, list] = {}
    for inst_id, inst in INSTRUMENTS.items():
        pts = [r for r in records if r["instrument"] == inst_id]
        if len(pts) >= 2:
            step = 300 / (len(pts) - 1)
            sparks[inst_id] = [
                (round(i * step, 1),
                 round(55 - (r["total"] / inst["max_score"]) * 50, 1))
                for i, r in enumerate(pts)
            ]
        else:
            sparks[inst_id] = []
    return page("History", HISTORY_BODY, records=records, sparks=sparks,
                instruments=INSTRUMENTS)


@app.route("/history.csv")
def history_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "instrument", "total", "max_score", "severity",
                "impairment"])
    for r in load_results():
        w.writerow([r["ts"], r["name"], r["total"], r["max_score"],
                    r["severity"], r.get("impairment") or ""])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":
                             "attachment; filename=doc-b0t-history.csv"})


@app.route("/delete-all", methods=["POST"])
def delete_all():
    delete_all_results()
    return redirect(url_for("history"))


@app.route("/privacy")
def privacy():
    return page("Privacy", PRIVACY_BODY, store_items=STORE_ITEM_RESPONSES)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main():
    p = argparse.ArgumentParser(description="D0C-B0T screening companion")
    p.add_argument("--host", default=DEFAULT_HOST,
                   help="bind address (default 127.0.0.1 — localhost only)")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--debug", action="store_true")
    args = p.parse_args()
    if args.host not in ("127.0.0.1", "localhost"):
        print("WARNING: binding beyond localhost. Only do this on a trusted "
              "network — screening answers are sensitive.")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
