"""
embed.py — WBC Dashboard (Local Embeddings)
Converts analytics rows into natural language sentences,
embeds them via FREE SentenceTransformer (all-MiniLM-L6-v2),
and upserts into vectors.embeddings.

Run manually first to verify, then Dagster calls this via subprocess.
No API keys or rate limits!

Sentence sources (in run() order):
  1.  game_results            : 1 canonical sentence per game
  2.  standings               : 1 sentence per team per pool/round
  3.  player_tournament_stats : 1 sentence per player per season
  4.  player_game_stats       : 1 sentence per player per game (largest set, ~14k rows)
  5.  game_result_variants    : 2 alternate phrasings per game (beat / defeated)
                                 + championship/semifinal/quarterfinal bonus sentences
  6.  knockout_qa_pairs       : explicit Q&A pairs for every knockout round game
                                 championship=10, semifinal=6, quarterfinal=6
  7.  team_season_summary     : 1 sentence per team per season
                                 ← wins now counted from game_results, not standings
  8.  pool_winners            : 1 sentence per pool per season (new)
  9.  season_stat_leaders     : batting avg / HR / RBI / ERA leaders per season
  10. top_performer_per_game  : best hitter (RBI/HR) + best pitcher (K, min 1 IP) per game
  11. expanded_standings      : strengthened standings-related sentences (undefeated, etc.)

REMOVED from Day 8:
  - head_to_head             : dropped (low ROI, misleading multi-game aggregation)
  - game_result_variants v3  : dropped (redundant with canonical game_results sentence)

FIXED vs Day 8:
  - team_season_summary now counts wins from game_results (not standings),
    so knockout wins are included in the champion's record.
  - is_championship() guards against "Semifinals" false-positive (semi/quarter checked first).
  - All knockout SQL filters use NOT LIKE '%semi%' AND NOT LIKE '%quarter%' guards.
"""

import os
import sys
import logging
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import numpy as np
from pgvector.psycopg2 import register_vector
import json

# ── Load env ─────────────────────────────────────────────────────────────────
env_path = Path(__file__).resolve().parents[2] / ".env.local"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────────
EMBED_MODEL      = "sentence-transformers/all-MiniLM-L6-v2"  # 22MB, 384 dims
EMBED_BATCH_SIZE = 64   # Optimal for CPU memory (t2.small/t3.micro)
EMBED_DIM        = 384

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Database connection
# ─────────────────────────────────────────────────────────────────────────────

def get_connection() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        dbname=os.environ["DB_NAME"],
        port=5432,
        sslmode="require",
        options="-c search_path=analytics,vectors,public",
    )
    register_vector(conn)
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def fmt_date(d) -> str:
    """Cross-platform date string: 'March 18' (no zero-pad)."""
    return d.strftime("%B") + " " + str(d.day) if d else ""


def round_display(r) -> str:
    """Return pool_display if set, otherwise round_label."""
    return r["pool_display"] if r["pool_display"] else r["round_label"]


def is_championship(round_label: str) -> bool:
    label = (round_label or "").lower()
    if "semi" in label or "quarter" in label:
        return False
    return any(w in label for w in ("championship", "final", "gold"))


def is_semifinal(round_label: str) -> bool:
    return "semi" in (round_label or "").lower()


def is_quarterfinal(round_label: str) -> bool:
    return "quarter" in (round_label or "").lower()


def is_knockout(round_label: str) -> bool:
    return is_championship(round_label) or is_semifinal(round_label) or is_quarterfinal(round_label)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Game result sentences
# ─────────────────────────────────────────────────────────────────────────────

def build_game_result_sentences(conn) -> list[dict]:
    sql = """
        SELECT
            season, round_label, pool_display, official_date,
            venue_name, home_team_name, away_team_name,
            home_score, away_score, away_is_winner,
            winning_team_name, is_mercy_rule, game_pk, run_margin
        FROM analytics.game_results
        WHERE abstract_game_state = 'Final'
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            rd = round_display(r)
            round_str = f"{r['season']} WBC {rd}"
            losing_team = r["away_team_name"] if not r["away_is_winner"] else r["home_team_name"]
            mercy  = " (mercy rule)" if r["is_mercy_rule"] else ""
            venue  = f" at {r['venue_name']}" if r["venue_name"] else ""
            date_s = fmt_date(r["official_date"])
            ws, ls = (r["away_score"], r["home_score"]) if r["away_is_winner"] else (r["home_score"], r["away_score"])

            content = (
                f"In the {round_str}, {r['winning_team_name']} defeated "
                f"{losing_team} {ws}-{ls}{mercy} on {date_s}{venue}."
            )
            rows.append({
                "content": content,
                "metadata": {
                    "source": "game_results",
                    "game_pk": r["game_pk"],
                    "season": r["season"],
                    "round_label": r["round_label"],
                },
            })
    log.info(f"  game_results: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 1.1. Detailed game facts
# ─────────────────────────────────────────────────────────────────────────────
def build_game_detail_sentences(conn) -> list[dict]:
    sql = """
        SELECT
            season, round_label, pool_display, official_date,
            venue_name, home_team_name, away_team_name,
            home_score, away_score, away_is_winner,
            winning_team_name, is_mercy_rule, game_pk, run_margin
        FROM analytics.game_results
        WHERE abstract_game_state = 'Final'
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            season = r["season"]
            rl = r["round_label"] or ""
            rd = round_display(r)
            winner = r["winning_team_name"]
            loser = r["away_team_name"] if not r["away_is_winner"] else r["home_team_name"]
            ws, ls = (r["away_score"], r["home_score"]) if r["away_is_winner"] else (r["home_score"], r["away_score"])
            run_margin = r["run_margin"]
            venue_name = r["venue_name"]
            date_s = fmt_date(r["official_date"])

            meta = {
                "source": "game_detail_facts",
                "game_pk": r["game_pk"],
                "season": season,
                "round_label": rl,
            }

            total_score = ws + ls
            if total_score >= 15 and run_margin >= 5:
                rows.append({"content": f"The {season} WBC {rd} game between {r['away_team_name']} and {r['home_team_name']} on {date_s} was a high-scoring affair, with {winner} defeating {loser} {ws}-{ls}.", "metadata": meta})
                rows.append({"content": f"{winner} had a dominant {ws}-{ls} victory over {loser} in the {season} WBC {rd} on {date_s}, a game with a high total score and large run differential.", "metadata": meta})
            elif run_margin >= 7:
                rows.append({"content": f"{winner} blew out {loser} with a {ws}-{ls} victory in the {season} WBC {rd} on {date_s}.", "metadata": meta})
                rows.append({"content": f"The {season} WBC {rd} game on {date_s} saw a significant run differential of {run_margin} as {winner} defeated {loser} {ws}-{ls}.", "metadata": meta})

            if is_championship(rl) and venue_name:
                rows.append({"content": f"The {season} WBC Championship game, where {winner} defeated {loser} {ws}-{ls}, was held at {venue_name}.", "metadata": meta})
                rows.append({"content": f"{venue_name} hosted the {season} WBC Championship game.", "metadata": meta})
                rows.append({"content": f"Where was the {season} WBC Championship held? {venue_name}.", "metadata": meta})

    log.info(f"  game_detail_facts: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 2. Standings sentences
# ─────────────────────────────────────────────────────────────────────────────

def build_standings_sentences(conn) -> list[dict]:
    sql = """
        SELECT season, pool_display, team_name,
               pool_wins, pool_losses, pool_run_differential, pool_gp
        FROM analytics.standings
        ORDER BY season, pool_display, pool_wins DESC
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            rd  = r["pool_run_differential"]
            rds = f"+{rd}" if rd and rd > 0 else str(rd) if rd else "0"
            rec = f"{r['pool_wins']}-{r['pool_losses']}"
            content = f"In the {r['season']} WBC {r['pool_display']}, {r['team_name']} went {rec} with a {rds} run differential."
            rows.append({
                "content": content,
                "metadata": {
                    "source": "standings",
                    "season": r["season"],
                    "pool_display": r["pool_display"],
                    "team_name": r["team_name"],
                },
            })
    log.info(f"  standings: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 2.1 Expanded Standings (Strengthened Sentences)
# ─────────────────────────────────────────────────────────────────────────────

def build_expanded_standings_sentences(conn) -> list[dict]:
    sql = """
        SELECT season, pool_display, team_name,
               pool_wins, pool_losses, pool_run_differential
        FROM analytics.standings
        WHERE pool_gp > 0
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            season = r["season"]
            pool = r["pool_display"]
            team = r["team_name"]
            wins = r["pool_wins"]
            losses = r["pool_losses"]

            meta = {"source": "expanded_standings", "season": season, "pool_display": pool, "team_name": team}

            if losses == 0 and wins > 0:
                rows.append({"content": f"{team} went undefeated in the {season} WBC {pool} with a perfect {wins}-0 record.", "metadata": meta})
                rows.append({"content": f"Did {team} go undefeated in pool play? Yes, {team} finished {wins}-0 in the {season} {pool}.", "metadata": meta})
            
            if wins == 0 and losses > 0:
                rows.append({"content": f"{team} went winless in the {season} WBC {pool}, finishing with a 0-{losses} record.", "metadata": meta})

    log.info(f"  expanded_standings: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 3. Player tournament sentences
# ─────────────────────────────────────────────────────────────────────────────

def build_player_tournament_sentences(conn) -> list[dict]:
    sql = """
        SELECT season, full_name, represented_country,
               position_abbreviation, position_type, games_played,
               season_batting_avg, season_batting_h, season_batting_hr,
               season_batting_rbi, season_batting_ab,
               season_pitching_era, season_pitching_ip,
               season_pitching_so, season_pitching_w,
               season_pitching_sv, season_pitching_bf
        FROM analytics.player_tournament_stats
        WHERE games_played > 0
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            name    = r["full_name"] or "Unknown"
            country = r["represented_country"] or "Unknown"
            pos     = r["position_abbreviation"] or "?"
            season  = r["season"]
            gp      = r["games_played"]
            is_pitcher = r["position_type"] == "Pitcher" or (r["season_pitching_bf"] and r["season_pitching_bf"] > 0)

            if is_pitcher:
                try: era = f"{float(r['season_pitching_era']):.2f}"
                except: era = "N/A"
                ip  = f"{float(r['season_pitching_ip']):.1f}" if r["season_pitching_ip"] else "0.0"
                k   = r["season_pitching_so"] or 0
                w   = r["season_pitching_w"] or 0
                sv  = r["season_pitching_sv"] or 0
                content = f"In the {season} WBC, {name} ({country}, {pos}) had a {era} ERA with {k} strikeouts in {ip} IP ({w} W, {sv} SV) in {gp} games."
            else:
                try: avg = f".{int(min(float(r['season_batting_avg']), 0.999) * 1000):03d}"
                except: avg = ".000"
                hr  = r["season_batting_hr"] or 0
                rbi = r["season_batting_rbi"] or 0
                h   = r["season_batting_h"] or 0
                ab  = r["season_batting_ab"] or 0
                content = f"In the {season} WBC, {name} ({country}, {pos}) batted {avg} ({h}-for-{ab}) with {hr} HR and {rbi} RBI in {gp} games."

            rows.append({
                "content": content,
                "metadata": {"source": "player_tournament_stats", "season": season, "full_name": name, "represented_country": country},
            })
    log.info(f"  player_tournament_stats: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 3.1. Expanded player tournament sentences
# ─────────────────────────────────────────────────────────────────────────────
def build_expanded_player_tournament_sentences(conn) -> list[dict]:
    sql = """
        SELECT
            season, full_name, represented_country, birth_country, birth_date,
            team_name, season_batting_obp, season_batting_slg, season_batting_ops,
            season_pitching_era, season_pitching_ip, season_pitching_bb, season_pitching_h, games_played
        FROM analytics.player_tournament_stats
        WHERE games_played > 0
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            name = r["full_name"] or "Unknown"
            country = r["represented_country"] or "Unknown"
            birth_country = r["birth_country"] or "Unknown"
            season = r["season"]

            meta = {"source": "expanded_player_tournament_stats", "season": season, "full_name": name, "represented_country": country}

            if birth_country != "Unknown" and birth_country != country:
                rows.append({"content": f"{name}, born in {birth_country}, represented {country} in the {season} WBC.", "metadata": meta})
                rows.append({"content": f"Where was {name} born? {birth_country}.", "metadata": meta})

            if r["birth_date"]:
                age = season - r["birth_date"].year
                if age > 18:
                    rows.append({"content": f"{name} was approximately {age} years old during the {season} WBC.", "metadata": meta})

            if r["season_batting_ops"] and float(r["season_batting_ops"]) > 0:
                ops = f"{float(r['season_batting_ops']):.3f}"
                rows.append({"content": f"{name} ({country}) had an OPS of {ops} in the {season} WBC.", "metadata": meta})

            if r["season_pitching_ip"] and float(r["season_pitching_ip"]) > 0:
                whip = ( (r["season_pitching_bb"] or 0) + (r["season_pitching_h"] or 0) ) / float(r["season_pitching_ip"])
                rows.append({"content": f"{name} ({country}) had a WHIP of {whip:.2f} in the {season} WBC.", "metadata": meta})

    log.info(f"  expanded_player_tournament_stats: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 4. Player game sentences
# ─────────────────────────────────────────────────────────────────────────────

def build_player_game_sentences(conn) -> list[dict]:
    sql = """
        SELECT
            pgs.game_pk, pgs.season, pgs.official_date,
            pgs.full_name, pgs.represented_country,
            pgs.batting_ab, pgs.batting_h, pgs.batting_hr, pgs.batting_rbi,
            pgs.pitching_ip, pgs.pitching_er, pgs.pitching_so,
            pgs.pitching_w, pgs.pitching_l, pgs.pitching_sv,
            gr.round_label, gr.pool_display,
            gr.home_team_name, gr.away_team_name
        FROM analytics.player_game_stats pgs
        JOIN analytics.game_results gr ON gr.game_pk = pgs.game_pk
        WHERE gr.abstract_game_state = 'Final'
          AND (pgs.batting_ab > 0 OR pgs.pitching_ip > 0)
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            name      = r["full_name"] or "Unknown"
            country   = r["represented_country"] or "?"
            date_s    = fmt_date(r["official_date"])
            round_str = r["pool_display"] or r["round_label"] or "game"
            matchup   = f"{r['away_team_name']} vs {r['home_team_name']}"
            is_pitcher = r["pitching_ip"] and float(r["pitching_ip"]) > 0
            
            if is_pitcher:
                ip  = f"{float(r['pitching_ip']):.1f}"
                er  = r["pitching_er"] or 0
                k   = r["pitching_so"] or 0
                dec = ", W" if r["pitching_w"] else ", L" if r["pitching_l"] else ", SV" if r["pitching_sv"] else ""
                content = f"In a {r['season']} WBC {round_str} game on {date_s} ({matchup}), {name} ({country}) pitched {ip} IP, {er} ER, {k} K{dec}."
            else:
                h, ab, hr, ri = r["batting_h"] or 0, r["batting_ab"] or 0, r["batting_hr"] or 0, r["batting_rbi"] or 0
                suffix = f" with {hr} HR and {ri} RBI" if hr and ri else f" with {hr} HR" if hr else f" with {ri} RBI" if ri else ""
                content = f"In a {r['season']} WBC {round_str} game on {date_s} ({matchup}), {name} ({country}) went {h}-for-{ab}{suffix}."
            
            rows.append({
                "content": content,
                "metadata": {"source": "player_game_stats", "season": r["season"], "game_pk": r["game_pk"], "full_name": name},
            })
    log.info(f"  player_game_stats: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 4.1. Detailed player game facts
# ─────────────────────────────────────────────────────────────────────────────
def build_detailed_player_game_sentences(conn) -> list[dict]:
    sql = """
        SELECT
            pgs.game_pk, pgs.season, pgs.official_date,
            pgs.full_name, pgs.represented_country,
            pgs.batting_h, pgs.batting_hr, pgs.batting_rbi,
            pgs.pitching_so,
            gr.round_label, gr.pool_display, gr.home_team_name, gr.away_team_name
        FROM analytics.player_game_stats pgs
        JOIN analytics.game_results gr ON gr.game_pk = pgs.game_pk
        WHERE gr.abstract_game_state = 'Final'
          AND (pgs.batting_h >= 3 OR pgs.batting_hr >= 2 OR pgs.batting_rbi >= 4 OR pgs.pitching_so >= 10)
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            name      = r["full_name"] or "Unknown"
            country   = r["represented_country"] or "?"
            date_s    = fmt_date(r["official_date"])
            round_str = r["pool_display"] or r["round_label"] or "game"
            matchup   = f"{r['away_team_name']} vs {r['home_team_name']}"
            season    = r["season"]

            meta = {"source": "detailed_player_game_stats", "season": season, "game_pk": r["game_pk"], "full_name": name}

            if r["batting_h"] >= 3:
                rows.append({"content": f"{name} ({country}) had a 3-hit game in the {season} WBC {round_str} game on {date_s} ({matchup}).", "metadata": meta})
                rows.append({"content": f"Who had 3 hits on {date_s} in the {season} WBC? {name}.", "metadata": meta})
            if r["batting_hr"] >= 2:
                rows.append({"content": f"{name} ({country}) hit {r['batting_hr']} home runs in the {season} WBC {round_str} game on {date_s} ({matchup}).", "metadata": meta})
            if r["batting_rbi"] >= 4:
                rows.append({"content": f"{name} ({country}) drove in {r['batting_rbi']} runs in the {season} WBC {round_str} game on {date_s} ({matchup}).", "metadata": meta})
            if r["pitching_so"] >= 10:
                rows.append({"content": f"{name} ({country}) struck out {r['pitching_so']} batters in the {season} WBC {round_str} game on {date_s} ({matchup}).", "metadata": meta})

    log.info(f"  detailed_player_game_stats: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 5. Game result variants
# ─────────────────────────────────────────────────────────────────────────────

def build_game_result_variants(conn) -> list[dict]:
    sql = """
        SELECT
            season, round_label, pool_display,
            home_team_name, away_team_name,
            home_score, away_score, away_is_winner,
            winning_team_name, game_pk
        FROM analytics.game_results
        WHERE abstract_game_state = 'Final'
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            winner  = r["winning_team_name"]
            loser   = r["away_team_name"] if not r["away_is_winner"] else r["home_team_name"]
            season  = r["season"]
            rl      = r["round_label"] or ""
            rd      = round_display(r)
            ws, ls  = (r["away_score"], r["home_score"]) if r["away_is_winner"] else (r["home_score"], r["away_score"])

            meta = {"source": "game_result_variants", "game_pk": r["game_pk"], "season": season, "round_label": rl}

            rows.append({"content": f"{winner} beat {loser} {ws}-{ls} in the {season} WBC {rd}.", "metadata": meta})
            rows.append({"content": f"In the {season} WBC {rd}, {winner} defeated {loser} {ws}-{ls}.", "metadata": meta})

            if is_championship(rl):
                rows.append({"content": f"{winner} won the {season} World Baseball Classic championship, defeating {loser} {ws}-{ls} in the final.", "metadata": meta})
                rows.append({"content": f"The {season} WBC champion was {winner}. They defeated {loser} {ws}-{ls}.", "metadata": meta})
                rows.append({"content": f"{winner} is the {season} WBC title holder, having beaten {loser} {ws}-{ls}.", "metadata": meta})
            elif is_semifinal(rl):
                rows.append({"content": f"In the {season} WBC semifinals, {winner} eliminated {loser} {ws}-{ls} to advance to the championship.", "metadata": meta})
            elif is_quarterfinal(rl):
                rows.append({"content": f"In the {season} WBC quarterfinals, {winner} knocked out {loser} {ws}-{ls}.", "metadata": meta})

    log.info(f"  game_result_variants: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 6. Knockout Q&A pairs
# ─────────────────────────────────────────────────────────────────────────────

def build_knockout_qa_pairs(conn) -> list[dict]:
    sql = """
        SELECT
            season, round_label, pool_display,
            home_team_name, away_team_name,
            home_score, away_score, away_is_winner,
            winning_team_name, game_pk
        FROM analytics.game_results
        WHERE abstract_game_state = 'Final'
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
          AND (
                LOWER(round_label) LIKE '%championship%' OR
                LOWER(round_label) LIKE '%final%' OR
                LOWER(round_label) LIKE '%semi%' OR
                LOWER(round_label) LIKE '%quarter%'
          )
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            winner = r["winning_team_name"]
            loser  = r["away_team_name"] if not r["away_is_winner"] else r["home_team_name"]
            season = r["season"]
            rl     = r["round_label"] or ""
            ws, ls = (r["away_score"], r["home_score"]) if r["away_is_winner"] else (r["home_score"], r["away_score"])
            
            meta = {"source": "knockout_qa_pairs", "game_pk": r["game_pk"], "season": season, "round_label": rl}

            if is_championship(rl):
                qas = [
                    (f"Who won the {season} WBC?", f"{winner}."),
                    (f"Who won the {season} World Baseball Classic?", f"{winner} won the {season} WBC."),
                    (f"Did {winner} win the {season} WBC?", f"Yes, {winner} won the {season} World Baseball Classic."),
                    (f"Who won the championship in {season}?", f"{winner} won the {season} championship by defeating {loser}."),
                    (f"Who played in the {season} WBC final?", f"{winner} and {loser} played in the {season} WBC final."),
                    (f"What was the score of the {season} WBC final?", f"{winner} defeated {loser} {ws}-{ls}."),
                    (f"Who did {winner} beat to win the {season} WBC?", f"{winner} beat {loser} {ws}-{ls}."),
                    (f"Did {loser} win the {season} WBC?", f"No, {loser} lost to {winner} {ws}-{ls} in the {season} WBC final."),
                    (f"Who was the runner up in the {season} WBC?", f"{loser} was the runner up in the {season} WBC."),
                    (f"How many runs did {winner} score in the {season} WBC final?", f"{winner} scored {ws} runs in the {season} final.")
                ]
            elif is_semifinal(rl):
                qas = [
                    (f"Who won the {season} WBC semifinal between {winner} and {loser}?", f"{winner} won {ws}-{ls}."),
                    (f"Did {winner} make it to the {season} WBC final?", f"Yes, {winner} advanced by beating {loser} in the semifinals."),
                    (f"Who was eliminated in the {season} WBC semifinals by {winner}?", f"{loser} was eliminated by {winner}."),
                    (f"What was the score of the {season} semifinal game where {winner} played {loser}?", f"{winner} won {ws}-{ls}."),
                    (f"Who did {winner} defeat in the {season} semifinals?", f"{winner} defeated {loser}."),
                    (f"Did {loser} advance to the {season} final?", f"No, {loser} was eliminated by {winner} in the semifinals.")
                ]
            elif is_quarterfinal(rl):
                qas = [
                    (f"Who won the {season} WBC quarterfinal between {winner} and {loser}?", f"{winner} won {ws}-{ls}."),
                    (f"Who did {winner} beat in the {season} WBC quarterfinals?", f"{winner} defeated {loser}."),
                    (f"What was the score of the {winner} vs {loser} {season} quarterfinal?", f"The score was {winner} {ws}, {loser} {ls}."),
                    (f"Did {winner} advance to the {season} semifinals?", f"Yes, {winner} advanced by beating {loser} in the quarterfinals."),
                    (f"Was {loser} eliminated in the {season} quarterfinals?", f"Yes, {loser} was eliminated by {winner}."),
                    (f"Who knocked out {loser} in the {season} WBC quarterfinals?", f"{winner} knocked out {loser} {ws}-{ls}.")
                ]
            else:
                qas = []

            for q, a in qas:
                rows.append({"content": f"Q: {q} A: {a}", "metadata": meta})

    log.info(f"  knockout_qa_pairs: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 7. Team season summary
# ─────────────────────────────────────────────────────────────────────────────

def build_team_season_summary(conn) -> list[dict]:
    sql = """
        WITH team_games AS (
            SELECT season, winning_team_name AS team, 1 as win, 0 as loss
            FROM analytics.game_results WHERE abstract_game_state = 'Final'
            UNION ALL
            SELECT season,
                   CASE WHEN away_is_winner THEN home_team_name ELSE away_team_name END AS team,
                   0 as win, 1 as loss
            FROM analytics.game_results WHERE abstract_game_state = 'Final'
        )
        SELECT season, team, SUM(win) as total_wins, SUM(loss) as total_losses
        FROM team_games
        GROUP BY season, team
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            season = r["season"]
            team = r["team"]
            w, l = r["total_wins"], r["total_losses"]
            rows.append({
                "content": f"Overall, {team} finished the {season} WBC tournament with a record of {w} wins and {l} losses.",
                "metadata": {"source": "team_season_summary", "season": season, "team_name": team}
            })
    log.info(f"  team_season_summary: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 8. Pool winners
# ─────────────────────────────────────────────────────────────────────────────

def build_pool_winners(conn) -> list[dict]:
    sql = """
        WITH ranked_pools AS (
            SELECT season, pool_display, team_name, pool_wins, pool_losses,
                   ROW_NUMBER() OVER(PARTITION BY season, pool_display ORDER BY pool_wins DESC, pool_run_differential DESC) as rnk
            FROM analytics.standings
            WHERE pool_gp > 0
        )
        SELECT season, pool_display, team_name, pool_wins, pool_losses
        FROM ranked_pools
        WHERE rnk = 1 AND pool_display IS NOT NULL AND LOWER(pool_display) LIKE '%pool%'
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            season, pool, team = r["season"], r["pool_display"], r["team_name"]
            w, l = r["pool_wins"], r["pool_losses"]
            rows.append({
                "content": f"{team} won the {season} WBC {pool} with a record of {w}-{l}.",
                "metadata": {"source": "pool_winners", "season": season, "pool_display": pool, "team_name": team}
            })
    log.info(f"  pool_winners: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 9. Season stat leaders
# ─────────────────────────────────────────────────────────────────────────────

def build_season_stat_leaders(conn) -> list[dict]:
    # Simplified approach to fetch extreme maxes.
    sql = """
        SELECT season,
               full_name,
               represented_country,
               season_batting_hr,
               season_batting_rbi,
               season_pitching_so
        FROM analytics.player_tournament_stats
        WHERE games_played > 0
    """
    rows = []
    
    # We will process maxes in Python to avoid overly complex SQL window functions 
    # across multiple distinct metrics.
    season_data = {}
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            s = r["season"]
            if s not in season_data:
                season_data[s] = {"hr": [], "rbi": [], "so": []}
            
            hr = r["season_batting_hr"] or 0
            rbi = r["season_batting_rbi"] or 0
            so = r["season_pitching_so"] or 0
            name_info = f"{r['full_name']} ({r['represented_country']})"
            
            season_data[s]["hr"].append((hr, name_info))
            season_data[s]["rbi"].append((rbi, name_info))
            season_data[s]["so"].append((so, name_info))

    for s, stats in season_data.items():
        meta = {"source": "season_stat_leaders", "season": s}
        
        # HR Leader
        stats["hr"].sort(key=lambda x: x[0], reverse=True)
        if stats["hr"] and stats["hr"][0][0] > 0:
            top_hr, top_hr_name = stats["hr"][0]
            rows.append({"content": f"{top_hr_name} led the {s} WBC in home runs with {top_hr} HR.", "metadata": meta})

        # RBI Leader
        stats["rbi"].sort(key=lambda x: x[0], reverse=True)
        if stats["rbi"] and stats["rbi"][0][0] > 0:
            top_rbi, top_rbi_name = stats["rbi"][0]
            rows.append({"content": f"{top_rbi_name} led the {s} WBC in runs batted in with {top_rbi} RBI.", "metadata": meta})

        # SO Leader
        stats["so"].sort(key=lambda x: x[0], reverse=True)
        if stats["so"] and stats["so"][0][0] > 0:
            top_so, top_so_name = stats["so"][0]
            rows.append({"content": f"{top_so_name} led the {s} WBC in strikeouts with {top_so} K.", "metadata": meta})

    log.info(f"  season_stat_leaders: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 10. Top performer per game
# ─────────────────────────────────────────────────────────────────────────────

def build_top_performer_per_game(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, full_name, represented_country, 
               batting_rbi, pitching_so,
               ROW_NUMBER() OVER(PARTITION BY game_pk ORDER BY batting_rbi DESC NULLS LAST) as rbi_rnk,
               ROW_NUMBER() OVER(PARTITION BY game_pk ORDER BY pitching_so DESC NULLS LAST) as so_rnk
        FROM analytics.player_game_stats
        WHERE batting_rbi > 0 OR pitching_so > 0
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            game_pk = r["game_pk"]
            season = r["season"]
            name = f"{r['full_name']} ({r['represented_country']})"
            meta = {"source": "top_performer_per_game", "season": season, "game_pk": game_pk}

            if r["rbi_rnk"] == 1 and r["batting_rbi"] and r["batting_rbi"] >= 3:
                rows.append({"content": f"{name} was a top offensive performer in their {season} WBC game, driving in {r['batting_rbi']} runs.", "metadata": meta})
            
            if r["so_rnk"] == 1 and r["pitching_so"] and r["pitching_so"] >= 5:
                rows.append({"content": f"{name} was a top pitching performer in their {season} WBC game, striking out {r['pitching_so']} batters.", "metadata": meta})

    log.info(f"  top_performer_per_game: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RUN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run():
    """Main execution entrypoint for building, embedding, and saving vectors."""
    log.info("Starting WBC embedding pipeline...")
    conn = get_connection()
    
    sentences = []
    
    # 1. Base Game Data
    sentences.extend(build_game_result_sentences(conn))
    sentences.extend(build_game_detail_sentences(conn))
    
    # 2. Standings Data
    sentences.extend(build_standings_sentences(conn))
    sentences.extend(build_expanded_standings_sentences(conn))
    
    # 3. Tournament Player Data
    sentences.extend(build_player_tournament_sentences(conn))
    sentences.extend(build_expanded_player_tournament_sentences(conn))
    
    # 4. Game Player Data
    sentences.extend(build_player_game_sentences(conn))
    sentences.extend(build_detailed_player_game_sentences(conn))
    
    # 5. Variants & Q&A
    sentences.extend(build_game_result_variants(conn))
    sentences.extend(build_knockout_qa_pairs(conn))
    
    # 6. Summaries & Leaders
    sentences.extend(build_team_season_summary(conn))
    sentences.extend(build_pool_winners(conn))
    sentences.extend(build_season_stat_leaders(conn))
    sentences.extend(build_top_performer_per_game(conn))

    total = len(sentences)
    log.info(f"Total sentences extracted: {total}")

    if total == 0:
        log.warning("No sentences generated. Exiting.")
        conn.close()
        return

    log.info(f"Loading SentenceTransformer model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)

    with conn.cursor() as cur:
        # Prepare table
        log.info("Preparing vectors.embeddings table...")
        cur.execute("""
            CREATE SCHEMA IF NOT EXISTS vectors;
            CREATE TABLE IF NOT EXISTS vectors.embeddings (
                id BIGSERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                embedding vector(384),
                metadata JSONB
            );
        """)
        # We truncate to replace all data completely for the pipeline run.
        cur.execute("TRUNCATE vectors.embeddings;") 
        
        log.info(f"Embedding and inserting in batches of {EMBED_BATCH_SIZE}...")
        
        for i in range(0, total, EMBED_BATCH_SIZE):
            batch = sentences[i:i+EMBED_BATCH_SIZE]
            contents = [b["content"] for b in batch]
            metadatas = [json.dumps(b["metadata"]) for b in batch]

            # Generate vectors
            embeddings = model.encode(contents, normalize_embeddings=True)

            # Insert
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO vectors.embeddings (content, metadata, embedding) VALUES %s",
                [(c, m, e.tolist()) for c, m, e in zip(contents, metadatas, embeddings)]
            )
            
            if (i + len(batch)) % 1000 == 0 or (i + len(batch)) == total:
                log.info(f"  Inserted {i + len(batch)} / {total} records")

        conn.commit()
        
    conn.close()
    log.info("Embedding pipeline completed successfully!")


if __name__ == "__main__":
    run()