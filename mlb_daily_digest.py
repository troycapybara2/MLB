import streamlit as st
import requests
from datetime import date, timedelta
from collections import defaultdict

# ── Constants ────────────────────────────────────────────────────────
BASE    = "https://statsapi.mlb.com/api/v1"
PHI_ID  = 143
NYY_ID  = 147
SEASON  = date.today().year

AL_DIVS = {200: "AL West", 201: "AL East", 202: "AL Central"}
NL_DIVS = {203: "NL West", 204: "NL East", 205: "NL Central"}
ALL_DIVS = {**AL_DIVS, **NL_DIVS}

DIV_ORDER = [201, 202, 200, 204, 205, 203]

# Team ID ↔ abbreviation lookups (MLB team IDs are stable)
TEAM_IDS = {
    "LAA": 108, "ARI": 109, "BAL": 110, "BOS": 111,
    "CHC": 112, "CIN": 113, "CLE": 114, "COL": 115,
    "DET": 116, "HOU": 117, "KC":  118, "LAD": 119,
    "WSH": 120, "NYM": 121, "OAK": 133, "ATH": 133,
    "PIT": 134, "SD":  135, "SEA": 136, "SF":  137,
    "STL": 138, "TB":  139, "TEX": 140, "TOR": 141,
    "MIN": 142, "PHI": 143, "ATL": 144, "CWS": 145,
    "MIA": 146, "NYY": 147, "MIL": 158,
}
TEAM_ABBRS = {v: k for k, v in TEAM_IDS.items()}  # id → abbr

def team_abbr(team_dict):
    """Get abbreviation from a team dict — falls back to ID lookup."""
    return (team_dict.get("abbreviation")
            or TEAM_ABBRS.get(team_dict.get("id"), "???"))

TEAM_COLORS = {
    "ARI": "#A71930", "ATL": "#CE1141", "BAL": "#DF4601", "BOS": "#BD3039",
    "CHC": "#0E3386", "CIN": "#C6011F", "CLE": "#E31937", "COL": "#333366",
    "CWS": "#27251F", "DET": "#0C2340", "HOU": "#002D62", "KC":  "#004687",
    "LAA": "#BA0021", "LAD": "#005A9C", "MIA": "#00A3E0", "MIL": "#12284B",
    "MIN": "#002B5C", "NYM": "#002D72", "NYY": "#003087", "OAK": "#003831",
    "ATH": "#003831", "PHI": "#E81828", "PIT": "#FDB827", "SD":  "#2F241D",
    "SEA": "#0C2C56", "SF":  "#FD5A1E", "STL": "#C41E3A", "TB":  "#092C5C",
    "TEX": "#003278", "TOR": "#134A8E", "WSH": "#AB0003",
}

def logo(abbr, sz=28):
    color = TEAM_COLORS.get(abbr, "#333355")
    font  = max(8, sz // 3)
    pad   = max(2, sz // 8)
    return (
        f"<span style='display:inline-flex;align-items:center;justify-content:center;"
        f"width:{sz}px;height:{sz}px;min-width:{sz}px;border-radius:4px;"
        f"background:{color};color:#ffffff;"
        f"font-family:\"Barlow Condensed\",sans-serif;font-size:{font}px;font-weight:700;"
        f"letter-spacing:0.02em;flex-shrink:0;vertical-align:middle'>{abbr}</span>"
    )

# ── Page Config ──────────────────────────────────────────────────────
st.set_page_config(page_title="Capy's MLB Roundup", page_icon="⚾", layout="wide")

# ── CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Reset & Base ── */
#MainMenu, header, footer, .stDeployButton { display:none !important; visibility:hidden !important; }
.stApp { background: #0e0e18 !important; }
.block-container { padding: 1.5rem 2.5rem 3rem !important; max-width: 1440px !important; }
* { box-sizing: border-box; }

body, p, span, div, td, th { font-family: 'DM Sans', sans-serif; }

/* ── App Header ── */
.roundup-header {
    text-align: center;
    padding: 0.6rem 0 1rem;
}
.roundup-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.8rem;
    font-weight: 800;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #eeeef5;
    line-height: 1;
}
.roundup-title .accent { color: #e81828; }
.roundup-date {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #7788bb;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-top: 0.3rem;
}
.roundup-rule {
    height: 2px;
    background: linear-gradient(90deg, transparent, #e81828 20%, #e81828 80%, transparent);
    border: none;
    margin: 0 0 1.6rem;
}

/* ── Section Headers ── */
.sec-head {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #7788bb;
    border-bottom: 1px solid #22223a;
    padding-bottom: 0.5rem;
    margin: 0 0 0.9rem;
}

/* ── Hero Team Cards ── */
.hero-card {
    background: #16162a;
    border: 1px solid #282840;
    border-radius: 10px;
    padding: 1.1rem 1.3rem;
    min-height: 110px;
    position: relative;
    overflow: hidden;
}
.hero-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}
.hero-card.phi::before { background: #e81828; }
.hero-card.nyy::before { background: #4d7bc4; }
.hero-card-label {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-bottom: 0.7rem;
}
.hero-card.phi .hero-card-label { color: #e81828; }
.hero-card.nyy .hero-card-label { color: #4d7bc4; }

.hero-matchup {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
}
.hero-team-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.hero-score {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    min-width: 1.8rem;
    text-align: right;
    margin-left: auto;
}
.hero-score.w { color: #eeeef5; }
.hero-score.l { color: #44445a; }
.hero-tname { font-size: 0.9rem; font-weight: 500; }
.hero-tname.w { color: #eeeef5; }
.hero-tname.l { color: #55556a; }
.hero-status {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #55556a;
    margin-top: 0.3rem;
    letter-spacing: 0.05em;
}
.hero-noplay {
    color: #55556a;
    font-size: 0.82rem;
    font-style: italic;
    padding: 0.5rem 0;
}

/* ── Standings Tables ── */
.std-wrap {
    background: #16162a;
    border: 1px solid #282840;
    border-radius: 8px;
    overflow: hidden;
}
.std-div-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #7788bb;
    background: #111125;
    padding: 0.45rem 0.9rem;
    border-bottom: 1px solid #22223a;
}
.std-tbl { width: 100%; border-collapse: collapse; }
.std-tbl th {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    font-weight: 500;
    letter-spacing: 0.1em;
    color: #55556a;
    text-transform: uppercase;
    text-align: right;
    padding: 0.35rem 0.7rem;
    border-bottom: 1px solid #22223a;
    background: #111125;
    white-space: nowrap;
}
.std-tbl th:first-child { text-align: left; padding-left: 0.9rem; }
.std-tbl td {
    padding: 0.45rem 0.7rem;
    border-bottom: 1px solid #111125;
    text-align: right;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #9090b8;
    white-space: nowrap;
}
.std-tbl td:first-child {
    text-align: left;
    padding-left: 0.9rem;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.83rem;
    color: #ccccd8;
}
.std-tbl tr:last-child td { border-bottom: none; }
.std-tbl .pct { color: #9999b0; font-weight: 500; }
.std-tbl .strk-w { color: #22c55e; }
.std-tbl .strk-l { color: #ef4444; }
.std-tbl tr.phi-row td { background: #18090a !important; }
.std-tbl tr.phi-row td:first-child { color: #eeeef5; }
.std-tbl tr.nyy-row td { background: #090910 !important; }
.std-tbl tr.nyy-row td:first-child { color: #eeeef5; }
.std-tbl tr.div-leader td:first-child { color: #eeeef5; font-weight: 500; }
.std-tbl .wc-tag {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    background: #0f1f10;
    color: #4ade80;
    border: 1px solid #1a3018;
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    vertical-align: middle;
    margin-left: 0.35rem;
}

/* ── Game Rows ── */
.games-wrap {
    background: #16162a;
    border: 1px solid #282840;
    border-radius: 8px;
    overflow: hidden;
}
.game-row {
    display: flex;
    align-items: center;
    padding: 0.55rem 1rem;
    border-bottom: 1px solid #111125;
    gap: 0.5rem;
}
.game-row:last-child { border-bottom: none; }
.game-row.phi-game { background: #200d10; border-left: 3px solid #e81828; }
.game-row.nyy-game { background: #0d0d22; border-left: 3px solid #4d7bc4; }
.game-side { display: flex; flex-direction: column; gap: 0.25rem; flex: 1; }
.game-team-line { display: flex; align-items: center; gap: 0.45rem; }
.game-team-name { font-size: 0.82rem; }
.game-team-name.w { color: #ccccd8; font-weight: 500; }
.game-team-name.l { color: #55556a; }
.game-sc {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.15rem;
    font-weight: 700;
    min-width: 1.5rem;
    text-align: right;
    margin-left: auto;
}
.game-sc.w { color: #eeeef5; }
.game-sc.l { color: #44445a; }
.game-info {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    color: #55556a;
    min-width: 60px;
    text-align: right;
    white-space: nowrap;
}
.game-divider {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #55556a;
    background: #111125;
    padding: 0.25rem 1rem;
    border-bottom: 1px solid #111125;
}

/* ── Stat Leaders ── */
.leaders-wrap {
    background: #16162a;
    border: 1px solid #282840;
    border-radius: 8px;
    overflow: hidden;
}
.leader-row {
    display: flex;
    align-items: center;
    padding: 0.55rem 0.9rem;
    border-bottom: 1px solid #111125;
    gap: 0.7rem;
}
.leader-row:last-child { border-bottom: none; }
.leader-rank {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #55556a;
    min-width: 1.2rem;
    text-align: center;
}
.leader-rank.gold { color: #f5a623; font-weight: 700; }
.leader-rank.silver { color: #9999b0; font-weight: 700; }
.leader-rank.bronze { color: #8b6914; font-weight: 700; }
.leader-name { font-size: 0.85rem; color: #ccccd8; font-weight: 500; flex: 1; }
.leader-team {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #7777aa;
}
.leader-val {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: #4f8ef7;
    min-width: 2.5rem;
    text-align: right;
}

/* ── Pitchers ── */
.pitcher-row {
    display: flex;
    align-items: center;
    padding: 0.55rem 0.9rem;
    border-bottom: 1px solid #111125;
    gap: 1rem;
}
.pitcher-row:last-child { border-bottom: none; }
.pitcher-left { flex: 1; }
.pitcher-name { font-size: 0.85rem; color: #ccccd8; font-weight: 500; }
.pitcher-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #888899;
    margin-top: 0.1rem;
}
.pitcher-k {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.5rem;
    font-weight: 800;
    color: #f5a623;
    min-width: 2.5rem;
    text-align: right;
}
.pitcher-k-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.55rem;
    color: #7777aa;
    text-align: right;
    letter-spacing: 0.1em;
}
.pitcher-line {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #7777aa;
    text-align: right;
    min-width: 120px;
}
.pitcher-dec {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    margin-left: 0.4rem;
    vertical-align: middle;
}
.pitcher-dec.W { background: #0f1f10; color: #4ade80; border: 1px solid #1a3018; }
.pitcher-dec.L { background: #1f0f0f; color: #ef4444; border: 1px solid #3a1818; }

/* ── Buttons ── */
.stButton > button {
    background: #16162a !important;
    border: 1px solid #282840 !important;
    color: #7788bb !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
    border-radius: 6px !important;
    padding: 0.4rem 1rem !important;
    transition: all 0.15s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    border-color: #4f8ef7 !important;
    color: #4f8ef7 !important;
}

/* ── Batting Insights ── */
.insight-row {
    display: flex;
    align-items: flex-start;
    gap: 0.7rem;
    padding: 0.7rem 0.9rem;
    border-bottom: 1px solid #111125;
}
.insight-row:last-child { border-bottom: none; }
.insight-tag {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    padding: 0.15rem 0.45rem;
    border-radius: 3px;
    white-space: nowrap;
    flex-shrink: 0;
    margin-top: 0.15rem;
    min-width: 52px;
    text-align: center;
}
.insight-text {
    font-size: 0.85rem;
    color: #a8a8cc;
    line-height: 1.55;
}
.insight-text b { color: #ddddf0; font-weight: 600; }

/* ── Tonight's Starters ── */
.tonight-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.65rem 0.9rem;
    border-bottom: 1px solid #111125;
    gap: 1rem;
}
.tonight-row:last-child { border-bottom: none; }
.tonight-left { flex: 1; min-width: 0; }
.tonight-name { font-size: 0.87rem; font-weight: 500; color: #ccccd8; }
.tonight-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.63rem;
    color: #7777aa;
    margin-top: 0.15rem;
    white-space: nowrap;
}
.tonight-stats { display: flex; gap: 1.2rem; align-items: center; }
.tonight-stat-block { text-align: right; min-width: 52px; }
.tonight-stat-val {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.4rem;
    font-weight: 800;
    color: #4f8ef7;
    line-height: 1;
}
.tonight-stat-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.55rem;
    color: #33333f;
    letter-spacing: 0.08em;
    margin-top: 0.1rem;
}
.k-bar-wrap {
    width: 52px;
    height: 2px;
    background: #1e1e2a;
    border-radius: 1px;
    margin-top: 0.3rem;
}
.k-bar {
    height: 100%;
    border-radius: 1px;
    transition: width 0.3s ease;
}

/* ── Misc ── */
.no-data {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #2a2a35;
    font-style: italic;
    padding: 1rem;
    text-align: center;
}
.gap { margin-top: 1.4rem; }
</style>
""", unsafe_allow_html=True)

# ── Session State ────────────────────────────────────────────────────
if "vd" not in st.session_state:
    st.session_state.vd = date.today() - timedelta(days=1)

# ── API Helpers ──────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_games(d):
    r = requests.get(
        f"{BASE}/schedule?sportId=1&date={d}&hydrate=linescore,decisions,team",
        timeout=10
    )
    if r.status_code != 200:
        return []
    out = []
    for day in r.json().get("dates", []):
        for g in day.get("games", []):
            if g.get("status", {}).get("abstractGameState") == "Final":
                out.append(g)
    return out

@st.cache_data(ttl=300)
def get_boxscore(pk):
    r = requests.get(f"{BASE}/game/{pk}/boxscore", timeout=10)
    return r.json() if r.status_code == 200 else {}

@st.cache_data(ttl=600)
def get_standings_data():
    r = requests.get(
        f"{BASE}/standings?leagueId=103,104&season={SEASON}&standingsTypes=regularSeason",
        timeout=10
    )
    return r.json().get("records", []) if r.status_code == 200 else []

def extract_hr_rbi(games_list):
    hrs  = defaultdict(lambda: {"n": "", "t": "", "abbr": "", "c": 0})
    rbis = defaultdict(lambda: {"n": "", "t": "", "abbr": "", "c": 0})
    for g in games_list:
        box = get_boxscore(g["gamePk"])
        for side in ("home", "away"):
            abbr = (g["teams"][side]["team"].get("abbreviation")
                    or TEAM_ABBRS.get(g["teams"][side]["team"].get("id"), ""))
            players = box.get("teams", {}).get(side, {}).get("players", {})
            for pid in box.get("teams", {}).get(side, {}).get("batters", []):
                p   = players.get(f"ID{pid}", {})
                s   = p.get("stats", {}).get("batting", {})
                nm  = p.get("person", {}).get("fullName", "")
                if s.get("homeRuns", 0):
                    hrs[pid]["n"] = nm; hrs[pid]["t"] = abbr; hrs[pid]["abbr"] = abbr; hrs[pid]["c"] += s["homeRuns"]
                if s.get("rbi", 0):
                    rbis[pid]["n"] = nm; rbis[pid]["t"] = abbr; rbis[pid]["abbr"] = abbr; rbis[pid]["c"] += s["rbi"]
    return (sorted(hrs.values(),  key=lambda x: -x["c"]),
            sorted(rbis.values(), key=lambda x: -x["c"]))

def extract_pitchers(games_list):
    out = []
    for g in games_list:
        box   = get_boxscore(g["gamePk"])
        decs  = g.get("decisions", {})
        win_id = decs.get("winner", {}).get("id")
        los_id = decs.get("loser",  {}).get("id")
        for side, opp in (("away", "home"), ("home", "away")):
            pl = box.get("teams", {}).get(side, {}).get("pitchers", [])
            if not pl:
                continue
            pid = pl[0]
            p   = box.get("teams", {}).get(side, {}).get("players", {}).get(f"ID{pid}", {})
            s   = p.get("stats", {}).get("pitching", {})
            abbr= box.get("teams", {}).get(side, {}).get("team", {}).get("abbreviation", "")
            opp_abbr = (g["teams"][opp]["team"].get("abbreviation")
                        or TEAM_ABBRS.get(g["teams"][opp]["team"].get("id"), ""))
            dec = "W" if pid == win_id else ("L" if pid == los_id else "")
            out.append({
                "name": p.get("person", {}).get("fullName", ""),
                "abbr": abbr, "opp": opp_abbr,
                "ip": s.get("inningsPitched", "0.0"),
                "k":  s.get("strikeOuts", 0),
                "er": s.get("earnedRuns", 0),
                "h":  s.get("hits", 0),
                "bb": s.get("baseOnBalls", 0),
                "dec": dec,
            })
    return sorted(out, key=lambda x: -x["k"])

@st.cache_data(ttl=1800)
def get_tonight_starters():
    today_str = date.today().strftime("%Y-%m-%d")
    r = requests.get(
        f"{BASE}/schedule?sportId=1&date={today_str}&hydrate=probablePitcher",
        timeout=10
    )
    if r.status_code != 200:
        return []
    out = []
    for day in r.json().get("dates", []):
        for g in day.get("games", []):
            game_time = g.get("gameDate", "")
            for side, opp in (("away", "home"), ("home", "away")):
                pp = g["teams"][side].get("probablePitcher")
                if not pp:
                    continue
                out.append({
                    "id":       pp["id"],
                    "name":     pp.get("fullName", ""),
                    "abbr":     (g["teams"][side]["team"].get("abbreviation")
                                 or TEAM_ABBRS.get(g["teams"][side]["team"].get("id"), "")),
                    "opp_abbr": (g["teams"][opp]["team"].get("abbreviation")
                                 or TEAM_ABBRS.get(g["teams"][opp]["team"].get("id"), "")),
                    "home":     side == "home",
                    "game_time": game_time,
                })
    return out

@st.cache_data(ttl=1800)
def get_pitcher_k_stats(person_id):
    """Returns season avg K/start and last-5-starts avg K."""
    # Season totals
    sr = requests.get(
        f"{BASE}/people/{person_id}/stats?stats=season&group=pitching&season={SEASON}",
        timeout=10
    )
    season_avg = None
    era, record, ip_str = "-.--", "-", "0.0"
    if sr.status_code == 200:
        splits = sr.json().get("stats", [{}])[0].get("splits", [])
        if splits:
            s  = splits[0].get("stat", {})
            gs = s.get("gamesStarted", 0)
            k  = s.get("strikeOuts", 0)
            era = s.get("era", "-.--")
            ip_str = s.get("inningsPitched", "0.0")
            w  = s.get("wins", 0)
            l  = s.get("losses", 0)
            record = f"{w}-{l}"
            season_avg = round(k / gs, 1) if gs > 0 else None

    # Game log → last 5 starts
    lr = requests.get(
        f"{BASE}/people/{person_id}/stats?stats=gameLog&group=pitching&season={SEASON}",
        timeout=10
    )
    last5_avg = None
    if lr.status_code == 200:
        splits = lr.json().get("stats", [{}])[0].get("splits", [])
        starts = [s for s in splits if s.get("stat", {}).get("gamesStarted", 0) > 0]
        last5  = starts[-5:]  # game log is chronological oldest→newest
        if last5:
            total_k = sum(s["stat"].get("strikeOuts", 0) for s in last5)
            last5_avg = round(total_k / len(last5), 1)

    return {"season_avg": season_avg, "last5_avg": last5_avg,
            "era": era, "record": record, "ip": ip_str}

# ── Batting Insight Engine ────────────────────────────────────────────

@st.cache_data(ttl=1800)
def get_leaders_with_ids(stat, limit=20):
    r = requests.get(
        f"{BASE}/stats/leaders?leaderCategories={stat}&sportId=1&season={SEASON}&limit={limit}",
        timeout=10
    )
    if r.status_code != 200:
        return []
    out = []
    for cat in r.json().get("leagueLeaders", []):
        for row in cat.get("leaders", []):
            out.append({
                "rank":    row.get("rank"),
                "id":      row.get("person", {}).get("id"),
                "name":    row.get("person", {}).get("fullName", ""),
                "team":    row.get("team", {}).get("abbreviation", ""),
                "team_id": row.get("team", {}).get("id"),
                "value":   row.get("value"),
            })
    return out

@st.cache_data(ttl=1800)
def get_player_gamelog_hitting(person_id):
    r = requests.get(
        f"{BASE}/people/{person_id}/stats?stats=gameLog&group=hitting&season={SEASON}",
        timeout=10
    )
    if r.status_code != 200:
        return []
    return r.json().get("stats", [{}])[0].get("splits", [])

@st.cache_data(ttl=1800)
def get_vs_team_stats(person_id, opp_id):
    r = requests.get(
        f"{BASE}/people/{person_id}/stats?stats=vsTeam&group=hitting&season={SEASON}"
        f"&opposingTeamId={opp_id}",
        timeout=10
    )
    if r.status_code != 200:
        return {}
    splits = r.json().get("stats", [{}])[0].get("splits", [])
    return splits[0].get("stat", {}) if splits else {}

@st.cache_data(ttl=1800)
def get_todays_schedule():
    r = requests.get(
        f"{BASE}/schedule?sportId=1&date={date.today().strftime('%Y-%m-%d')}",
        timeout=10
    )
    if r.status_code != 200:
        return []
    return [g for day in r.json().get("dates", []) for g in day.get("games", [])]

def _hitting_streak(splits):
    n = 0
    for s in reversed(splits):
        if s.get("stat", {}).get("hits", 0) > 0:
            n += 1
        else:
            break
    return n

def _last_n(splits, n=7):
    sl   = splits[-n:] if len(splits) >= n else splits
    hrs  = sum(s["stat"].get("homeRuns", 0) for s in sl)
    rbi  = sum(s["stat"].get("rbi", 0) for s in sl)
    hits = sum(s["stat"].get("hits", 0) for s in sl)
    ab   = sum(s["stat"].get("atBats", 0) for s in sl)
    return {"hrs": hrs, "rbi": rbi, "hits": hits, "ab": ab,
            "ba": round(hits / ab, 3) if ab else 0, "g": len(sl)}

@st.cache_data(ttl=1800)
def generate_batting_insights():
    raw = []

    # ── Pool top hitters ──────────────────────────────────────────────
    seen_ids = set()
    players  = []
    for stat in ("homeRuns", "rbi", "battingAverage"):
        for p in get_leaders_with_ids(stat, 20):
            if p["id"] and p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                players.append(p)

    # Build a quick lookup: team abbr → list of players on that team
    team_players = defaultdict(list)
    for p in players:
        if p["team"]:
            team_players[p["team"]].append(p)

    # ── Per-player insights ───────────────────────────────────────────
    for p in players[:30]:
        pid = p["id"]
        if not pid:
            continue
        splits = get_player_gamelog_hitting(pid)
        if not splits or len(splits) < 5:
            continue

        name   = p["name"]
        team   = p["team"]
        streak = _hitting_streak(splits)
        l7     = _last_n(splits, 7)
        l14    = _last_n(splits, 14)
        gp     = len(splits)
        entries = []

        # Hitting streak
        if streak >= 15:
            entries.append({"text": f"<b>{name}</b> ({team}) is riding a <b>{streak}-game hitting streak</b> — one of the longest active in the majors", "pri": streak + 90, "type": "STREAK", "color": "#f5a623", "bg": "#1e1505"})
        elif streak >= 10:
            entries.append({"text": f"<b>{name}</b> ({team}) has hit safely in <b>{streak} consecutive games</b>", "pri": streak + 50, "type": "STREAK", "color": "#f5a623", "bg": "#1e1505"})
        elif streak >= 7:
            entries.append({"text": f"<b>{name}</b> ({team}) has reached base via hit in <b>{streak} straight games</b>", "pri": streak + 20, "type": "STREAK", "color": "#f5a623", "bg": "#1e1505"})

        # HR burst (last 7)
        if l7["hrs"] >= 5:
            entries.append({"text": f"<b>{name}</b> ({team}) has been on a power surge — <b>{l7['hrs']} HRs in {l7['g']} games</b>", "pri": l7["hrs"] * 20, "type": "POWER", "color": "#ef4444", "bg": "#1f0808"})
        elif l7["hrs"] >= 3:
            entries.append({"text": f"<b>{name}</b> ({team}) has <b>{l7['hrs']} HRs</b> over the last {l7['g']} games", "pri": l7["hrs"] * 14, "type": "POWER", "color": "#ef4444", "bg": "#1f0808"})

        # HR burst (last 14 only if not already flagged last 7)
        if l14["hrs"] >= 8 and l7["hrs"] < 3:
            entries.append({"text": f"<b>{name}</b> ({team}) has <b>{l14['hrs']} HRs</b> over the last 14 games", "pri": l14["hrs"] * 7, "type": "POWER", "color": "#ef4444", "bg": "#1f0808"})

        # RBI burst
        if l7["rbi"] >= 11:
            entries.append({"text": f"<b>{name}</b> ({team}) has been a run-producing machine — <b>{l7['rbi']} RBIs</b> over the last {l7['g']} games", "pri": l7["rbi"] * 6, "type": "RBI", "color": "#22c55e", "bg": "#081a08"})
        elif l7["rbi"] >= 7:
            entries.append({"text": f"<b>{name}</b> ({team}) has driven in <b>{l7['rbi']} runs</b> over the last {l7['g']} games", "pri": l7["rbi"] * 4, "type": "RBI", "color": "#22c55e", "bg": "#081a08"})

        # Hot bat (meaningful AB sample)
        if l7["ab"] >= 22 and l7["ba"] >= 0.400:
            entries.append({"text": f"<b>{name}</b> ({team}) is locked in — <b>.{int(l7['ba']*1000):03d}</b> over the last {l7['g']} games ({l7['hits']}-for-{l7['ab']})", "pri": int(l7["ba"] * 560), "type": "HOT BAT", "color": "#4f8ef7", "bg": "#080f22"})
        elif l7["ab"] >= 15 and l7["ba"] >= 0.467:
            entries.append({"text": f"<b>{name}</b> ({team}) is scorching right now — <b>.{int(l7['ba']*1000):03d}</b> over the last {l7['g']} games", "pri": int(l7["ba"] * 650), "type": "HOT BAT", "color": "#4f8ef7", "bg": "#080f22"})

        # Season HR pace
        if p.get("value") and p in players and gp >= 50:
            try:
                s_hrs = int(p["value"])
                pace  = round(s_hrs / gp * 162)
                if pace >= 50:
                    entries.append({"text": f"<b>{name}</b> ({team}) leads the majors with {s_hrs} HRs and is on pace for <b>{pace} this season</b>", "pri": pace + 35, "type": "PACE", "color": "#a78bfa", "bg": "#0f0a1f"})
                elif pace >= 43:
                    entries.append({"text": f"<b>{name}</b> ({team}) is on pace for <b>{pace} HRs</b> — currently at {s_hrs} on the year", "pri": pace + 20, "type": "PACE", "color": "#a78bfa", "bg": "#0f0a1f"})
            except Exception:
                pass

        if entries:
            best = max(entries, key=lambda x: x["pri"])
            raw.append({**best, "pid": pid})

    # ── Tonight matchup insights (PHI + NYY vs tonight's opponent) ────
    tonight_sched = get_todays_schedule()
    phi_opp = nyy_opp = None
    for g in tonight_sched:
        hid = g["teams"]["home"]["team"]["id"]
        aid = g["teams"]["away"]["team"]["id"]
        if PHI_ID in (hid, aid):
            phi_opp = aid if hid == PHI_ID else hid
        if NYY_ID in (hid, aid):
            nyy_opp = aid if hid == NYY_ID else hid

    for tracked_id, opp_id, label in ((PHI_ID, phi_opp, "PHI"), (NYY_ID, nyy_opp, "NYY")):
        if not opp_id:
            continue
        opp_abbr = TEAM_ABBRS.get(opp_id, "")
        for p in team_players.get(label, [])[:5]:
            pid = p.get("id")
            if not pid:
                continue
            vs   = get_vs_team_stats(pid, opp_id)
            ab   = vs.get("atBats", 0)
            hits = vs.get("hits", 0)
            hrs  = vs.get("homeRuns", 0)
            if ab < 10:
                continue
            ba = round(hits / ab, 3)
            if ba >= 0.350:
                raw.append({"text": f"<b>{p['name']}</b> ({label}) is batting <b>.{int(ba*1000):03d}</b> ({hits}-for-{ab}) vs {opp_abbr} — tonight's opponent", "pri": int(ba * 320) + 65, "type": "TONIGHT", "color": "#f97316", "bg": "#1a0e05", "pid": pid})
            elif hrs >= 3:
                raw.append({"text": f"<b>{p['name']}</b> ({label}) has <b>{hrs} career HRs</b> against tonight's opponent ({opp_abbr})", "pri": hrs * 12 + 45, "type": "TONIGHT", "color": "#f97316", "bg": "#1a0e05", "pid": pid})

    # ── Sort + deduplicate by player, return top 8 ────────────────────
    raw.sort(key=lambda x: -x["pri"])
    final, seen_pids = [], set()
    for item in raw:
        if item["pid"] not in seen_pids:
            seen_pids.add(item["pid"])
            final.append(item)
        if len(final) >= 8:
            break

    return final

def render_insight_row(ins):
    c   = ins.get("color", "#4f8ef7")
    bg  = ins.get("bg", "#0a0f20")
    tag = ins.get("type", "NOTE")
    tag_html = (
        f"<span class='insight-tag' "
        f"style='color:{c};background:{bg};border:1px solid {c}33'>"
        f"{tag}</span>"
    )
    return (f"<div class='insight-row'>"
            f"{tag_html}"
            f"<span class='insight-text'>{ins['text']}</span>"
            f"</div>")

def render_tonight_pitcher_row(p, stats):
    matchup = f"vs {p['opp_abbr']}" if p["home"] else f"@ {p['opp_abbr']}"
    season_avg_disp = f"{stats['season_avg']}" if stats["season_avg"] is not None else "—"
    last5_disp      = f"{stats['last5_avg']}"  if stats["last5_avg"]  is not None else "—"

    # Spark bar: fill based on season avg (max ~10 Ks = full bar)
    bar_pct = min(int((stats["season_avg"] or 0) / 10 * 100), 100)
    l5_pct  = min(int((stats["last5_avg"]  or 0) / 10 * 100), 100)
    l5_color = "#4ade80" if (stats["last5_avg"] or 0) >= (stats["season_avg"] or 0) else "#ef4444"

    phi_nyy_abbrs = {
        p["abbr"] for p in [{"abbr": "PHI"}, {"abbr": "NYY"}]
        if p["abbr"] in ("PHI", "NYY")
    }
    is_tracked = p["abbr"] in ("PHI", "NYY") or p["opp_abbr"] in ("PHI", "NYY")
    tracked_border = ""
    if p["abbr"] == "PHI" or p["opp_abbr"] == "PHI":
        tracked_border = "border-left:3px solid #e81828;"
    elif p["abbr"] == "NYY" or p["opp_abbr"] == "NYY":
        tracked_border = "border-left:3px solid #4d7bc4;"

    return f"""
    <div class="tonight-row" style="{tracked_border}">
        <div class="tonight-left">
            <div style="display:flex;align-items:center;gap:0.5rem">
                {logo(p['abbr'], 24)}
                <div>
                    <div class="tonight-name">{p['name']}</div>
                    <div class="tonight-meta">{p['abbr']} {matchup} &nbsp;·&nbsp; {stats['record']} &nbsp;·&nbsp; {stats['era']} ERA</div>
                </div>
            </div>
        </div>
        <div class="tonight-stats">
            <div class="tonight-stat-block">
                <div class="tonight-stat-val">{season_avg_disp}</div>
                <div class="tonight-stat-label">K/START</div>
                <div class="k-bar-wrap"><div class="k-bar" style="width:{bar_pct}%;background:#4f8ef7"></div></div>
            </div>
            <div class="tonight-stat-block">
                <div class="tonight-stat-val" style="color:{l5_color}">{last5_disp}</div>
                <div class="tonight-stat-label">K/LAST 5</div>
                <div class="k-bar-wrap"><div class="k-bar" style="width:{l5_pct}%;background:{l5_color}"></div></div>
            </div>
        </div>
    </div>"""

def parse_standings(records):
    """Returns dict: div_id → list of team dicts sorted by standing."""
    divs = {}
    for rec in records:
        did  = rec.get("division", {}).get("id")
        dname = ALL_DIVS.get(did, "")
        teams = []
        for t in rec.get("teamRecords", []):
            tid   = t.get("team", {}).get("id")
            abbr  = t.get("team", {}).get("abbreviation", "")
            name  = t.get("team", {}).get("name", "")
            w     = t.get("wins", 0)
            l     = t.get("losses", 0)
            pct   = t.get("winningPercentage", ".000")
            gb    = t.get("gamesBack", "-")
            strk  = t.get("streak", {}).get("streakCode", "")
            l10r  = next((s for s in t.get("records", {}).get("splitRecords", []) if s.get("type") == "lastTen"), {})
            l10   = f"{l10r.get('wins','-')}-{l10r.get('losses','-')}" if l10r else "-"
            teams.append({"id": tid, "abbr": abbr, "name": name, "w": w, "l": l,
                          "pct": pct, "gb": gb, "streak": strk, "l10": l10})
        divs[did] = {"name": dname, "teams": teams}
    return divs

def wildcard_positions(divs, league_div_ids):
    """Compute WC positions for one league from division standings."""
    leaders = set()
    all_teams = []
    for did in league_div_ids:
        if did not in divs:
            continue
        teams = divs[did]["teams"]
        if teams:
            leaders.add(teams[0]["id"])
        all_teams.extend(teams)
    # Sort by pct desc, then wins desc
    all_teams_sorted = sorted(all_teams, key=lambda t: (-float(t["pct"]), -t["w"]))
    return [t for t in all_teams_sorted if t["id"] not in leaders]

# ── Render Helpers ────────────────────────────────────────────────────
def render_standings_table(div_data, highlight_ids=(PHI_ID, NYY_ID), show_wc=False, wc_count=3):
    teams = div_data["teams"]
    rows  = ""
    for i, t in enumerate(teams):
        rc = ""
        if t["id"] == PHI_ID:
            rc = "phi-row"
        elif t["id"] == NYY_ID:
            rc = "nyy-row"
        elif i == 0:
            rc = "div-leader"

        gb_str = "—" if t["gb"] in ("-", "0", 0) else t["gb"]
        strk   = t["streak"]
        strk_cls = "strk-w" if strk.startswith("W") else ("strk-l" if strk.startswith("L") else "")

        wc_tag = ""
        if show_wc and i < wc_count:
            wc_tag = f"<span class='wc-tag'>WC{i+1}</span>"

        rows += f"""
        <tr class="{rc}">
            <td>{logo(t['abbr'], 18)} {t['name']}{wc_tag}</td>
            <td>{t['w']}</td>
            <td>{t['l']}</td>
            <td class="pct">{t['pct']}</td>
            <td>{gb_str}</td>
            <td>{t['l10']}</td>
            <td class="{strk_cls}">{strk}</td>
        </tr>"""

    return f"""
    <div class="std-wrap">
        <div class="std-div-title">{div_data['name']}</div>
        <table class="std-tbl">
            <thead><tr>
                <th>Team</th><th>W</th><th>L</th><th>PCT</th><th>GB</th><th>L10</th><th>Strk</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>"""

def render_hero_card(game, my_id, css_class, label):
    if game is None:
        return f"""
        <div class="hero-card {css_class}">
            <div class="hero-card-label">{label}</div>
            <div class="hero-noplay">No game yesterday</div>
        </div>"""

    home  = game["teams"]["home"]
    away  = game["teams"]["away"]
    hs    = home.get("score", 0)
    as_   = away.get("score", 0)
    hid   = home["team"]["id"]
    habbr = team_abbr(home["team"])
    aabbr = team_abbr(away["team"])
    hname = home["team"]["name"]
    aname = away["team"]["name"]
    inn   = game.get("linescore", {}).get("currentInning", 9)
    status= f"F/{inn}" if inn != 9 else "Final"

    my_won = (hid == my_id and hs > as_) or (hid != my_id and as_ > hs)
    result_label = "✓ WIN" if my_won else "✗ LOSS"
    result_color = "#22c55e" if my_won else "#ef4444"

    top_abbr, top_sc, bot_abbr, bot_sc = (
        (habbr, hs, aabbr, as_) if hs >= as_ else (aabbr, as_, habbr, hs)
    )
    top_name = hname if top_abbr == habbr else aname
    bot_name = hname if bot_abbr == habbr else aname

    return f"""
    <div class="hero-card {css_class}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.6rem">
            <div class="hero-card-label">{label}</div>
            <div style="font-family:'Barlow Condensed',sans-serif;font-size:0.85rem;font-weight:700;color:{result_color}">{result_label}</div>
        </div>
        <div class="hero-matchup">
            <div class="hero-team-row">
                {logo(top_abbr, 26)}
                <span class="hero-tname w">{top_name}</span>
                <span class="hero-score w">{top_sc}</span>
            </div>
            <div class="hero-team-row">
                {logo(bot_abbr, 26)}
                <span class="hero-tname l">{bot_name}</span>
                <span class="hero-score l">{bot_sc}</span>
            </div>
        </div>
        <div class="hero-status">{status} · {aabbr} @ {habbr}</div>
    </div>"""

def render_game_row(g):
    home  = g["teams"]["home"]
    away  = g["teams"]["away"]
    hs    = home.get("score", 0)
    as_   = away.get("score", 0)
    hid   = home["team"]["id"]
    aid   = away["team"]["id"]
    habbr = team_abbr(home["team"])
    aabbr = team_abbr(away["team"])
    hname = home["team"]["name"]
    aname = away["team"]["name"]
    inn   = g.get("linescore", {}).get("currentInning", 9)
    status= f"F/{inn}" if inn != 9 else "F"

    row_cls = ""
    if PHI_ID in (hid, aid): row_cls = "phi-game"
    elif NYY_ID in (hid, aid): row_cls = "nyy-game"

    # Winner on top
    if hs >= as_:
        t1_abbr, t1_name, t1_sc, t1_w = habbr, hname, hs, True
        t2_abbr, t2_name, t2_sc, t2_w = aabbr, aname, as_, False
    else:
        t1_abbr, t1_name, t1_sc, t1_w = aabbr, aname, as_, True
        t2_abbr, t2_name, t2_sc, t2_w = habbr, hname, hs, False

    def trow(abbr, name, sc, won):
        wc = "w" if won else "l"
        return (f"<div class='game-team-line'>"
                f"{logo(abbr, 20)}"
                f"<span class='game-team-name {wc}'>{name}</span>"
                f"<span class='game-sc {wc}'>{sc}</span>"
                f"</div>")

    return (f"<div class='game-row {row_cls}'>"
            f"<div class='game-side'>{trow(t1_abbr,t1_name,t1_sc,t1_w)}{trow(t2_abbr,t2_name,t2_sc,t2_w)}</div>"
            f"<div class='game-info'>{aabbr}@{habbr}<br>{status}</div>"
            f"</div>")

def render_leader_row(i, name, abbr, val):
    rank_cls = "gold" if i == 0 else ("silver" if i == 1 else ("bronze" if i == 2 else ""))
    rank_str = ["1", "2", "3"][i] if i < 3 else str(i + 1)
    return (f"<div class='leader-row'>"
            f"<span class='leader-rank {rank_cls}'>{rank_str}</span>"
            f"{logo(abbr, 22)}"
            f"<span class='leader-name'>{name}</span>"
            f"<span class='leader-team'>{abbr}</span>"
            f"<span class='leader-val'>{val}</span>"
            f"</div>")

def render_pitcher_row(p):
    dec_html = f"<span class='pitcher-dec {p['dec']}'>{p['dec']}</span>" if p["dec"] else ""
    return (f"<div class='pitcher-row'>"
            f"<div style='display:flex;align-items:center;gap:0.5rem;min-width:180px'>"
            f"{logo(p['abbr'], 22)}"
            f"<div class='pitcher-left'>"
            f"<div class='pitcher-name'>{p['name']}{dec_html}</div>"
            f"<div class='pitcher-meta'>{p['abbr']} vs {p['opp']} · {p['ip']} IP · {p['h']}H {p['er']}ER {p['bb']}BB</div>"
            f"</div></div>"
            f"<div style='text-align:right'>"
            f"<div class='pitcher-k'>{p['k']}</div>"
            f"<div class='pitcher-k-label'>STRK</div>"
            f"</div>"
            f"</div>")

# ═══════════════════════════════════════════════════════════════════════
# RENDER
# ═══════════════════════════════════════════════════════════════════════
vd      = st.session_state.vd
vd_str  = vd.strftime("%Y-%m-%d")
today   = date.today()
is_today_minus_1 = (vd == today - timedelta(days=1))

# ── Header ───────────────────────────────────────────────────────────
c_prev, c_title, c_next = st.columns([1, 6, 1])
with c_prev:
    st.write("")
    if st.button("◀  Prev"):
        st.session_state.vd -= timedelta(days=1)
        st.rerun()
with c_title:
    st.markdown(f"""
    <div class="roundup-header">
        <div class="roundup-title"><span class="accent">Capy's</span> MLB Roundup</div>
        <div class="roundup-date">{vd.strftime("%A, %B %-d, %Y")}</div>
    </div>""", unsafe_allow_html=True)
with c_next:
    st.write("")
    if st.button("Next  ▶", disabled=is_today_minus_1):
        st.session_state.vd += timedelta(days=1)
        st.rerun()

st.markdown("<hr class='roundup-rule'>", unsafe_allow_html=True)

# ── Load Data ────────────────────────────────────────────────────────
with st.spinner("Loading..."):
    games_list   = get_games(vd_str)
    standings_raw = get_standings_data()

if not games_list:
    st.markdown('<div class="no-data">No final games found for this date.</div>', unsafe_allow_html=True)
    st.stop()

divs = parse_standings(standings_raw)

phi_game = next((g for g in games_list if PHI_ID in (g["teams"]["home"]["team"]["id"], g["teams"]["away"]["team"]["id"])), None)
nyy_game = next((g for g in games_list if NYY_ID in (g["teams"]["home"]["team"]["id"], g["teams"]["away"]["team"]["id"])), None)

al_east = divs.get(201, {"name": "AL East", "teams": []})
nl_east = divs.get(204, {"name": "NL East", "teams": []})
al_wc   = wildcard_positions(divs, [201, 202, 200])
nl_wc   = wildcard_positions(divs, [204, 205, 203])

# ══ SECTION 1: My Teams + Division Focus ═════════════════════════════
st.markdown('<div class="sec-head">My Teams</div>', unsafe_allow_html=True)

hero_cols = st.columns(2)
with hero_cols[0]:
    st.markdown(render_hero_card(phi_game, PHI_ID, "phi", "⬤ Phillies"), unsafe_allow_html=True)
with hero_cols[1]:
    st.markdown(render_hero_card(nyy_game, NYY_ID, "nyy", "⬤ Yankees"), unsafe_allow_html=True)

st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
st.markdown('<div class="sec-head">AL East &amp; NL East Standings</div>', unsafe_allow_html=True)

div_cols = st.columns(2)
with div_cols[0]:
    st.markdown(render_standings_table(al_east), unsafe_allow_html=True)
with div_cols[1]:
    st.markdown(render_standings_table(nl_east), unsafe_allow_html=True)

st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
st.markdown('<div class="sec-head">Wild Card Race</div>', unsafe_allow_html=True)

wc_cols = st.columns(2)
with wc_cols[0]:
    al_wc_div = {"name": "AL Wild Card", "teams": al_wc[:6]}
    st.markdown(render_standings_table(al_wc_div, show_wc=True, wc_count=3), unsafe_allow_html=True)
with wc_cols[1]:
    nl_wc_div = {"name": "NL Wild Card", "teams": nl_wc[:6]}
    st.markdown(render_standings_table(nl_wc_div, show_wc=True, wc_count=3), unsafe_allow_html=True)

# ══ SECTION 2: All Yesterday's Scores ════════════════════════════════
st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
st.markdown(f'<div class="sec-head">All Games — {vd.strftime("%B %-d")}</div>', unsafe_allow_html=True)

# Sort: PHI/NYY first, then by score desc
def game_sort_key(g):
    ids = {g["teams"]["home"]["team"]["id"], g["teams"]["away"]["team"]["id"]}
    priority = 0 if PHI_ID in ids or NYY_ID in ids else 1
    return (priority,)

sorted_games = sorted(games_list, key=game_sort_key)
game_rows_html = "".join(render_game_row(g) for g in sorted_games)
st.markdown(f'<div class="games-wrap">{game_rows_html}</div>', unsafe_allow_html=True)

# ══ SECTION 3: HR / RBI Leaders ══════════════════════════════════════
st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
st.markdown(f'<div class="sec-head">Yesterday\'s Performers</div>', unsafe_allow_html=True)

with st.spinner("Loading HR/RBI data..."):
    hrs, rbis = extract_hr_rbi(games_list)

perf_cols = st.columns(2)
with perf_cols[0]:
    st.markdown('<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:0.75rem;font-weight:700;letter-spacing:0.15em;color:#33333f;text-transform:uppercase;margin-bottom:0.5rem">Home Runs</div>', unsafe_allow_html=True)
    if hrs:
        rows_html = "".join(render_leader_row(i, p["n"], p["abbr"], f"{p['c']} HR") for i, p in enumerate(hrs[:12]))
        st.markdown(f'<div class="leaders-wrap">{rows_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-data">No home runs</div>', unsafe_allow_html=True)

with perf_cols[1]:
    st.markdown('<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:0.75rem;font-weight:700;letter-spacing:0.15em;color:#33333f;text-transform:uppercase;margin-bottom:0.5rem">RBI</div>', unsafe_allow_html=True)
    if rbis:
        rows_html = "".join(render_leader_row(i, p["n"], p["abbr"], f"{p['c']} RBI") for i, p in enumerate(rbis[:12]))
        st.markdown(f'<div class="leaders-wrap">{rows_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-data">No RBI data</div>', unsafe_allow_html=True)

# ══ SECTION 4: Full Standings ═════════════════════════════════════════
st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
st.markdown('<div class="sec-head">Full League Standings</div>', unsafe_allow_html=True)

al_divs_ordered = [201, 202, 200]
nl_divs_ordered = [204, 205, 203]

stand_cols = st.columns(2)
with stand_cols[0]:
    for did in al_divs_ordered:
        if did in divs:
            st.markdown(render_standings_table(divs[did]), unsafe_allow_html=True)
            st.markdown('<div style="margin-bottom:0.7rem"></div>', unsafe_allow_html=True)
with stand_cols[1]:
    for did in nl_divs_ordered:
        if did in divs:
            st.markdown(render_standings_table(divs[did]), unsafe_allow_html=True)
            st.markdown('<div style="margin-bottom:0.7rem"></div>', unsafe_allow_html=True)

# ══ SECTION 5: Starting Pitchers ══════════════════════════════════════
st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
st.markdown('<div class="sec-head">Starting Pitchers — Sorted by Strikeouts</div>', unsafe_allow_html=True)

with st.spinner("Loading pitcher data..."):
    pitchers = extract_pitchers(games_list)

if pitchers:
    # Two columns of pitchers
    mid = len(pitchers) // 2 + len(pitchers) % 2
    p_cols = st.columns(2)
    with p_cols[0]:
        html = "".join(render_pitcher_row(p) for p in pitchers[:mid])
        st.markdown(f'<div class="leaders-wrap">{html}</div>', unsafe_allow_html=True)
    with p_cols[1]:
        html = "".join(render_pitcher_row(p) for p in pitchers[mid:])
        st.markdown(f'<div class="leaders-wrap">{html}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="no-data">No pitcher data available.</div>', unsafe_allow_html=True)

# ══ SECTION 6: Batting Insights ══════════════════════════════════════
st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
st.markdown('<div class="sec-head">Recent Batting Insights</div>', unsafe_allow_html=True)

with st.spinner("Generating batting insights..."):
    insights = generate_batting_insights()

if insights:
    mid = len(insights) // 2 + len(insights) % 2
    ins_cols = st.columns(2)
    with ins_cols[0]:
        html = "".join(render_insight_row(i) for i in insights[:mid])
        st.markdown(f'<div class="leaders-wrap">{html}</div>', unsafe_allow_html=True)
    with ins_cols[1]:
        html = "".join(render_insight_row(i) for i in insights[mid:])
        st.markdown(f'<div class="leaders-wrap">{html}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="no-data">No notable batting insights right now. Check back during the season.</div>', unsafe_allow_html=True)

# ══ SECTION 7: Tonight's Projected Starters ══════════════════════════
st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
st.markdown(f'<div class="sec-head">Tonight\'s Projected Starters — {today.strftime("%B %-d")}</div>', unsafe_allow_html=True)

with st.spinner("Loading tonight's starters..."):
    tonight = get_tonight_starters()

if tonight:
    # Fetch stats for each pitcher (cached per player, ~1800s TTL)
    enriched = []
    for p in tonight:
        stats = get_pitcher_k_stats(p["id"])
        enriched.append((p, stats))

    # Sort: PHI/NYY first, then by season avg Ks desc
    def tonight_sort(item):
        p, s = item
        priority = 0 if p["abbr"] in ("PHI", "NYY") or p["opp_abbr"] in ("PHI", "NYY") else 1
        return (priority, -(s["season_avg"] or 0))

    enriched.sort(key=tonight_sort)

    # Split into two columns
    mid = len(enriched) // 2 + len(enriched) % 2
    tn_cols = st.columns(2)
    with tn_cols[0]:
        html = "".join(render_tonight_pitcher_row(p, s) for p, s in enriched[:mid])
        st.markdown(f'<div class="leaders-wrap">{html}</div>', unsafe_allow_html=True)
    with tn_cols[1]:
        html = "".join(render_tonight_pitcher_row(p, s) for p, s in enriched[mid:])
        st.markdown(f'<div class="leaders-wrap">{html}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="no-data">No probable pitchers announced yet for tonight.</div>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center;font-family:'JetBrains Mono',monospace;font-size:0.6rem;
color:#1e1e2a;margin-top:3rem;padding-top:1rem;border-top:1px solid #18181f;letter-spacing:0.1em">
MLB STATS API · CAPY'S MLB ROUNDUP · {today.strftime("%B %-d, %Y").upper()}
</div>
""", unsafe_allow_html=True)
