import requests
from config import PANDASCORE_TOKEN
from database import get_connection

BASE_URL = "https://api.pandascore.co"

HEADERS = {
    "Authorization": f"Bearer {PANDASCORE_TOKEN}"
}

def fetch_mlbb_matches(status="finished", max_pages=10):
    """
    Fetch MLBB matches from PandaScore.
    - status: 'finished', 'not_started', 'running'
    - max_pages: how many pages to fetch (100 matches per page = 1000 matches at max_pages=10)
    """
    all_matches = []

    for page in range(1, max_pages + 1):
        print(f"  📄 Fetching page {page}/{max_pages}...")

        params = {
            "status":   status,
            "sort":     "-begin_at",  # most recent first
            "per_page": 100,
            "page":     page
        }

        try:
            response = requests.get(
                f"{BASE_URL}/mlbb/matches",
                headers=HEADERS,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if not data:
                    print(f"  ✅ No more data at page {page}, stopping.")
                    break

                all_matches.extend(data)
                print(f"  ✅ Got {len(data)} matches (total so far: {len(all_matches)})")

            elif response.status_code == 429:
                print("  ⚠️ Rate limited — you've hit the free tier limit. Wait a minute and try again.")
                break

            else:
                print(f"  ❌ Failed at page {page}: {response.status_code} - {response.text}")
                break

        except Exception as e:
            print(f"  ❌ Error on page {page}: {e}")
            break

    return all_matches


def extract_match_data(match):
    """Flatten nested API response into a clean flat dictionary"""
    opponents = match.get("opponents", [])
    results   = match.get("results", [])

    team1  = opponents[0]["opponent"] if len(opponents) > 0 else {}
    team2  = opponents[1]["opponent"] if len(opponents) > 1 else {}
    score1 = results[0]["score"]      if len(results)   > 0 else None
    score2 = results[1]["score"]      if len(results)   > 1 else None

    return {
        "id":              match.get("id"),
        "name":            match.get("name"),
        "status":          match.get("status"),
        "match_type":      match.get("match_type"),
        "number_of_games": match.get("number_of_games"),
        "scheduled_at":    match.get("scheduled_at"),
        "begin_at":        match.get("begin_at"),
        "end_at":          match.get("end_at"),
        "league_name":     match.get("league",      {}).get("name"),
        "serie_name":      match.get("serie",       {}).get("full_name"),
        "tournament_name": match.get("tournament",  {}).get("name"),
        "team1_id":        team1.get("id"),
        "team1_name":      team1.get("name"),
        "team1_score":     score1,
        "team2_id":        team2.get("id"),
        "team2_name":      team2.get("name"),
        "team2_score":     score2,
        "winner_id":       match.get("winner_id"),
    }


def save_matches(matches):
    """Save matches to PostgreSQL, skipping duplicates"""
    if not matches:
        print("No matches to save.")
        return

    conn   = get_connection()
    cursor = conn.cursor()

    saved   = 0
    skipped = 0

    for match in matches:
        data = extract_match_data(match)

        cursor.execute("""
            INSERT INTO matches (
                id, name, status, match_type, number_of_games,
                scheduled_at, begin_at, end_at,
                league_name, serie_name, tournament_name,
                team1_id, team1_name, team1_score,
                team2_id, team2_name, team2_score,
                winner_id
            ) VALUES (
                %(id)s, %(name)s, %(status)s, %(match_type)s, %(number_of_games)s,
                %(scheduled_at)s, %(begin_at)s, %(end_at)s,
                %(league_name)s, %(serie_name)s, %(tournament_name)s,
                %(team1_id)s, %(team1_name)s, %(team1_score)s,
                %(team2_id)s, %(team2_name)s, %(team2_score)s,
                %(winner_id)s
            )
            ON CONFLICT (id) DO NOTHING
        """, data)

        if cursor.rowcount == 1:
            saved += 1
        else:
            skipped += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"  💾 Saved: {saved} new | Skipped: {skipped} duplicates")


def run():
    print("🔄 Starting MLBB backfill...\n")

    # Fetch finished matches (historical data)
    print("📦 Fetching FINISHED matches...")
    finished = fetch_mlbb_matches(status="finished", max_pages=10)
    print(f"\n→ Total finished matches fetched: {len(finished)}")
    save_matches(finished)

    # Also keep upcoming matches
    print("\n📦 Fetching UPCOMING matches...")
    upcoming = fetch_mlbb_matches(status="not_started", max_pages=2)
    print(f"\n→ Total upcoming matches fetched: {len(upcoming)}")
    save_matches(upcoming)

    print("\n✅ Backfill complete!")


if __name__ == "__main__":
    run()