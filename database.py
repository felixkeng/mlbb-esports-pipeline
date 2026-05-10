import psycopg2
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS

def get_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        options="-c client_encoding=UTF8"  # ← add this
    )
    return conn

def create_tables():
    """Create all tables if they don't exist yet"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id              INTEGER PRIMARY KEY,
            name            TEXT,
            status          TEXT,
            match_type      TEXT,
            number_of_games INTEGER,
            scheduled_at    TIMESTAMP,
            begin_at        TIMESTAMP,
            end_at          TIMESTAMP,
            league_name     TEXT,
            serie_name      TEXT,
            tournament_name TEXT,
            team1_id        INTEGER,
            team1_name      TEXT,
            team1_score     INTEGER,
            team2_id        INTEGER,
            team2_name      TEXT,
            team2_score     INTEGER,
            winner_id       INTEGER,
            ingested_at     TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Tables created!")

def create_heroes_table():
    """Create heroes table for storing hero meta stats"""
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS heroes (
            id              SERIAL PRIMARY KEY,
            hero_name       TEXT UNIQUE NOT NULL,
            role            TEXT,
            tier            TEXT,
            win_rate        FLOAT,
            pick_rate       FLOAT,
            ban_rate        FLOAT,
            strong_against  TEXT,
            weak_against    TEXT,
            scraped_at      TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Heroes table created!")

# Run directly to test
if __name__ == "__main__":
    create_tables()
    create_heroes_table()