from database import get_connection

def get_team_form(team_name: str, last_n: int = 5):
    """
    Calculate form for a team based on their last N matches.
    Works whether the team was team1 or team2 in the match.
    """
    conn   = get_connection()
    cursor = conn.cursor()

    # Get last N finished matches for this team
    # UNION combines matches where they were team1 OR team2
    cursor.execute("""
        SELECT 
            match_date,
            opponent,
            team_score,
            opponent_score,
            won
        FROM (
            SELECT
                COALESCE(begin_at, scheduled_at) AS match_date,
                team2_name   AS opponent,
                team1_score  AS team_score,
                team2_score  AS opponent_score,
                (winner_id = team1_id) AS won
            FROM matches
            WHERE team1_name ILIKE %s
            AND status = 'finished'
            AND winner_id IS NOT NULL

            UNION ALL

            SELECT
                COALESCE(begin_at, scheduled_at) AS match_date,
                team1_name   AS opponent,
                team2_score  AS team_score,
                team1_score  AS opponent_score,
                (winner_id = team2_id) AS won
            FROM matches
            WHERE team2_name ILIKE %s
            AND status = 'finished'
            AND winner_id IS NOT NULL
        ) AS team_matches
        ORDER BY match_date DESC
        LIMIT %s
    """, (team_name, team_name, last_n))

    rows    = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()

    if not rows:
        return None

    matches = [dict(zip(columns, row)) for row in rows]

    # Calculate form metrics
    wins         = sum(1 for m in matches if m["won"])
    losses       = len(matches) - wins
    win_rate     = round(wins / len(matches) * 100, 1)

    # Build result string like "W W L W L"
    form_string  = " ".join("W" if m["won"] else "L" for m in matches)

    # Current streak — count consecutive same results from most recent
    streak_type  = "W" if matches[0]["won"] else "L"
    streak_count = 0
    for m in matches:
        if (m["won"] and streak_type == "W") or (not m["won"] and streak_type == "L"):
            streak_count += 1
        else:
            break

    # Trend — compare first half vs second half win rate
    # "second half" here means older matches (end of list)
    half         = len(matches) // 2
    if half > 0:
        recent_wr  = sum(1 for m in matches[:half] if m["won"]) / half
        older_wr   = sum(1 for m in matches[half:] if m["won"]) / (len(matches) - half)
        if recent_wr > older_wr + 0.2:
            trend  = "📈 Improving"
        elif recent_wr < older_wr - 0.2:
            trend  = "📉 Declining"
        else:
            trend  = "➡️ Stable"
    else:
        trend      = "➡️ Stable"

    return {
        "team":          team_name,
        "matches_analysed": len(matches),
        "wins":          wins,
        "losses":        losses,
        "win_rate_pct":  win_rate,
        "form":          form_string,
        "streak":        f"{streak_count}{streak_type}",
        "trend":         trend,
        "recent_matches": matches
    }


def get_head_to_head(team_a: str, team_b: str):
    """
    Get historical head-to-head record between two teams.
    """
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COALESCE(begin_at, scheduled_at) AS match_date,
            name,
            team1_name,
            team1_score,
            team2_name,
            team2_score,
            winner_id,
            team1_id,
            team2_id,
            league_name
        FROM matches
        WHERE status = 'finished'
        AND winner_id IS NOT NULL
        AND (
            (team1_name ILIKE %s AND team2_name ILIKE %s)
            OR
            (team1_name ILIKE %s AND team2_name ILIKE %s)
        )
        ORDER BY match_date DESC
    """, (team_a, team_b, team_b, team_a))

    rows    = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()

    if not rows:
        return None

    matches  = [dict(zip(columns, row)) for row in rows]

    a_wins   = sum(1 for m in matches if
                   (m["team1_name"].lower() == team_a.lower() and m["winner_id"] == m["team1_id"]) or
                   (m["team2_name"].lower() == team_a.lower() and m["winner_id"] == m["team2_id"]))
    b_wins   = len(matches) - a_wins

    return {
        "team_a":        team_a,
        "team_b":        team_b,
        "total_matches": len(matches),
        "team_a_wins":   a_wins,
        "team_b_wins":   b_wins,
        "matches":       matches
    }


# Quick test when run directly
if __name__ == "__main__":
    import json

    print("=== ONIC Form ===")
    form = get_team_form("ONIC", last_n=10)
    if form:
        # Print everything except recent_matches for readability
        summary = {k: v for k, v in form.items() if k != "recent_matches"}
        print(json.dumps(summary, indent=2, default=str))
    else:
        print("Team not found")

    print("\n=== ONIC vs RRQ Hoshi H2H ===")
    h2h = get_head_to_head("ONIC", "RRQ Hoshi")
    if h2h:
        summary = {k: v for k, v in h2h.items() if k != "matches"}
        print(json.dumps(summary, indent=2, default=str))
    else:
        print("No matches found")

def get_draft_recommendation(enemy_heroes: list, role: str):
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT hero_name, role, tier, win_rate, pick_rate, ban_rate,
               strong_against, weak_against
        FROM heroes
        WHERE role ILIKE %s
        ORDER BY win_rate DESC
    """, (f"%{role}%",))

    rows    = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()

    if not rows:
        return []

    heroes           = [dict(zip(columns, row)) for row in rows]
    enemy_normalized = [e.strip().lower() for e in enemy_heroes]
    tier_points      = {"S": 3, "A": 2, "B": 1, "C": 0, "D": 0}
    scored           = []

    for hero in heroes:
        if not hero["win_rate"]:
            continue

        score        = hero["win_rate"]
        strong_list  = [s.strip().lower() for s in hero["strong_against"].split(",")] if hero["strong_against"] else []
        counter_hits = [e for e in enemy_normalized if any(e in s or s in e for s in strong_list)]
        counter_score = len(counter_hits) * 2
        score        += counter_score

        tier          = (hero["tier"] or "").strip().upper()
        score        += tier_points.get(tier, 0)

        weak_list    = [w.strip().lower() for w in hero["weak_against"].split(",")] if hero["weak_against"] else []
        weak_hits    = [e for e in enemy_normalized if any(e in w or w in e for w in weak_list)]
        score        -= len(weak_hits) * 1.5

        scored.append({
            "hero_name":     hero["hero_name"],
            "role":          hero["role"],
            "tier":          hero["tier"],
            "win_rate":      hero["win_rate"],
            "ban_rate":      hero["ban_rate"],
            "counters":      [e for e in enemy_heroes if e.strip().lower() in counter_hits],
            "weak_to":       [e for e in enemy_heroes if e.strip().lower() in weak_hits],
            "counter_score": counter_score,
            "tier_bonus":    tier_points.get(tier, 0),
            "total_score":   round(score, 2),
        })

    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return scored[:5]