#!/usr/bin/env python3
"""
WBC Dashboard - Ingestion Pipeline
Single-file Python script to ingest MLB Stats API data into Supabase raw schema.

Flow:
1. Load .env.local from repo root → Connect to Supabase (SSL required)
2. Ingest players: /api/v1/sports/51/players → raw.players
3. Ingest schedule + games per season:
   - Schedule API → raw.schedule (full game objects: status, scores, dates, gameType etc)
   - Boxscore API → raw.games (full boxscore blobs, gamePk + season injected only)
4. Smart skip: completed seasons skipped on rerun, current season always refreshed

raw.schedule and raw.games are joined in dbt on gamePk to produce analytics tables.

Usage:
  python ingest.py --verify          # Check existing data counts/shapes
  python ingest.py --players-only    # Just players (fast, ~2s)
  python ingest.py --games-only      # Just games + schedule (~3min first run)
  python ingest.py                   # Full pipeline
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

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
        print("Check .env.local at repo root.")
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
# SCHEDULE INGESTION
# =============================================================================

def fetch_schedule_for_season(season: int) -> List[Dict[str, Any]]:
    """
    Fetch schedule for one WBC season.
    Returns full game objects from the schedule API — not just gamePks.
    Each object contains: gamePk, gameType, officialDate, status, scores,
    venue, description, seriesDescription, dayNight, ifNecessary etc.
    """
    data = get_with_retry(
        f"{MLB_API_BASE}/api/v1/schedule",
        params={"sportId": 51, "season": season, "gameType": "F,D,L,W"},
    )
    if not data:
        return []

    games = [
        game
        for date_entry in data.get("dates", [])
        for game in date_entry.get("games", [])
        if game.get("gamePk")
    ]
    print(f"  Found {len(games)} games in schedule")
    return games


def upsert_schedule(conn: psycopg.Connection, schedule_games: List[Dict[str, Any]], season: int):
    """
    Upsert schedule game objects into raw.schedule.
    One row per gamePk — stores the full schedule API game object as-is.
    dbt joins this to raw.games on gamePk to enrich analytics tables.
    """
    if not schedule_games:
        print(f"  No schedule data to upsert for {season}")
        return

    rows = []
    skipped = 0
    for game in schedule_games:
        game_pk = game.get("gamePk")
        if game_pk is None:
            skipped += 1
            continue
        rows.append((int(game_pk), json.dumps(game)))

    if skipped:
        print(f"  WARNING: Skipped {skipped} schedule entries missing gamePk")

    sql = """
        INSERT INTO raw.schedule (game_pk, data)
        VALUES (%s, %s)
        ON CONFLICT (game_pk) DO UPDATE SET
            data        = EXCLUDED.data,
            ingested_at = NOW()
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)

    print(f"  Upserted {len(rows)} schedule entries into raw.schedule ✓")


def get_ingested_schedule_seasons(conn: psycopg.Connection) -> set:
    """Return set of seasons already in raw.schedule (excludes current season)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT data->>'season'
            FROM raw.schedule
            WHERE (data->>'season')::int != %s
        """, (CURRENT_SEASON,))
        return {row[0] for row in cur.fetchall()}

# =============================================================================
# GAME (BOXSCORE) INGESTION
# =============================================================================

def get_ingested_seasons(conn: psycopg.Connection) -> set:
    """Return set of seasons already fully ingested into raw.games (excludes current season)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT data->>'season'
            FROM raw.games
            WHERE (data->>'season')::int != %s
        """, (CURRENT_SEASON,))
        return {row[0] for row in cur.fetchall()}


def fetch_boxscores_for_season(
    season: int,
    game_pks: List[int],
) -> List[Dict[str, Any]]:
    """
    Fetch all boxscores for a season.
    Injects gamePk and season at root — these are the only fields injected.
    All other enrichment (dates, status, gameType, scores) lives in raw.schedule
    and is joined by dbt, not here.
    """
    boxscores = []
    total = len(game_pks)
    for i, pk in enumerate(game_pks, 1):
        print(f"  [{i}/{total}] fetching gamePk {pk}...")
        data = get_with_retry(f"{MLB_API_BASE}/api/v1/game/{pk}/boxscore")
        if data:
            data["gamePk"] = pk        # injected — not in boxscore response
            data["season"] = str(season)  # injected — not in boxscore response
            boxscores.append(data)
        else:
            print(f"  SKIP: gamePk {pk}")

    return boxscores


def upsert_games(conn: psycopg.Connection, games: List[Dict[str, Any]], season: int):
    """Upsert all boxscores for a season in a single executemany call."""
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

# =============================================================================
# COMBINED SEASON INGESTION
# =============================================================================

def ingest_games(conn: psycopg.Connection):
    """
    Per season: fetch schedule → upsert raw.schedule → fetch boxscores → upsert raw.games.
    One schedule API call per season feeds both tables.
    Smart skip: historical seasons skipped if already in both tables.
    Current season always re-fetched (live tournament, scores/status may have changed).
    """
    print("\n" + "=" * 60)
    print("INGESTING SCHEDULE + GAMES")
    print("=" * 60)

    ingested_game_seasons     = get_ingested_seasons(conn)
    ingested_schedule_seasons = get_ingested_schedule_seasons(conn)

    # A season is skippable only if both tables already have it
    fully_ingested = ingested_game_seasons & ingested_schedule_seasons
    if fully_ingested:
        print(f"INFO: Skipping already-ingested seasons: {sorted(fully_ingested)}")

    total_seasons = len(WBC_SEASONS)
    for season_num, season in enumerate(WBC_SEASONS, 1):
        print(f"\n--- Season {season} ({season_num}/{total_seasons}) ---")

        skip_games    = str(season) in ingested_game_seasons
        skip_schedule = str(season) in ingested_schedule_seasons

        if skip_games and skip_schedule:
            print(f"  SKIP: already ingested")
            continue

        # One schedule API call — used for both raw.schedule and gamePk extraction
        schedule_games = fetch_schedule_for_season(season)
        if not schedule_games:
            print(f"  No games found — skipping")
            continue

        # Upsert schedule data
        if not skip_schedule:
            upsert_schedule(conn, schedule_games, season)
        else:
            print(f"  SKIP raw.schedule: already ingested")

        # Extract gamePks and fetch boxscores
        if not skip_games:
            game_pks = [int(g["gamePk"]) for g in schedule_games]
            boxscores = fetch_boxscores_for_season(season, game_pks)
            upsert_games(conn, boxscores, season)
        else:
            print(f"  SKIP raw.games: already ingested")

    print("\nINFO: All seasons processed ✓")

# =============================================================================
# VERIFICATION
# =============================================================================

def print_summary(conn: psycopg.Connection):
    """Print row counts and breakdown by season for all raw tables."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM raw.players")
        players = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM raw.games")
        games = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM raw.schedule")
        schedule = cur.fetchone()[0]

        cur.execute("""
            SELECT data->>'season' AS season, COUNT(*) AS games
            FROM raw.games
            GROUP BY 1
            ORDER BY 1
        """)
        games_by_season = cur.fetchall()

        cur.execute("""
            SELECT data->>'season' AS season, COUNT(*) AS entries
            FROM raw.schedule
            GROUP BY 1
            ORDER BY 1
        """)
        schedule_by_season = cur.fetchall()

    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"  raw.players  : {players:,} rows")
    print(f"  raw.games    : {games:,} rows")
    print(f"  raw.schedule : {schedule:,} rows")

    if games_by_season:
        print("\n  raw.games by season:")
        for season, count in games_by_season:
            print(f"    {season or 'unknown'}: {count} games")

    if schedule_by_season:
        print("\n  raw.schedule by season:")
        for season, count in schedule_by_season:
            print(f"    {season or 'unknown'}: {count} entries")

        # Sanity check — counts should match between tables per season
        games_dict    = dict(games_by_season)
        schedule_dict = dict(schedule_by_season)
        mismatches = [
            s for s in schedule_dict
            if games_dict.get(s) != schedule_dict[s]
        ]
        if mismatches:
            print(f"\n  WARNING: Count mismatch between raw.games and raw.schedule for seasons: {mismatches}")
            print("  This is expected for the current season if games are scheduled but not yet played.")
        else:
            print("\n  raw.games and raw.schedule counts match ✓")

# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="WBC Data Ingestion Pipeline")
    parser.add_argument("--players-only", action="store_true", help="Ingest players only")
    parser.add_argument("--games-only",   action="store_true", help="Ingest schedule + games only")
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

def run():
    """
    Programmatic entry point for Dagster (bypasses argparse).
    Runs the full pipeline: players → schedule → games → summary.
    """
    cfg  = load_config()
    conn = get_db_connection(cfg)
    try:
        ingest_players(conn)
        ingest_games(conn)
        print_summary(conn)
    finally:
        conn.close()
        print("\nINFO: Connection closed.")


if __name__ == "__main__":
    main()