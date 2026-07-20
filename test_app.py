#!/usr/bin/env python3
"""Tests for D0C-B0T scoring and routes.  Run:  python3 -m pytest test_app.py
(or without pytest:  python3 test_app.py)"""

import json

import app as doc


# --------------------------------------------------------------------------- #
# Scoring rules — verified against the published severity bands
# --------------------------------------------------------------------------- #

def test_phq9_bands():
    cases = [
        (0, "Minimal or none"), (4, "Minimal or none"),
        (5, "Mild"), (9, "Mild"),
        (10, "Moderate"), (14, "Moderate"),
        (15, "Moderately severe"), (19, "Moderately severe"),
        (20, "Severe"), (27, "Severe"),
    ]
    for total, expected in cases:
        answers = [3] * (total // 3) + ([total % 3] if total % 3 else [])
        answers += [0] * (9 - len(answers))
        r = doc.score("phq9", answers)
        assert r["total"] == total, (total, r["total"])
        assert r["severity"] == expected, (total, r["severity"], expected)


def test_gad7_bands():
    cases = [(0, "Minimal or none"), (4, "Minimal or none"),
             (5, "Mild"), (9, "Mild"),
             (10, "Moderate"), (14, "Moderate"),
             (15, "Severe"), (21, "Severe")]
    for total, expected in cases:
        answers = [3] * (total // 3) + ([total % 3] if total % 3 else [])
        answers += [0] * (7 - len(answers))
        r = doc.score("gad7", answers)
        assert r["total"] == total
        assert r["severity"] == expected, (total, r["severity"], expected)


def test_crisis_flag_any_endorsement():
    # Item 9 (index 8) endorsed at ANY level flags crisis, even with low total
    for level in (1, 2, 3):
        answers = [0] * 8 + [level]
        r = doc.score("phq9", answers)
        assert r["crisis_flag"] is True
        assert r["severity"] in ("Minimal or none", "Mild")
    r = doc.score("phq9", [3] * 8 + [0])
    assert r["crisis_flag"] is False  # high total but item 9 = 0


def test_invalid_answers_rejected():
    for bad in ([0] * 8, [0] * 10, [0] * 8 + [4], [0] * 8 + [-1],
                [0] * 8 + ["2"]):
        try:
            doc.score("phq9", bad)  # type: ignore[arg-type]
        except ValueError:
            continue
        raise AssertionError(f"accepted invalid answers: {bad}")


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

def _client(tmp_path=None):
    doc.app.config["TESTING"] = True
    return doc.app.test_client()


def test_pages_render():
    c = _client()
    for path in ("/", "/screen/phq9", "/screen/gad7", "/history", "/privacy"):
        resp = c.get(path)
        assert resp.status_code == 200, path
        assert b"screening companion, not a doctor" in resp.data, path
    assert c.get("/screen/nope").status_code == 404


def test_submit_and_crisis_banner():
    c = _client()
    form = {f"q{i}": "0" for i in range(9)}
    form["q8"] = "1"  # endorse self-harm item at lowest level
    resp = c.post("/screen/phq9", data=form)
    assert resp.status_code == 200
    assert b"988" in resp.data
    assert b"Please read this first" in resp.data

    form["q8"] = "0"
    resp = c.post("/screen/phq9", data=form)
    assert b"Please read this first" not in resp.data
    assert b"Minimal or none" in resp.data


def test_incomplete_submission_rejected():
    c = _client()
    resp = c.post("/screen/phq9", data={"q0": "1"})
    assert resp.status_code == 400
    assert b"answer every question" in resp.data


def test_save_and_history_and_privacy_default(tmp_path, monkeypatch=None):
    # Redirect storage into a temp dir
    doc.DATA_DIR = tmp_path
    doc.RESULTS_FILE = tmp_path / "results.json"
    c = _client()
    payload = json.dumps({"instrument": "gad7", "answers": [1] * 7})
    resp = c.post("/save", data={"payload": payload,
                                 "impairment": "Somewhat difficult"})
    assert resp.status_code == 302
    records = json.loads(doc.RESULTS_FILE.read_text())
    assert len(records) == 1
    assert records[0]["total"] == 7
    assert records[0]["severity"] == "Mild"
    # Privacy default: item answers NOT stored
    assert "answers" not in records[0]
    # CSV export works
    resp = c.get("/history.csv")
    assert b"GAD-7,7,21,Mild" in resp.data
    # Delete-all works
    c.post("/delete-all")
    assert not doc.RESULTS_FILE.exists()


def test_malformed_save_rejected():
    c = _client()
    assert c.post("/save", data={"payload": "not json"}).status_code == 400
    bad = json.dumps({"instrument": "phq9", "answers": [9] * 9})
    assert c.post("/save", data={"payload": bad}).status_code == 400


if __name__ == "__main__":
    import inspect
    import sys
    import tempfile
    from pathlib import Path

    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                params = inspect.signature(fn).parameters
                if "tmp_path" in params:
                    with tempfile.TemporaryDirectory() as td:
                        fn(Path(td))
                else:
                    fn()
                print(f"  PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"  FAIL  {name}: {e}")
    sys.exit(1 if failures else 0)
