# 🩺 D0C-B0T

> A self-hosted, privacy-first companion for the PHQ-9 and GAD-7 mental health **screening** questionnaires — with the published scoring rules, printable reports, score history, and crisis resources built in.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![Tests](https://img.shields.io/badge/tests-9%20passing-brightgreen.svg)
![Privacy](https://img.shields.io/badge/data-stays%20on%20your%20machine-orange.svg)

> **D0C-B0T is a screening companion, not a doctor.** The PHQ-9 and GAD-7 are validated screening instruments used by clinicians worldwide, but a score is not a diagnosis — high or low. This app computes standard scores, maps them to the published severity bands, and points you toward a conversation with a qualified professional. **If you are in crisis, call or text 988 (US) or your local emergency number.**

---

## ✨ Features

- **Proper clinical scoring** — full PHQ-9 (0–27) and GAD-7 (0–21) with the exact published item wording, 0–3 response scale, severity bands (minimal / mild / moderate / [moderately severe] / severe), and the standard functional-impairment follow-up question. Every band boundary is covered by unit tests.
- **Safety-first by design** — if PHQ-9 item 9 (thoughts of self-harm) is endorsed at *any* level, crisis resources (988 Lifeline, Crisis Text Line, findahelpline.com) are shown prominently **before** the score, regardless of the total. Non-diagnostic language throughout: results describe severity ranges and the published guidance, never "you have X."
- **Clean web interface** — calm, accessible, keyboard-navigable forms; automatic dark mode; works entirely offline (no CDN fonts or scripts).
- **Reporting** — an item-by-item breakdown, a printable/PDF report styled for handing to a clinician, and CSV export of your history.
- **Score history with trends** — opt-in only. Sparkline trends per instrument, because clinicians track these scores over time (a drop of ≥5 points is generally considered meaningful improvement).
- **Real privacy controls**
  - Nothing is stored unless you explicitly click **Save to history**.
  - By default only totals/severity are saved — **never per-item answers** (flip `STORE_ITEM_RESPONSES = True` for clinician-supervised use).
  - All data lives in `data/results.json` on your machine; one-click **Delete all history**.
  - Binds to `127.0.0.1` by default; no accounts, cookies, analytics, or third-party requests; `Cache-Control: no-store` on every response.

## 📸 Screenshots

> _Add your screenshots here:_

| Home | Questionnaire | Result with report | History trends |
|---|---|---|---|
| ![Home](docs/screenshot-home.png) | ![PHQ-9](docs/screenshot-phq9.png) | ![Result](docs/screenshot-result.png) | ![History](docs/screenshot-history.png) |

## 🚀 Installation

```bash
git clone https://github.com/YOUR_USERNAME/D0C-B0T.git
cd D0C-B0T
python3 -m venv .venv && source .venv/bin/activate   # optional but tidy
pip install -r requirements.txt                      # just Flask
python3 app.py
# → open http://127.0.0.1:5000
```

Run the test suite:

```bash
python3 test_app.py          # zero-dependency runner
# or: python3 -m pytest test_app.py
```

## 📖 Usage

1. Pick a screen — **PHQ-9** (depression) or **GAD-7** (anxiety). Each takes under two minutes.
2. Answer the questions about the **last two weeks**, plus the daily-impact question.
3. Review your result: total score, severity band, the published guidance for that band, and an item breakdown.
4. Optionally **Print / PDF report** to bring to an appointment, or **Save to history** to track trends over time.
5. Nothing was right for you? Click "Done — don't save" and nothing is retained.

### The scoring, exactly

| PHQ-9 total | Severity | GAD-7 total | Severity |
|---|---|---|---|
| 0–4 | Minimal or none | 0–4 | Minimal or none |
| 5–9 | Mild | 5–9 | Mild |
| 10–14 | Moderate | 10–14 | Moderate |
| 15–19 | Moderately severe | 15–21 | Severe |
| 20–27 | Severe | | |

A score of **10+** on either instrument is the commonly used cut-point for a follow-up conversation with a clinician. PHQ-9 item 9 is treated as significant at any non-zero answer, independent of the total.

## 🔒 Privacy model

| | |
|---|---|
| Completing a questionnaire | stores **nothing** |
| Clicking "Save to history" | stores date, instrument, total, severity band, impact answer — locally |
| Per-item answers | **not stored** by default (`STORE_ITEM_RESPONSES = False`) |
| Network | zero outbound requests; localhost-only by default |
| Deletion | one click on the History page, or delete `data/` |

If you bind beyond localhost (`--host 0.0.0.0`) to use it from your phone, do it only on a trusted network and understand that HTTP traffic on that network is unencrypted — put it behind HTTPS (see DEPLOYMENT.md).

## ⚕️ About the instruments

The PHQ-9 and GAD-7 were developed by Drs. Robert L. Spitzer, Janet B.W. Williams, Kurt Kroenke and colleagues. Both are in the public domain and may be reproduced without permission. They are among the most-validated brief screening measures in primary care worldwide — which is exactly why this app implements their wording and scoring verbatim rather than inventing its own questions.

## ⚠️ What this project will not do

- Diagnose, or imply a diagnosis
- Recommend medications or treatments
- Replace crisis services, therapy, or medical care
- Phone home with your answers

Issues/PRs that add these will be declined; PRs improving accessibility, translations (validated translations of both instruments exist in many languages), or additional *validated* public-domain screens are very welcome.

## 📄 License

[MIT](LICENSE) for the code. The PHQ-9 and GAD-7 instruments themselves are public domain.
