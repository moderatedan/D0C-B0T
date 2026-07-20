# Deploying D0C-B0T

The intended deployment is **your own machine** — that's the privacy model.
"Deployment" here mostly means publishing the repo, plus a couple of
self-hosting patterns.

## Push to GitHub

```bash
git init
git add .
git commit -m "v2: PHQ-9/GAD-7 published scoring, web UI, reports, history, privacy controls"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/D0C-B0T.git
git push -u origin main
```

Verify nothing personal is staged first:

```bash
git status --ignored | grep data/    # data/ must be ignored
```

Repo settings worth doing:
- **Topics:** `mental-health`, `phq-9`, `gad-7`, `screening`, `flask`,
  `self-hosted`, `privacy`
- **About:** "Self-hosted PHQ-9/GAD-7 screening companion. Published scoring,
  printable reports, local-only data. Not a diagnostic tool."
- Keep the "not a diagnostic tool" phrase in the About line — it sets the
  right expectation before anyone even opens the README.

## Run locally (the normal case)

```bash
pip install -r requirements.txt
python3 app.py                # http://127.0.0.1:5000, localhost only
```

## Home-network access (e.g., from your phone)

```bash
python3 app.py --host 0.0.0.0 --port 5000
```

Only on a network you trust. For anything beyond that, put a TLS reverse
proxy in front (Caddy makes this two lines):

```
your.hostname.example {
    reverse_proxy 127.0.0.1:5000
}
```

## Production-ish serving

Flask's built-in server is fine for one household. If you want a proper
WSGI server:

```bash
pip install gunicorn
gunicorn -w 2 -b 127.0.0.1:5000 app:app
```

## Do NOT deploy this as a public website casually

Hosting a mental-health screener for the general public brings real
responsibilities: accessibility, up-to-date crisis resources for every
region you serve, data-protection law (GDPR/HIPAA-adjacent questions), and
uptime someone in a bad moment might depend on. This codebase is built and
worded for personal/household self-hosting. If you want to serve others,
involve a clinician and review the crisis-resource list for your audience's
countries first.

## Post-publish checklist

- [ ] Replace `YOUR_USERNAME` in README.md, `YOUR_NAME` in LICENSE
- [ ] Run `python3 test_app.py` — all 9 tests must pass
- [ ] Take the four screenshots referenced in README (`docs/`)
- [ ] Verify the crisis banner: submit a PHQ-9 with question 9 = "Several
      days" and confirm the 988 banner appears above the score
- [ ] Tag a release: `git tag v2.0.0 && git push --tags`
