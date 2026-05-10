# MLBB Esports Data Pipeline

An end-to-end data engineering portfolio project built with real Mobile Legends: Bang Bang esports data.

## Architecture
PandaScore API + mlbbhub.com
↓
collector.py + scraper.py   (ETL pipeline)
↓
PostgreSQL                (structured storage)
↓
FastAPI                   (REST API)
↓
static/index.html           (frontend UI)

## Features

- Ingests 1000+ real MLBB pro match results from PandaScore API
- Scrapes hero meta stats (win rate, pick rate, ban rate, counters) from mlbbhub.com
- Stores structured data in PostgreSQL with idempotent inserts
- Exposes 10+ REST API endpoints via FastAPI
- Draft recommendation engine — given enemy picks + your role, recommends best heroes by win rate, counter matchups, and tier

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /matches` | All matches with optional filters |
| `GET /matches/{id}` | Single match detail |
| `GET /standings` | Team win/loss records |
| `GET /tournaments` | All tournaments in database |
| `GET /form/{team}` | Team form — last N matches, streak, trend |
| `GET /h2h` | Head-to-head record between two teams |
| `GET /heroes` | All heroes with meta stats |
| `GET /heroes/top` | Top heroes by win rate, ban rate, pick rate |
| `GET /heroes/{name}` | Single hero detail |
| `GET /counters/{name}` | Hero counter matchups |
| `GET /recommend` | Draft recommendation engine |
| `GET /ui` | Frontend UI |

## Tech Stack

- **Python 3** — core language
- **PostgreSQL 15** — primary database
- **FastAPI + uvicorn** — REST API server
- **psycopg2** — PostgreSQL driver
- **requests** — API consumption
- **BeautifulSoup4** — web scraping
- **python-dotenv** — environment variable management

## Setup

1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/mlbb-esports-pipeline.git
cd mlbb-esports-pipeline
```

2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

3. Create `.env` file
PANDASCORE_TOKEN=your_token_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mlbb_esports
DB_USER=mlbb_user
DB_PASS=mlbb_pass

4. Set up PostgreSQL
```bash
psql postgres
CREATE DATABASE mlbb_esports;
CREATE USER mlbb_user WITH PASSWORD 'mlbb_pass';
GRANT ALL PRIVILEGES ON DATABASE mlbb_esports TO mlbb_user;
GRANT ALL ON SCHEMA public TO mlbb_user;
\q
```

5. Run setup and data collection
```bash
python3 database.py       # create tables
python3 collector.py      # fetch match data
python3 scraper.py        # scrape hero stats
python3 run.py            # start API server
```

6. Open the app
http://127.0.0.1:8000/ui