#!/usr/bin/env python3
"""
WBC Dashboard - Day 2 Ingestion Pipeline
Single-file Python script to ingest MLB Stats API data into Supabase raw schema.
 
Flow:
1. Load .env.local from repo root → Connect to Supabase (SSL required)
2. Ingest players: /api/v1/sports/51/players → raw.players
3. Ingest games: per season — schedule → boxscores → single upsert
4. Smart skip: completed seasons skipped on rerun, current season always refreshed
 
Usage:
  python ingest.py --verify          # Check existing data counts/shapes
  python ingest.py --players-only    # Just players (fast, ~2s)
  python ingest.py --games-only      # Just games (~3min first run, ~30s after)
  python ingest.py                   # Full pipeline
"""
 
import os
import sys
import time
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
 
import requests
import psycopg
from dotenv import load_dotenv
 
# =============================================================================
# CONFIGURATION
# =============================================================================
 
WBC_SEASONS = [2006, 2009, 2013, 2017, 2023, 2026]
CURRENT_SEASON = max(WBC_SEASONS)  # Always re-fetched — may have unplayed/live games
MLB_API_BASE = "https://statsapi.mlb.com"
 
# =============================================================================
# ENVIRONMENT & DATABASE
# =============================================================================
 
def load_config() -> Dict[str, str]:
    """Load .env.local from repo root (two levels up from this script)."""
    script_dir = Path(__file__).resolve().parent
    env_path = (script_dir / ".." / ".." / ".env.local").resolve()
 
    if env_path.exists():
        load_dotenv(env_path)
        print(f"INFO: Loaded config from {env_path}")
    else:
        print(f"WARNING: {env_path} not found — relying on process environment")
 
    cfg = {
        "DB_HOST":     os.getenv("DB_HOST"),
        "DB_PORT":     os.getenv("DB_PORT", "5432"),
        "DB_NAME":     os.getenv("DB_NAME"),
        "DB_USER":     os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
    }
 
    missing = [k for k, v in cfg.items() if not v]
    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}")
        print("\nExpected in .env.local at repo root:")
        print("  DB_HOST=aws-0-us-east-1.pooler.supabase.com")
        print("  DB_PORT=5432")
        print("  DB_NAME=postgres")
        print("  DB_USER=postgres.yourprojectref")
        print("  DB_PASSWORD=your-supabase-db-password")
        sys.exit(1)
 
    return cfg
 
 
def get_db_connection(cfg: Dict[str, str]) -> psycopg.Connection:
    """Open a psycopg3 connection to Supabase with SSL and autocommit."""
    try:
        conn = psycopg.connect(
            host=cfg["DB_HOST"],
            port=cfg["DB_PORT"],
            dbname=cfg["DB_NAME"],
            user=cfg["DB_USER"],
            password=cfg["DB_PASSWORD"],
            connect_timeout=10,
            sslmode="require",
            autocommit=True,
        )
        print("INFO: Connected to Supabase ✓")
        return conn
    except Exception as e:
        print(f"ERROR: Database connection failed: {e}")
        sys.exit(1)
 
# =============================================================================
# HTTP CLIENT WITH RETRY
# =============================================================================
 
def get_with_retry(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    backoff: float = 1.0,
) -> Optional[Dict]:
    """GET with exponential backoff. Handles 429s, timeouts, transient errors."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            print(f"WARNING: {url} → HTTP {resp.status_code} (attempt {attempt}/{max_retries})")
        except requests.RequestException as e:
            print(f"WARNING: Request error for {url}: {e} (attempt {attempt}/{max_retries})")
 
        if attempt < max_retries:
            sleep_for = backoff * attempt
            print(f"INFO: Retrying in {sleep_for:.1f}s...")
            time.sleep(sleep_for)
 
    print(f"ERROR: Giving up on {url} after {max_retries} attempts")
    return None
 
# =============================================================================
# PLAYER INGESTION
# =============================================================================
 
def fetch_all_players() -> List[Dict[str, Any]]:
    """Fetch all international baseball players (sportId=51, no season filter)."""
    url = f"{MLB_API_BASE}/api/v1/sports/51/players"
    data = get_with_retry(url)
    if not data:
        return []
 
    players = data.get("people", [])
    print(f"INFO: Fetched {len(players):,} players from /sports/51/players")
    return players
 
 
def upsert_players(conn: psycopg.Connection, players: List[Dict[str, Any]]):
    """Upsert all players in a single executemany call."""
    if not players:
        print("INFO: No players to upsert")
        return
 
    rows = []
    skipped = 0
    for player in players:
        player_id = player.get("id")
        if player_id is None:
            skipped += 1
            continue
        rows.append((int(player_id), json.dumps(player)))
 
    if skipped:
        print(f"WARNING: Skipped {skipped} players with missing ID")
 
    sql = """
        INSERT INTO raw.players (player_id, data)
        VALUES (%s, %s)
        ON CONFLICT (player_id) DO UPDATE SET
            data        = EXCLUDED.data,
            ingested_at = NOW()
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
 
    print(f"INFO: Upserted {len(rows):,} players into raw.players")
 
 
def ingest_players(conn: psycopg.Connection):
    print("\n" + "=" * 60)
    print("INGESTING PLAYERS")
    print("=" * 60)
    players = fetch_all_players()
    upsert_players(conn, players)
 
# =============================================================================
# GAME INGESTION
# =============================================================================
 
def get_ingested_seasons(conn: psycopg.Connection) -> set:
    """Return set of seasons already fully ingested (excludes current season)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT data->>'season'
            FROM raw.games
            WHERE (data->>'season')::int != %s
        """, (CURRENT_SEASON,))
        return {row[0] for row in cur.fetchall()}
 
 
def fetch_schedule_for_season(season: int) -> List[int]:
    """Return list of gamePks for one WBC season."""
    data = get_with_retry(
        f"{MLB_API_BASE}/api/v1/schedule",
        params={"sportId": 51, "season": season, "gameType": "F,D,L,W"},
    )
    if not data:
        return []
 
    game_pks = [
        int(game["gamePk"])
        for date_entry in data.get("dates", [])
        for game in date_entry.get("games", [])
        if game.get("gamePk")
    ]
    print(f"  Found {len(game_pks)} games")
    return game_pks
 
 
def fetch_boxscores_for_season(season: int, game_pks: List[int]) -> List[Dict[str, Any]]:
    """Fetch all boxscores for a season. Injects gamePk and season at root."""
    boxscores = []
    total = len(game_pks)
    for i, pk in enumerate(game_pks, 1):
        print(f"  [{i}/{total}] fetching gamePk {pk}...")
        data = get_with_retry(f"{MLB_API_BASE}/api/v1/game/{pk}/boxscore")
        if data:
            data["gamePk"] = pk
            data["season"] = str(season)
            boxscores.append(data)
        else:
            print(f"  SKIP: gamePk {pk}")
 
    return boxscores
 
 
def upsert_games(conn: psycopg.Connection, games: List[Dict[str, Any]], season: int):
    """Upsert all games for a season in a single executemany call."""
    if not games:
        print(f"  No games to upsert for {season}")
        return
 
    rows = []
    skipped = 0
    for game in games:
        game_pk = game.get("gamePk")
        if game_pk is None:
            skipped += 1
            continue
        rows.append((int(game_pk), json.dumps(game)))
 
    if skipped:
        print(f"  WARNING: Skipped {skipped} games missing gamePk")
 
    sql = """
        INSERT INTO raw.games (game_pk, data)
        VALUES (%s, %s)
        ON CONFLICT (game_pk) DO UPDATE SET
            data        = EXCLUDED.data,
            ingested_at = NOW()
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
 
    print(f"  Upserted {len(rows)} games into raw.games ✓")
 
 
def ingest_games(conn: psycopg.Connection):
    """Per season: fetch schedule → fetch boxscores → upsert. Skip completed seasons."""
    print("\n" + "=" * 60)
    print("INGESTING GAMES")
    print("=" * 60)
 
    ingested_seasons = get_ingested_seasons(conn)
    if ingested_seasons:
        print(f"INFO: Skipping already-ingested seasons: {sorted(ingested_seasons)}")
 
    total_seasons = len(WBC_SEASONS)
    for season_num, season in enumerate(WBC_SEASONS, 1):
        print(f"\n--- Season {season} ({season_num}/{total_seasons}) ---")
 
        if str(season) in ingested_seasons:
            print(f"  SKIP: already ingested")
            continue
 
        game_pks = fetch_schedule_for_season(season)
        if not game_pks:
            print(f"  No games found — skipping")
            continue
 
        boxscores = fetch_boxscores_for_season(season, game_pks)
        upsert_games(conn, boxscores, season)
 
    print("\nINFO: All seasons processed ✓")
 
# =============================================================================
# VERIFICATION
# =============================================================================
 
def print_summary(conn: psycopg.Connection):
    """Print row counts and a breakdown of games by season."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM raw.players")
        players = cur.fetchone()[0]
 
        cur.execute("SELECT COUNT(*) FROM raw.games")
        games = cur.fetchone()[0]
 
        cur.execute("""
            SELECT data->>'season' AS season, COUNT(*) AS games
            FROM raw.games
            GROUP BY 1
            ORDER BY 1
        """)
        by_season = cur.fetchall()
 
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"  raw.players : {players:,} rows")
    print(f"  raw.games   : {games:,} rows")
    if by_season:
        print("\n  Games by season:")
        for season, count in by_season:
            print(f"    {season or 'unknown'}: {count} games")
    else:
        print("\n  No game data yet — run without --verify to ingest")
 
# =============================================================================
# ENTRY POINT
# =============================================================================
 
def main():
    parser = argparse.ArgumentParser(description="WBC Data Ingestion Pipeline")
    parser.add_argument("--players-only", action="store_true", help="Ingest players only")
    parser.add_argument("--games-only",   action="store_true", help="Ingest games only")
    parser.add_argument("--verify",       action="store_true", help="Print table counts, no ingestion")
    args = parser.parse_args()
 
    cfg  = load_config()
    conn = get_db_connection(cfg)
 
    try:
        if args.verify:
            print_summary(conn)
        elif args.players_only:
            ingest_players(conn)
            print_summary(conn)
        elif args.games_only:
            ingest_games(conn)
            print_summary(conn)
        else:
            ingest_players(conn)
            ingest_games(conn)
            print_summary(conn)
    finally:
        conn.close()
        print("\nINFO: Connection closed.")
 
 
if __name__ == "__main__":
    main()