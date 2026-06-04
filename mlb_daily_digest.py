import streamlit as st
import requests
from datetime import date, timedelta
from collections import defaultdict

st.set_page_config(
    page_title="MLB Daily Digest",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Source+Serif+4:ital,wght@0,300;0,400;1,300&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Source Serif 4', serif;
}
.stApp {
    background-color: #0f0f0f;
    color: #f0ebe0;
}
h1, h2, h3, .section-title {
    font-family: 'Oswald', sans-serif;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.digest-header {
    border-bottom: 3px solid #c8102e;
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
}
.digest-header h1 {
    font-family: 'Oswald', sans-serif;
    font-size: 2.6rem;
    font-weight: 700;
    color: #f0ebe0;
    letter-spacing: 0.08em;
    margin: 0;
    text-transform: uppercase;
}
.digest-header .dateline {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: #888;
    letter-spacing: 0.1em;
    margin-top: 0.2rem;
}

.section-title {
    font-family: 'Oswald', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: #c8102e;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 0.4rem;
    margin-bottom: 1rem;
}

.game-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-left: 3px solid #c8102e;
    border-radius: 2px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.6rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem;
}
.game-card.featured {
    border-left: 4px solid #003087;
    background: #141420;
}
.game-card.featured-red {
    border-left: 4px solid #e81828;
    background: #1a1010;
}
.game-winner {
    font-weight: 500;
    color: #f0ebe0;
    font-size: 0.9rem;
}
.game-loser {
    color: #666;
    font-size: 0.9rem;
}
.game-score {
    color: #c8102e;
    font-weight: 500;
}
.game-status {
    color: #888;
    font-size: 0.72rem;
    margin-top: 0.2rem;
}

.stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.45rem 0;
    border-bottom: 1px solid #1e1e1e;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem;
}
.stat-row:last-child { border-bottom: none; }
.stat-name { color: #d0c8b8; }
.stat-team { color: #666; font-size: 0.72rem; margin-left: 0.4rem; }
.stat-val { color: #c8102e; font-weight: 500; font-size: 0.9rem; }

.pitcher-row {
    background: #141414;
    border: 1px solid #222;
    border-radius: 2px;
    padding: 0.7rem 0.9rem;
    margin-bottom: 0.5rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
}
.pitcher-name { color: #f0ebe0; font-weight: 500; font-size: 0.88rem; }
.pitcher-line { color: #888; margin-top: 0.2rem; }
.pitcher-k { color: #f5a623; font-weight: 500; }

.rank-badge {
    display: inline-block;
    width: 1.4rem;
    text-align: center;
    color: #666;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    margin-right: 0.3rem;
}
.rank-badge.top { color: #c8102e; font-weight: 600; }

.standings-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
}
.standings-table th {
    color: #666;
    font-weight: 400;
    text-align: right;
    padding: 0.3rem 0.5rem;
    border-bottom: 1px solid #2a2a2a;
    font-size: 0.7rem;
    letter-spacing: 0.06em;
}
.standings-table th:first-child { text-align: left; }
.standings-table td {
    padding: 0.4rem 0.5rem;
    border-bottom: 1px solid #1a1a1a;
    text-align: right;
    color: #c0b8a8;
}
.standings-table td:first-child { text-align: left; color: #f0ebe0; }
.standings-table tr.divider-top td { border-top: 2px solid #333; }
.standings-table .pct-lead { color: #c8102e; font-weight: 500; }
.team-highlight-phi { background: #140a0a; }
.team-highlight-nyy { background: #0a0a14; }

.alert-banner {
    background: #1e1010;
    border: 1px solid #c8102e;
    border-radius: 2px;
    padding: 0.7rem 1rem;
    margin-bottom: 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    color: #f0ebe0;
}
.alert-banner .alert-label {
    color: #c8102e;
    font-weight: 600;
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}

.no-data {
    color: #555;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    font-style: italic;
    padding: 1rem 0;
}

[data-testid="stMetricValue"] {
    font-family: 'Oswald', sans-serif !important;
    font-size: 2rem !important;
    color: #c8102e !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.7rem !important;
    color: #666 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}
</style>
""", unsafe_allow_html=True)

BASE = "https://statsapi.mlb.com/api/v1"

PHI_ID = 143
NYY_ID = 147

TRACKED = {PHI_ID: ("PHI", "Phillies", "featured-red"), NYY_ID: ("NYY", "Yankees", "featured")}

@st.cache_data(ttl=300)
def get_yesterday_games(game_date):
    url = f"{BASE}/schedule?sportId=1&date={game_date}&hydrate=linescore,decisions,probablePitcher"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return []
    data = r.json()
    games = []
    for day in data.get("dates", []):
        for g in day.get("games", []):
            if g.get("status", {}).get("abstractGameState") == "Final":
                games.append(g)
    return games

@st.cache_data(ttl=300)
def get_game_feed(game_pk):
    url = f"{BASE}/game/{game_pk}/boxscore"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return None
    return r.json()

@st.cache_data(ttl=600)
def get_season_leaders(stat, limit=10):
    url = f"{BASE}/stats/leaders?leaderCategories={stat}&sportId=1&season=2025&limit={limit}"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return []
    data = r.json()
    leaders = []
    for cat in data.get("leagueLeaders", []):
        for row in cat.get("leaders", []):
            leaders.append({
                "rank": row.get("rank"),
                "name": row.get("person", {}).get("fullName", ""),
                "team": row.get("team", {}).get("abbreviation", ""),
                "value": row.get("value"),
            })
    return leaders

@st.cache_data(ttl=300)
def get_standings():
    url = f"{BASE}/standings?leagueId=103,104&season=2025&standingsTypes=regularSeason"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return []
    return r.json().get("records", [])

def extract_hr_rbi(games):
    hrs = defaultdict(lambda: {"name": "", "team": "", "count": 0})
    rbis = defaultdict(lambda: {"name": "", "team": "", "count": 0})

    for g in games:
        pk = g["gamePk"]
        box = get_game_feed(pk)
        if not box:
            continue
        for side in ["home", "away"]:
            team_abbr = g["teams"][side]["team"].get("abbreviation", "")
            batters = box.get("teams", {}).get(side, {}).get("batters", [])
            players = box.get("teams", {}).get(side, {}).get("players", {})
            for pid in batters:
                key = f"ID{pid}"
                p = players.get(key, {})
                stats = p.get("stats", {}).get("batting", {})
                name = p.get("person", {}).get("fullName", "")
                hr = stats.get("homeRuns", 0)
                rbi = stats.get("rbi", 0)
                if hr:
                    hrs[pid]["name"] = name
                    hrs[pid]["team"] = team_abbr
                    hrs[pid]["count"] += hr
                if rbi:
                    rbis[pid]["name"] = name
                    rbis[pid]["team"] = team_abbr
                    rbis[pid]["count"] += rbi

    hrs_sorted = sorted(hrs.values(), key=lambda x: -x["count"])
    rbis_sorted = sorted(rbis.values(), key=lambda x: -x["count"])
    return hrs_sorted, rbis_sorted

def extract_pitchers(games):
    pitchers = []
    for g in games:
        pk = g["gamePk"]
        away_name = g["teams"]["away"]["team"]["name"]
        home_name = g["teams"]["home"]["team"]["name"]
        away_abbr = g["teams"]["away"]["team"].get("abbreviation", "")
        home_abbr = g["teams"]["home"]["team"].get("abbreviation", "")

        box = get_game_feed(pk)
        if not box:
            continue

        for side, opp_abbr, opp_name in [("away", home_abbr, home_name), ("home", away_abbr, away_name)]:
            pitchers_list = box.get("teams", {}).get(side, {}).get("pitchers", [])
            players = box.get("teams", {}).get(side, {}).get("players", {})
            if not pitchers_list:
                continue
            sp_id = pitchers_list[0]
            key = f"ID{sp_id}"
            p = players.get(key, {})
            stats = p.get("stats", {}).get("pitching", {})
            name = p.get("person", {}).get("fullName", "")
            ip = stats.get("inningsPitched", "0.0")
            k = stats.get("strikeOuts", 0)
            er = stats.get("earnedRuns", 0)
            h = stats.get("hits", 0)
            bb = stats.get("baseOnBalls", 0)
            team_abbr = box.get("teams", {}).get(side, {}).get("team", {}).get("abbreviation", "")

            decision = ""
            decisions = g.get("decisions", {})
            winner_id = decisions.get("winner", {}).get("id")
            loser_id = decisions.get("loser", {}).get("id")
            if sp_id == winner_id:
                decision = "W"
            elif sp_id == loser_id:
                decision = "L"

            pitchers.append({
                "name": name,
                "team": team_abbr or (away_abbr if side == "away" else home_abbr),
                "opp": opp_abbr,
                "ip": ip,
                "k": k,
                "er": er,
                "h": h,
                "bb": bb,
                "decision": decision,
            })

    return sorted(pitchers, key=lambda x: -x["k"])

def render_standings(records):
    division_order = {
        "American League East": 1, "American League Central": 2, "American League West": 3,
        "National League East": 4, "National League Central": 5, "National League West": 6,
    }
    records_sorted = sorted(records, key=lambda r: division_order.get(r.get("division", {}).get("nameShort", ""), 99))

    phi_team_records = {}
    nyy_team_records = {}

    st.markdown('<div class="section-title">Standings</div>', unsafe_allow_html=True)

    for rec in records_sorted:
        div_name = rec.get("division", {}).get("name", "")
        teams = rec.get("teamRecords", [])

        st.markdown(f"<div style='font-family:Oswald,sans-serif;font-size:0.8rem;color:#888;letter-spacing:0.1em;text-transform:uppercase;margin:1rem 0 0.4rem;'>{div_name}</div>", unsafe_allow_html=True)

        rows_html = ""
        for i, t in enumerate(teams):
            tname = t.get("team", {}).get("name", "")
            tid = t.get("team", {}).get("id")
            w = t.get("wins", 0)
            l = t.get("losses", 0)
            pct = t.get("winningPercentage", ".000")
            gb = t.get("gamesBack", "-")
            streak = t.get("streak", {}).get("streakCode", "")
            l10 = t.get("records", {}).get("splitRecords", [])
            last10 = next((s for s in l10 if s.get("type") == "lastTen"), {})
            l10_str = f"{last10.get('wins','-')}-{last10.get('losses','-')}" if last10 else "-"

            row_class = ""
            if tid == PHI_ID:
                row_class = "team-highlight-phi"
            elif tid == NYY_ID:
                row_class = "team-highlight-nyy"

            divider_class = "divider-top" if i == 3 else ""

            rows_html += f"""
            <tr class="{row_class} {divider_class}">
                <td>{tname}</td>
                <td>{w}</td>
                <td>{l}</td>
                <td class="pct-lead">{pct}</td>
                <td>{gb}</td>
                <td>{l10_str}</td>
                <td>{streak}</td>
            </tr>"""

        st.markdown(f"""
        <table class="standings-table">
            <thead><tr>
                <th>Team</th><th>W</th><th>L</th><th>PCT</th><th>GB</th><th>L10</th><th>Strk</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>""", unsafe_allow_html=True)

yesterday = date.today() - timedelta(days=1)
game_date_str = yesterday.strftime("%Y-%m-%d")

st.markdown(f"""
<div class="digest-header">
    <div class="dateline">⚾ &nbsp; MLB DAILY DIGEST &nbsp; · &nbsp; MORNING EDITION</div>
    <h1>{yesterday.strftime("%A, %B %-d")}</h1>
</div>
""", unsafe_allow_html=True)

with st.spinner("Pulling yesterday's data..."):
    games = get_yesterday_games(game_date_str)

if not games:
    st.markdown('<div class="no-data">No final games found for yesterday. Check back during the season.</div>', unsafe_allow_html=True)
    st.stop()

# ── Tracked team alerts ──────────────────────────────────────────────
phi_games = [g for g in games if g["teams"]["home"]["team"]["id"] == PHI_ID or g["teams"]["away"]["team"]["id"] == PHI_ID]
nyy_games = [g for g in games if g["teams"]["home"]["team"]["id"] == NYY_ID or g["teams"]["away"]["team"]["id"] == NYY_ID]

def game_summary_line(g):
    home = g["teams"]["home"]
    away = g["teams"]["away"]
    hr = g.get("linescore", {}).get("innings", [])
    home_score = home.get("score", 0)
    away_score = away.get("score", 0)
    home_name = home["team"]["name"]
    away_name = away["team"]["name"]
    if home_score > away_score:
        return f"<b>{home_name}</b> def. {away_name} <span style='color:#c8102e'>{home_score}–{away_score}</span>"
    else:
        return f"<b>{away_name}</b> def. {home_name} <span style='color:#c8102e'>{away_score}–{home_score}</span>"

for label, tgames, color in [("PHI · Phillies", phi_games, "#e81828"), ("NYY · Yankees", nyy_games, "#003087")]:
    for g in tgames:
        line = game_summary_line(g)
        st.markdown(f"""
        <div class="alert-banner" style="border-color:{color}">
            <div class="alert-label" style="color:{color}">{label}</div>
            {line}
        </div>""", unsafe_allow_html=True)

# ── Layout ───────────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    # Games
    st.markdown('<div class="section-title">Yesterday\'s Results</div>', unsafe_allow_html=True)
    for g in sorted(games, key=lambda x: (
        -(x["teams"]["home"]["team"]["id"] in (PHI_ID, NYY_ID) or x["teams"]["away"]["team"]["id"] in (PHI_ID, NYY_ID)),
    )):
        home = g["teams"]["home"]
        away = g["teams"]["away"]
        home_score = home.get("score", 0)
        away_score = away.get("score", 0)
        home_name = home["team"]["name"]
        away_name = away["team"]["name"]
        home_id = home["team"]["id"]
        away_id = away["team"]["id"]

        card_class = "game-card"
        if home_id in TRACKED or away_id in TRACKED:
            tid = home_id if home_id in TRACKED else away_id
            card_class = f"game-card {TRACKED[tid][2]}"

        inn = g.get("linescore", {}).get("currentInning", 9)
        inn_str = f"F/{inn}" if inn != 9 else "Final"

        if home_score > away_score:
            winner_line = f'<span class="game-winner">{home_name}</span>'
            loser_line = f'<span class="game-loser">{away_name}</span>'
            score_line = f'<span class="game-score">{home_score}–{away_score}</span>'
        else:
            winner_line = f'<span class="game-winner">{away_name}</span>'
            loser_line = f'<span class="game-loser">{home_name}</span>'
            score_line = f'<span class="game-score">{away_score}–{home_score}</span>'

        st.markdown(f"""
        <div class="{card_class}">
            {winner_line} {score_line} over {loser_line}
            <div class="game-status">{inn_str} &nbsp;·&nbsp; {away_name} @ {home_name}</div>
        </div>""", unsafe_allow_html=True)

    # Starting pitchers
    st.markdown('<div class="section-title" style="margin-top:1.5rem">Starting Pitchers</div>', unsafe_allow_html=True)
    with st.spinner("Loading pitcher data..."):
        pitchers = extract_pitchers(games)

    if pitchers:
        for p in pitchers:
            dec_html = f" &nbsp;<span style='color:#f5a623;font-size:0.75rem'>({p['decision']})</span>" if p["decision"] else ""
            st.markdown(f"""
            <div class="pitcher-row">
                <div class="pitcher-name">{p['name']} <span style='color:#666;font-size:0.75rem'>{p['team']} vs {p['opp']}</span>{dec_html}</div>
                <div class="pitcher-line">
                    {p['ip']} IP &nbsp;·&nbsp;
                    <span class="pitcher-k">{p['k']} K</span> &nbsp;·&nbsp;
                    {p['h']} H &nbsp;·&nbsp; {p['er']} ER &nbsp;·&nbsp; {p['bb']} BB
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-data">No pitcher data available.</div>', unsafe_allow_html=True)

with col_right:
    # Yesterday HR / RBI
    st.markdown('<div class="section-title">Yesterday\'s Home Runs</div>', unsafe_allow_html=True)
    with st.spinner("Loading HR/RBI..."):
        hrs, rbis = extract_hr_rbi(games)

    if hrs:
        for i, p in enumerate(hrs[:15]):
            badge_class = "rank-badge top" if i < 3 else "rank-badge"
            hr_str = f"{'x'+str(p['count']) if p['count'] > 1 else '1'} HR"
            st.markdown(f"""
            <div class="stat-row">
                <span><span class="{badge_class}">{i+1}</span><span class="stat-name">{p['name']}</span><span class="stat-team">{p['team']}</span></span>
                <span class="stat-val">{hr_str}</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-data">No home runs yesterday.</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title" style="margin-top:1.5rem">Yesterday\'s RBI Leaders</div>', unsafe_allow_html=True)
    if rbis:
        for i, p in enumerate(rbis[:10]):
            badge_class = "rank-badge top" if i < 3 else "rank-badge"
            st.markdown(f"""
            <div class="stat-row">
                <span><span class="{badge_class}">{i+1}</span><span class="stat-name">{p['name']}</span><span class="stat-team">{p['team']}</span></span>
                <span class="stat-val">{p['count']} RBI</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-data">No RBI data available.</div>', unsafe_allow_html=True)

    # Season leaderboards
    st.markdown('<div class="section-title" style="margin-top:1.5rem">Season HR Leaders</div>', unsafe_allow_html=True)
    hr_leaders = get_season_leaders("homeRuns")
    for row in hr_leaders:
        badge_class = "rank-badge top" if row["rank"] <= 3 else "rank-badge"
        st.markdown(f"""
        <div class="stat-row">
            <span><span class="{badge_class}">{row['rank']}</span><span class="stat-name">{row['name']}</span><span class="stat-team">{row['team']}</span></span>
            <span class="stat-val">{row['value']}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title" style="margin-top:1.5rem">Season RBI Leaders</div>', unsafe_allow_html=True)
    rbi_leaders = get_season_leaders("rbi")
    for row in rbi_leaders:
        badge_class = "rank-badge top" if row["rank"] <= 3 else "rank-badge"
        st.markdown(f"""
        <div class="stat-row">
            <span><span class="{badge_class}">{row['rank']}</span><span class="stat-name">{row['name']}</span><span class="stat-team">{row['team']}</span></span>
            <span class="stat-val">{row['value']}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title" style="margin-top:1.5rem">Season BA Leaders</div>', unsafe_allow_html=True)
    ba_leaders = get_season_leaders("battingAverage")
    for row in ba_leaders:
        badge_class = "rank-badge top" if row["rank"] <= 3 else "rank-badge"
        st.markdown(f"""
        <div class="stat-row">
            <span><span class="{badge_class}">{row['rank']}</span><span class="stat-name">{row['name']}</span><span class="stat-team">{row['team']}</span></span>
            <span class="stat-val">{row['value']}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title" style="margin-top:1.5rem">Season K Leaders (SP)</div>', unsafe_allow_html=True)
    k_leaders = get_season_leaders("strikeouts")
    for row in k_leaders:
        badge_class = "rank-badge top" if row["rank"] <= 3 else "rank-badge"
        st.markdown(f"""
        <div class="stat-row">
            <span><span class="{badge_class}">{row['rank']}</span><span class="stat-name">{row['name']}</span><span class="stat-team">{row['team']}</span></span>
            <span class="stat-val">{row['value']} K</span>
        </div>""", unsafe_allow_html=True)

# ── Standings at bottom ───────────────────────────────────────────────
st.markdown("---")
with st.spinner("Loading standings..."):
    standings = get_standings()
if standings:
    render_standings(standings)

st.markdown(f"""
<div style='text-align:center;font-family:IBM Plex Mono,monospace;font-size:0.65rem;color:#444;margin-top:2rem;padding-top:1rem;border-top:1px solid #1a1a1a;'>
    DATA: MLB STATS API &nbsp;·&nbsp; UPDATED {date.today().strftime("%B %-d, %Y").upper()} &nbsp;·&nbsp; PHI + NYY TRACKED
</div>
""", unsafe_allow_html=True)
