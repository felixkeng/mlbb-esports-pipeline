import requests
from bs4 import BeautifulSoup
from database import get_connection, create_heroes_table

URL = "https://mlbbhub.com/statistics"

HEADERS = {
    # pretend to be a browser so the site doesn't block us
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def parse_percent(value: str) -> float:
    """Convert '56.17%' → 56.17"""
    try:
        return float(value.strip().replace("%", ""))
    except:
        return None

def scrape_hero_stats():
    """Scrape hero win/pick/ban rates from mlbbhub.com"""
    print("🌐 Fetching mlbbhub.com/statistics...")

    response = requests.get(URL, headers=HEADERS, timeout=15)

    if response.status_code != 200:
        print(f"❌ Failed to fetch page: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "lxml")

    # Find the stats table
    table = soup.find("table")
    if not table:
        print("❌ Could not find stats table on page")
        return []

    rows   = table.find("tbody").find_all("tr")
    heroes = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 8:
            continue

        # Extract hero name from the link text
        hero_link = cols[1].find("a")
        hero_name = hero_link.get_text(strip=True) if hero_link else cols[1].get_text(strip=True)

        # Role
        role = cols[2].get_text(strip=True)

        # Tier
        tier = cols[3].get_text(strip=True)

        # Win rate, pick rate, ban rate
        win_rate  = parse_percent(cols[4].get_text(strip=True))
        pick_rate = parse_percent(cols[6].get_text(strip=True))
        ban_rate  = parse_percent(cols[7].get_text(strip=True))

        # Strong against — get title attributes from hero icons
        strong_icons = cols[8].find_all(title=True) if len(cols) > 8 else []
        strong_against = ", ".join([
            icon["title"].split(" (")[0]  # remove the "(+0.1% WR)" part
            for icon in strong_icons
        ])

        # Weak against
        weak_icons = cols[9].find_all(title=True) if len(cols) > 9 else []
        weak_against = ", ".join([
            icon["title"].split(" (")[0]
            for icon in weak_icons
        ])

        heroes.append({
            "hero_name":      hero_name,
            "role":           role,
            "tier":           tier,
            "win_rate":       win_rate,
            "pick_rate":      pick_rate,
            "ban_rate":       ban_rate,
            "strong_against": strong_against,
            "weak_against":   weak_against,
        })

    print(f"✅ Scraped {len(heroes)} heroes")
    return heroes


def save_heroes(heroes):
    """Save hero stats to PostgreSQL, updating existing ones"""
    if not heroes:
        print("No hero data to save.")
        return

    conn   = get_connection()
    cursor = conn.cursor()

    saved   = 0
    updated = 0

    for h in heroes:
        # ON CONFLICT DO UPDATE = if hero already exists, update their stats
        # This is different from matches where we use DO NOTHING
        # Hero stats change every patch so we WANT to update them
        cursor.execute("""
            INSERT INTO heroes (
                hero_name, role, tier,
                win_rate, pick_rate, ban_rate,
                strong_against, weak_against,
                scraped_at
            ) VALUES (
                %(hero_name)s, %(role)s, %(tier)s,
                %(win_rate)s, %(pick_rate)s, %(ban_rate)s,
                %(strong_against)s, %(weak_against)s,
                NOW()
            )
            ON CONFLICT (hero_name)
            DO UPDATE SET
                role           = EXCLUDED.role,
                tier           = EXCLUDED.tier,
                win_rate       = EXCLUDED.win_rate,
                pick_rate      = EXCLUDED.pick_rate,
                ban_rate       = EXCLUDED.ban_rate,
                strong_against = EXCLUDED.strong_against,
                weak_against   = EXCLUDED.weak_against,
                scraped_at     = NOW()
        """, h)

        if cursor.rowcount == 1:
            saved += 1
        else:
            updated += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ Saved: {saved} new heroes | Updated: {updated} existing")


def run():
    print("🔄 Starting hero stats scrape...\n")
    create_heroes_table()
    heroes = scrape_hero_stats()
    save_heroes(heroes)
    print("\n✅ Done!")


if __name__ == "__main__":
    run()