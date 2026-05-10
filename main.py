from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import get_connection
from model import get_team_form, get_head_to_head, get_draft_recommendation

app = FastAPI(
    title="MLBB Esports API",
    description="Live match data pipeline for Mobile Legends: Bang Bang",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/ui")
def serve_ui():
    return FileResponse("static/index.html")

@app.get("/")
def root():
    return {"message": "MLBB Esports API is running 🎮"}


@app.get("/matches")
def get_matches(status: str = None, league: str = None, limit: int = 20):
    """
    Get all matches. Optionally filter by:
    - status: 'finished', 'canceled', 'running'
    - league: e.g. 'World Championship'
    - limit: how many to return (default 20)
    """
    conn   = get_connection()
    cursor = conn.cursor()

    query  = "SELECT * FROM matches WHERE 1=1"
    params = []

    if status:
        query += " AND status = %s"
        params.append(status)

    if league:
        query += " AND league_name ILIKE %s"
        params.append(f"%{league}%")

    query += " ORDER BY scheduled_at DESC NULLS LAST"
    query += f" LIMIT {limit}"

    cursor.execute(query, params)
    rows    = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    cursor.close()
    conn.close()

    return {"count": len(rows), "matches": [dict(zip(columns, row)) for row in rows]}


@app.get("/matches/{match_id}")
def get_match(match_id: int):
    """Get a single match by its ID"""
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM matches WHERE id = %s", (match_id,))
    row     = cursor.fetchone()
    columns = [desc[0] for desc in cursor.description]

    cursor.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Match not found")

    return dict(zip(columns, row))


@app.get("/standings")
def get_standings():
    """
    Calculate win/loss record for each team from finished matches.
    This is computed live from your database — no separate table needed.
    """
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            team_name,
            COUNT(*) AS total_matches,
            SUM(CASE WHEN winner_id = team_id THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN winner_id != team_id AND winner_id IS NOT NULL THEN 1 ELSE 0 END) AS losses
        FROM (
            SELECT team1_id AS team_id, team1_name AS team_name, winner_id FROM matches WHERE status = 'finished'
            UNION ALL
            SELECT team2_id AS team_id, team2_name AS team_name, winner_id FROM matches WHERE status = 'finished'
        ) AS team_matches
        GROUP BY team_name, team_id
        ORDER BY wins DESC
    """)

    rows    = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    cursor.close()
    conn.close()

    return {"standings": [dict(zip(columns, row)) for row in rows]}


@app.get("/tournaments")
def get_tournaments():
    """List all unique tournaments in the database"""
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            league_name,
            serie_name,
            tournament_name,
            COUNT(*) AS match_count,
            MIN(scheduled_at) AS starts,
            MAX(scheduled_at) AS ends
        FROM matches
        GROUP BY league_name, serie_name, tournament_name
        ORDER BY starts DESC NULLS LAST
    """)

    rows    = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    cursor.close()
    conn.close()

    return {"tournaments": [dict(zip(columns, row)) for row in rows]}

    from model import get_team_form, get_head_to_head

@app.get("/form/{team_name}")
def team_form(team_name: str, last_n: int = 5):
    """
    Get form for a team based on their last N matches.
    Example: /form/ONIC or /form/ONIC?last_n=10
    """
    result = get_team_form(team_name, last_n)
    if not result:
        raise HTTPException(status_code=404, detail=f"No data found for team: {team_name}")
    return result


@app.get("/h2h")
def head_to_head(team_a: str, team_b: str):
    """
    Get head-to-head record between two teams.
    Example: /h2h?team_a=ONIC&team_b=RRQ Hoshi
    """
    result = get_head_to_head(team_a, team_b)
    if not result:
        raise HTTPException(status_code=404, detail="No matches found between these teams")
    return result

@app.get("/heroes")
def get_heroes(role: str = None, tier: str = None, limit: int = 50):
    """
    Get all heroes with their meta stats.
    Filter by role (Tank, Mage, etc) or tier (S, A, B, C)
    Example: /heroes?role=Tank&tier=S
    """
    conn   = get_connection()
    cursor = conn.cursor()

    query  = "SELECT * FROM heroes WHERE 1=1"
    params = []

    if role:
        query += " AND role ILIKE %s"
        params.append(f"%{role}%")

    if tier:
        query += " AND tier = %s"
        params.append(tier.upper())

    query += " ORDER BY win_rate DESC"
    query += f" LIMIT {limit}"

    cursor.execute(query, params)
    rows    = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    cursor.close()
    conn.close()

    return {"count": len(rows), "heroes": [dict(zip(columns, row)) for row in rows]}


@app.get("/heroes/top")
def get_top_heroes():
    """
    Get top heroes by category — most banned, highest win rate, most picked.
    Useful for quick meta overview.
    """
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT hero_name, role, tier, win_rate, pick_rate, ban_rate FROM heroes ORDER BY win_rate DESC LIMIT 5")
    top_wr    = [dict(zip([d[0] for d in cursor.description], r)) for r in cursor.fetchall()]

    cursor.execute("SELECT hero_name, role, tier, win_rate, pick_rate, ban_rate FROM heroes ORDER BY ban_rate DESC LIMIT 5")
    top_ban   = [dict(zip([d[0] for d in cursor.description], r)) for r in cursor.fetchall()]

    cursor.execute("SELECT hero_name, role, tier, win_rate, pick_rate, ban_rate FROM heroes ORDER BY pick_rate DESC LIMIT 5")
    top_pick  = [dict(zip([d[0] for d in cursor.description], r)) for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return {
        "highest_win_rate": top_wr,
        "most_banned":      top_ban,
        "most_picked":      top_pick,
    }


@app.get("/heroes/{hero_name}")
def get_hero(hero_name: str):
    """
    Get full stats for a specific hero including counters.
    Example: /heroes/Gloo or /heroes/Hanabi
    """
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM heroes WHERE hero_name ILIKE %s", (hero_name,))
    row     = cursor.fetchone()
    columns = [desc[0] for desc in cursor.description]

    cursor.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Hero '{hero_name}' not found")

    return dict(zip(columns, row))


@app.get("/counters/{hero_name}")
def get_counters(hero_name: str):
    """
    Get counter matchup info for a hero.
    Returns what this hero beats and what beats this hero.
    Example: /counters/Gloo
    """
    conn   = get_connection()
    cursor = conn.cursor()

    # Get the hero's own counter data
    cursor.execute("""
        SELECT hero_name, role, tier, win_rate, strong_against, weak_against
        FROM heroes WHERE hero_name ILIKE %s
    """, (hero_name,))
    row     = cursor.fetchone()
    columns = [desc[0] for desc in cursor.description]

    if not row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Hero '{hero_name}' not found")

    hero = dict(zip(columns, row))

    # Also find heroes that list this hero as their counter
    cursor.execute("""
        SELECT hero_name, role, tier, win_rate
        FROM heroes
        WHERE strong_against ILIKE %s
        ORDER BY win_rate DESC
    """, (f"%{hero_name}%",))

    countered_by_rows = cursor.fetchall()
    countered_by_cols = [desc[0] for desc in cursor.description]

    cursor.close()
    conn.close()

    strong_list   = [h.strip() for h in hero["strong_against"].split(",")] if hero["strong_against"] else []
    weak_list     = [h.strip() for h in hero["weak_against"].split(",")] if hero["weak_against"] else []
    countered_by  = [dict(zip(countered_by_cols, r)) for r in countered_by_rows]

    return {
        "hero":          hero["hero_name"],
        "role":          hero["role"],
        "tier":          hero["tier"],
        "win_rate":      hero["win_rate"],
        "strong_against": strong_list,
        "weak_against":  weak_list,
        "countered_by":  countered_by,
    }

@app.get("/recommend")
def recommend(
    role: str,
    enemy1: str = None,
    enemy2: str = None,
    enemy3: str = None,
    enemy4: str = None,
    enemy5: str = None,
):
    """
    Recommend best heroes given enemy team and your desired role.
    Role options: Tank, Fighter, Mage, Marksman, Assassin, Support
    Example: /recommend?role=Mage&enemy1=Gloo&enemy2=Hanabi
    """
    enemy_heroes = [e for e in [enemy1, enemy2, enemy3, enemy4, enemy5] if e]

    if not role:
        raise HTTPException(status_code=400, detail="Provide a role")

    results = get_draft_recommendation(enemy_heroes, role)

    if not results:
        raise HTTPException(status_code=404, detail=f"No heroes found for role: {role}")

    return {
        "your_role":   role,
        "enemy_team":  enemy_heroes,
        "recommended": results
    }

@app.get("/heroes/names")
def get_hero_names():
    """Return just hero names for autocomplete"""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT hero_name FROM heroes ORDER BY hero_name ASC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"heroes": [row[0] for row in rows]}