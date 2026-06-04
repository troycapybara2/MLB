"""
MLB Daily Digest — Email Script
Run this each morning (cron, GitHub Actions, Task Scheduler, etc.)

Setup:
  pip install requests
  Set env vars: MLB_EMAIL_TO, MLB_EMAIL_FROM, MLB_SMTP_HOST, MLB_SMTP_PORT, MLB_SMTP_USER, MLB_SMTP_PASS
  Or just hardcode them in the CONFIG block below.

GitHub Actions schedule example (.github/workflows/mlb_digest.yml):
  on:
    schedule:
      - cron: '0 11 * * *'   # 7am ET daily (UTC-4 in summer)
"""

import os
import smtplib
import requests
from datetime import date, timedelta
from collections import defaultdict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── CONFIG ────────────────────────────────────────────────────────────
EMAIL_TO   = os.environ.get("MLB_EMAIL_TO",   "you@email.com")
EMAIL_FROM = os.environ.get("MLB_EMAIL_FROM", "you@email.com")
SMTP_HOST  = os.environ.get("MLB_SMTP_HOST",  "smtp.gmail.com")
SMTP_PORT  = int(os.environ.get("MLB_SMTP_PORT", "587"))
SMTP_USER  = os.environ.get("MLB_SMTP_USER",  "you@gmail.com")
SMTP_PASS  = os.environ.get("MLB_SMTP_PASS",  "your_app_password")

PHI_ID = 143
NYY_ID = 147
BASE   = "https://statsapi.mlb.com/api/v1"
# ─────────────────────────────────────────────────────────────────────

def fetch(path):
    r = requests.get(f"{BASE}{path}", timeout=10)
    return r.json() if r.status_code == 200 else {}

def get_games(game_date):
    data = fetch(f"/schedule?sportId=1&date={game_date}&hydrate=linescore,decisions")
    games = []
    for day in data.get("dates", []):
        for g in day.get("games", []):
            if g.get("status", {}).get("abstractGameState") == "Final":
                games.append(g)
    return games

def get_boxscore(pk):
    return fetch(f"/game/{pk}/boxscore")

def get_leaders(stat, limit=10):
    data = fetch(f"/stats/leaders?leaderCategories={stat}&sportId=1&season=2025&limit={limit}")
    out = []
    for cat in data.get("leagueLeaders", []):
        for row in cat.get("leaders", []):
            out.append({
                "rank": row.get("rank"),
                "name": row.get("person", {}).get("fullName", ""),
                "team": row.get("team", {}).get("abbreviation", ""),
                "value": row.get("value"),
            })
    return out

def get_standings():
    data = fetch("/standings?leagueId=103,104&season=2025&standingsTypes=regularSeason")
    return data.get("records", [])

def extract_hr_rbi(games):
    hrs, rbis = defaultdict(lambda: {"n":"","t":"","c":0}), defaultdict(lambda: {"n":"","t":"","c":0})
    for g in games:
        box = get_boxscore(g["gamePk"])
        for side in ["home", "away"]:
            abbr = g["teams"][side]["team"].get("abbreviation","")
            players = box.get("teams",{}).get(side,{}).get("players",{})
            for pid in box.get("teams",{}).get(side,{}).get("batters",[]):
                p = players.get(f"ID{pid}",{})
                s = p.get("stats",{}).get("batting",{})
                nm = p.get("person",{}).get("fullName","")
                hr = s.get("homeRuns",0)
                rbi = s.get("rbi",0)
                if hr:
                    hrs[pid]["n"] = nm; hrs[pid]["t"] = abbr; hrs[pid]["c"] += hr
                if rbi:
                    rbis[pid]["n"] = nm; rbis[pid]["t"] = abbr; rbis[pid]["c"] += rbi
    return (sorted(hrs.values(), key=lambda x:-x["c"]),
            sorted(rbis.values(), key=lambda x:-x["c"]))

def extract_pitchers(games):
    pitchers = []
    for g in games:
        box = get_boxscore(g["gamePk"])
        for side, opp in [("away","home"),("home","away")]:
            pl = box.get("teams",{}).get(side,{}).get("pitchers",[])
            if not pl: continue
            pid = pl[0]
            p = box.get("teams",{}).get(side,{}).get("players",{}).get(f"ID{pid}",{})
            s = p.get("stats",{}).get("pitching",{})
            abbr = box.get("teams",{}).get(side,{}).get("team",{}).get("abbreviation","")
            opp_abbr = g["teams"][opp]["team"].get("abbreviation","")
            dec = ""
            decs = g.get("decisions",{})
            if pid == decs.get("winner",{}).get("id"): dec = "W"
            elif pid == decs.get("loser",{}).get("id"): dec = "L"
            pitchers.append({
                "name": p.get("person",{}).get("fullName",""),
                "team": abbr, "opp": opp_abbr,
                "ip": s.get("inningsPitched","0.0"),
                "k": s.get("strikeOuts",0),
                "er": s.get("earnedRuns",0),
                "h": s.get("hits",0),
                "bb": s.get("baseOnBalls",0),
                "dec": dec,
            })
    return sorted(pitchers, key=lambda x:-x["k"])

def build_html(yesterday, games, hrs, rbis, pitchers, standings,
               hr_lead, rbi_lead, ba_lead, k_lead):
    def game_row(g, highlight=False):
        home = g["teams"]["home"]
        away = g["teams"]["away"]
        hs, as_ = home.get("score",0), away.get("score",0)
        hn, an = home["team"]["name"], away["team"]["name"]
        inn = g.get("linescore",{}).get("currentInning",9)
        inn_str = f"F/{inn}" if inn != 9 else "Final"
        if hs > as_:
            return f"<tr{'  style=background:#1e1010' if highlight else ''}><td><b>{hn}</b> {hs} – {as_} {an}</td><td style='color:#888;font-size:11px'>{inn_str}</td></tr>"
        else:
            return f"<tr{'  style=background:#1e1010' if highlight else ''}><td><b>{an}</b> {as_} – {hs} {hn}</td><td style='color:#888;font-size:11px'>{inn_str}</td></tr>"

    def leaders_rows(items, val_key="value", suffix=""):
        rows = ""
        for r in items[:10]:
            medal = "🥇" if r["rank"]==1 else ("🥈" if r["rank"]==2 else ("🥉" if r["rank"]==3 else f"{r['rank']}."))
            rows += f"<tr><td>{medal}</td><td>{r['name']}</td><td style='color:#888;font-size:11px'>{r['team']}</td><td><b>{r[val_key]}{suffix}</b></td></tr>"
        return rows

    def stat_rows(items, c_key="c", suffix=""):
        rows = ""
        for i,p in enumerate(items[:10]):
            medal = "🥇" if i==0 else ("🥈" if i==1 else ("🥉" if i==2 else f"{i+1}."))
            rows += f"<tr><td>{medal}</td><td>{p['n']}</td><td style='color:#888;font-size:11px'>{p['t']}</td><td><b>{p[c_key]}{suffix}</b></td></tr>"
        return rows

    phi_games = [g for g in games if g["teams"]["home"]["team"]["id"]==PHI_ID or g["teams"]["away"]["team"]["id"]==PHI_ID]
    nyy_games = [g for g in games if g["teams"]["home"]["team"]["id"]==NYY_ID or g["teams"]["away"]["team"]["id"]==NYY_ID]

    phi_block = ""
    for g in phi_games:
        home, away = g["teams"]["home"], g["teams"]["away"]
        hs, as_ = home.get("score",0), away.get("score",0)
        hn, an = home["team"]["name"], away["team"]["name"]
        phi_block += f"<p style='margin:4px 0'><b>Phillies:</b> {'W' if (home['team']['id']==PHI_ID and hs>as_) or (away['team']['id']==PHI_ID and as_>hs) else 'L'} — {an} @ {hn}: {as_}–{hs}</p>"
    nyy_block = ""
    for g in nyy_games:
        home, away = g["teams"]["home"], g["teams"]["away"]
        hs, as_ = home.get("score",0), away.get("score",0)
        hn, an = home["team"]["name"], away["team"]["name"]
        nyy_block += f"<p style='margin:4px 0'><b>Yankees:</b> {'W' if (home['team']['id']==NYY_ID and hs>as_) or (away['team']['id']==NYY_ID and as_>hs) else 'L'} — {an} @ {hn}: {as_}–{hs}</p>"

    pitcher_rows = ""
    for p in pitchers[:15]:
        dec_str = f" ({p['dec']})" if p["dec"] else ""
        pitcher_rows += f"<tr><td>{p['name']}<span style='color:#888;font-size:11px'> {p['team']} vs {p['opp']}{dec_str}</span></td><td>{p['ip']} IP</td><td><b style='color:#c8102e'>{p['k']} K</b></td><td style='font-size:11px;color:#888'>{p['h']}H {p['er']}ER {p['bb']}BB</td></tr>"

    all_game_rows = "".join(
        game_row(g, highlight=(g["teams"]["home"]["team"]["id"] in (PHI_ID,NYY_ID) or
                                g["teams"]["away"]["team"]["id"] in (PHI_ID,NYY_ID)))
        for g in games
    )

    css = """
    body{font-family:'Helvetica Neue',Arial,sans-serif;background:#0f0f0f;color:#e8e0d0;margin:0;padding:0}
    .wrap{max-width:640px;margin:0 auto;padding:20px}
    h1{font-size:28px;font-weight:700;text-transform:uppercase;letter-spacing:3px;margin:0;color:#f0ebe0}
    h2{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:2px;color:#c8102e;border-bottom:1px solid #2a2a2a;padding-bottom:6px;margin:28px 0 12px}
    table{width:100%;border-collapse:collapse;font-size:13px}
    td{padding:6px 4px;border-bottom:1px solid #1e1e1e;vertical-align:top}
    .dateline{font-size:11px;color:#666;letter-spacing:2px;text-transform:uppercase;margin-top:4px}
    .alert{background:#1a1010;border-left:3px solid #c8102e;padding:10px 14px;margin-bottom:10px;font-size:13px}
    .alert-nyy{border-left-color:#003087;background:#0a0a1a}
    .footer{font-size:10px;color:#444;text-align:center;margin-top:32px;padding-top:12px;border-top:1px solid #1a1a1a}
    """

    html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css}</style></head><body>
    <div class='wrap'>
    <div style='border-bottom:3px solid #c8102e;padding-bottom:8px;margin-bottom:20px'>
        <div class='dateline'>⚾ MLB Daily Digest</div>
        <h1>{yesterday.strftime("%A, %B %-d, %Y")}</h1>
    </div>
    """

    if phi_block:
        html += f"<div class='alert'>{phi_block}</div>"
    if nyy_block:
        html += f"<div class='alert alert-nyy'>{nyy_block}</div>"

    html += f"<h2>Yesterday's Results</h2><table>{all_game_rows}</table>"
    html += f"<h2>Starting Pitchers (sorted by K)</h2><table>{pitcher_rows}</table>"

    html += f"""
    <table style='margin-top:20px'><tr style='vertical-align:top'>
    <td style='width:50%;padding-right:12px;border-bottom:none'>
        <h2 style='margin-top:0'>Yesterday's HRs</h2><table>{stat_rows(hrs)}</table>
    </td>
    <td style='width:50%;border-bottom:none'>
        <h2 style='margin-top:0'>Yesterday's RBIs</h2><table>{stat_rows(rbis)}</table>
    </td></tr></table>
    """

    html += f"""
    <table style='margin-top:20px'><tr style='vertical-align:top'>
    <td style='width:50%;padding-right:12px;border-bottom:none'>
        <h2 style='margin-top:0'>Season HR Leaders</h2><table>{leaders_rows(hr_lead)}</table>
    </td>
    <td style='width:50%;border-bottom:none'>
        <h2 style='margin-top:0'>Season RBI Leaders</h2><table>{leaders_rows(rbi_lead)}</table>
    </td></tr></table>
    <table style='margin-top:20px'><tr style='vertical-align:top'>
    <td style='width:50%;padding-right:12px;border-bottom:none'>
        <h2 style='margin-top:0'>Season BA Leaders</h2><table>{leaders_rows(ba_lead)}</table>
    </td>
    <td style='width:50%;border-bottom:none'>
        <h2 style='margin-top:0'>Season K Leaders</h2><table>{leaders_rows(k_lead, suffix=' K')}</table>
    </td></tr></table>
    """

    html += f"<div class='footer'>MLB Stats API · Generated {date.today().strftime('%B %-d, %Y').upper()} · PHI + NYY tracked</div>"
    html += "</div></body></html>"
    return html

def send_email(subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(html_body, "html"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo()
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

def main():
    yesterday = date.today() - timedelta(days=1)
    date_str  = yesterday.strftime("%Y-%m-%d")
    print(f"Pulling data for {date_str}...")

    games     = get_games(date_str)
    if not games:
        print("No games found. Exiting.")
        return

    hrs, rbis = extract_hr_rbi(games)
    pitchers  = extract_pitchers(games)
    standings = get_standings()
    hr_lead   = get_leaders("homeRuns")
    rbi_lead  = get_leaders("rbi")
    ba_lead   = get_leaders("battingAverage")
    k_lead    = get_leaders("strikeouts")

    html = build_html(yesterday, games, hrs, rbis, pitchers, standings,
                      hr_lead, rbi_lead, ba_lead, k_lead)

    subject = f"⚾ MLB Digest — {yesterday.strftime('%a %b %-d')}"
    send_email(subject, html)
    print(f"Email sent to {EMAIL_TO}")

if __name__ == "__main__":
    main()
