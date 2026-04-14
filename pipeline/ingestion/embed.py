"""
embed.py — WBC Dashboard RAG Embeddings
========================================
Converts all analytics tables into natural-language sentences,
embeds them with SentenceTransformer (all-MiniLM-L6-v2, free/local),
and upserts into vectors.embeddings.

DATA SOURCES — exact schema.table names and grains:
  wbc_mart.app_game_results        grain: 1 row per completed game
  wbc_mart.app_pool_standings      grain: 1 row per team per pool per season
  wbc_mart.app_player_season_stats grain: 1 row per player per season
  wbc_mart.app_game_detail         grain: 1 row per player per game

SENTENCE BUILDERS (in run() order):
  1.  game_result_sentences          canonical result sentence per game
  2.  game_result_variants           alternate phrasings + knockout context
  3.  knockout_qa_pairs              explicit Q&A for championship/semi/quarterfinal
  4.  mercy_rule_facts               mercy-rule game facts + Q&A
  5.  one_run_game_facts             one-run game facts
  6.  high_scoring_blowout_facts     blowout / high-total game facts
  7.  venue_facts                    venue sentences, championship venue Q&A
  8.  inning_scoring_facts           big innings (3+ runs), walk-offs, extra innings
  9.  rhe_facts                      team hits and errors box line per game
  10. pool_standings_sentences       record, run diff, runs scored/allowed per team
  11. pool_standings_expanded        undefeated / winless edge cases
  12. pool_winners                   who won each pool + Q&A
  13. team_season_record             overall W-L across all rounds per team per season
  14. player_season_sentences        core batting or pitching line per player per season
  15. player_season_adv_batting      OBP/SLG/OPS/ISO/BABIP/K%/BB% per season
  16. player_season_adv_pitching     ERA/WHIP/K9/BB9/W-L/SV/GS per season
  17. player_season_xbh_sb           stolen bases per season
  18. player_season_leaders          per-season stat leaders
  19. player_bio_facts               height, weight, handedness, position, debut, birthplace
  20. player_game_batting_sentences  per-game batting line per player
  21. player_game_pitching_sentences per-game pitching line per player
  22. player_game_notable_batting    standout games: 3H / 2HR / 4RBI / 2SB / 3BB
  23. player_game_notable_pitching   standout games: 10K / 7+IP / 0ER
  24. player_game_extra_batting      doubles, triples, HBP, GIDP in game
  25. team_game_batting_box          team-level hits/HR/BB/SO/SB per game
  26. team_game_pitching_box         team-level pitch count/K/BB/ER/WP per game
  27. team_game_fielding_facts       team errors / passed balls per game
  28. player_career_sentences        career totals for multi-season players
"""

import json
import logging
import os
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

# ── env ───────────────────────────────────────────────────────────────────────
env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(dotenv_path=env_path if env_path.exists() else None)

# ── config ────────────────────────────────────────────────────────────────────
EMBED_MODEL      = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_BATCH_SIZE = 64
EMBED_DIM        = 384

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DB connection
# ─────────────────────────────────────────────────────────────────────────────

def get_connection():
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        dbname=os.environ["DB_NAME"],
        port=5432,
        sslmode="require",
        options="-c search_path=wbc_mart,vectors,public",
    )
    register_vector(conn)
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def fmt_date(d) -> str:
    return (d.strftime("%B") + " " + str(d.day)) if d else ""


def fmt_avg(val) -> str:
    try:
        return f".{int(min(float(val), 0.9999) * 1000):03d}"
    except (TypeError, ValueError):
        return ".000"


def fmt_era(val) -> str:
    try:
        return f"{float(val):.2f}"
    except (TypeError, ValueError):
        return "N/A"


def fmt_ip(val) -> str:
    try:
        return f"{float(val):.1f}"
    except (TypeError, ValueError):
        return "0.0"


def is_championship(round_label: str) -> bool:
    label = (round_label or "").lower()
    if "semi" in label or "quarter" in label:
        return False
    return any(w in label for w in ("championship", "final", "gold"))


def is_semifinal(round_label: str) -> bool:
    return "semi" in (round_label or "").lower()


def is_quarterfinal(round_label: str) -> bool:
    return "quarter" in (round_label or "").lower()


def winner_loser(r):
    """Return (winner_name, loser_name, winner_score, loser_score)."""
    if r["away_is_winner"]:
        return r["away_team_name"], r["home_team_name"], r["away_score"], r["home_score"]
    return r["home_team_name"], r["away_team_name"], r["home_score"], r["away_score"]


def fetch(conn, sql) -> list:
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        return cur.fetchall()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Canonical game result sentences
#    Source: wbc_mart.app_game_results
#    Columns: game_pk, season, official_date, round_label, pool_group,
#             away_team_name, home_team_name, away_score, home_score,
#             away_is_winner, is_mercy_rule, venue_name, run_margin, total_runs
# ─────────────────────────────────────────────────────────────────────────────

def build_game_result_sentences(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, official_date, round_label, pool_group,
               away_team_name, home_team_name,
               away_score, home_score, away_is_winner,
               is_mercy_rule, venue_name, run_margin, total_runs
        FROM wbc_mart.app_game_results
        WHERE away_score IS NOT NULL AND home_score IS NOT NULL
    """
    rows = []
    for r in fetch(conn, sql):
        winner, loser, ws, ls = winner_loser(r)
        rd    = r["pool_group"] or r["round_label"] or "game"
        mercy = " (mercy rule)" if r["is_mercy_rule"] else ""
        venue = f" at {r['venue_name']}" if r["venue_name"] else ""
        date  = fmt_date(r["official_date"])
        meta  = {"source": "game_results", "game_pk": r["game_pk"],
                 "season": r["season"], "round_label": r["round_label"]}
        rows.append({
            "content": f"In the {r['season']} WBC {rd}, {winner} defeated {loser} {ws}-{ls}{mercy} on {date}{venue}.",
            "metadata": meta,
        })
    log.info(f"  game_result_sentences: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 2. Game result variants (alternate phrasings + knockout context)
#    Source: wbc_mart.app_game_results
# ─────────────────────────────────────────────────────────────────────────────

def build_game_result_variants(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, official_date, round_label, pool_group,
               away_team_name, home_team_name,
               away_score, home_score, away_is_winner
        FROM wbc_mart.app_game_results
        WHERE away_score IS NOT NULL AND home_score IS NOT NULL
    """
    rows = []
    for r in fetch(conn, sql):
        winner, loser, ws, ls = winner_loser(r)
        rd   = r["pool_group"] or r["round_label"] or "game"
        rl   = r["round_label"] or ""
        s    = r["season"]
        meta = {"source": "game_result_variants", "game_pk": r["game_pk"],
                "season": s, "round_label": rl}

        rows.append({"content": f"{winner} beat {loser} {ws}-{ls} in the {s} WBC {rd}.", "metadata": meta})
        rows.append({"content": f"In the {s} WBC {rd}, {winner} beat {loser} by a score of {ws}-{ls}.", "metadata": meta})

        if is_championship(rl):
            rows.append({"content": f"{winner} won the {s} World Baseball Classic, defeating {loser} {ws}-{ls} in the championship game.", "metadata": meta})
            rows.append({"content": f"The {s} WBC champion is {winner}. They beat {loser} {ws}-{ls}.", "metadata": meta})
            rows.append({"content": f"{winner} is the {s} WBC champion, having defeated {loser} {ws}-{ls} in the final.", "metadata": meta})
            rows.append({"content": f"Who won the {s} WBC? {winner}.", "metadata": meta})
        elif is_semifinal(rl):
            rows.append({"content": f"In the {s} WBC semifinals, {winner} eliminated {loser} {ws}-{ls} to advance to the championship.", "metadata": meta})
            rows.append({"content": f"{winner} beat {loser} {ws}-{ls} in the {s} WBC semifinals.", "metadata": meta})
        elif is_quarterfinal(rl):
            rows.append({"content": f"In the {s} WBC quarterfinals, {winner} knocked out {loser} {ws}-{ls}.", "metadata": meta})
            rows.append({"content": f"{winner} beat {loser} {ws}-{ls} in the {s} WBC quarterfinals.", "metadata": meta})

    log.info(f"  game_result_variants: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 3. Knockout Q&A pairs
#    Source: wbc_mart.app_game_results
# ─────────────────────────────────────────────────────────────────────────────

def build_knockout_qa_pairs(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, round_label, pool_group,
               away_team_name, home_team_name,
               away_score, home_score, away_is_winner
        FROM wbc_mart.app_game_results
        WHERE away_score IS NOT NULL AND home_score IS NOT NULL
          AND (
            LOWER(round_label) LIKE '%championship%' OR
            LOWER(round_label) LIKE '%final%'        OR
            LOWER(round_label) LIKE '%semi%'         OR
            LOWER(round_label) LIKE '%quarter%'
          )
    """
    rows = []
    for r in fetch(conn, sql):
        winner, loser, ws, ls = winner_loser(r)
        rl   = r["round_label"] or ""
        s    = r["season"]
        meta = {"source": "knockout_qa_pairs", "game_pk": r["game_pk"],
                "season": s, "round_label": rl}

        if is_championship(rl):
            qas = [
                (f"Who won the {s} WBC?",
                 f"{winner} won the {s} WBC."),
                (f"Who won the {s} World Baseball Classic?",
                 f"{winner} won the {s} World Baseball Classic."),
                (f"Did {winner} win the {s} WBC?",
                 f"Yes, {winner} won the {s} WBC, defeating {loser} {ws}-{ls}."),
                (f"Did {loser} win the {s} WBC?",
                 f"No, {loser} lost to {winner} {ws}-{ls} in the {s} WBC final."),
                (f"Who played in the {s} WBC final?",
                 f"{winner} and {loser} played in the {s} WBC championship game."),
                (f"What was the score of the {s} WBC final?",
                 f"{winner} defeated {loser} {ws}-{ls}."),
                (f"Who did {winner} beat to win the {s} WBC?",
                 f"{winner} beat {loser} {ws}-{ls} in the championship game."),
                (f"Who was the runner-up in the {s} WBC?",
                 f"{loser} was the runner-up in the {s} WBC, losing to {winner} {ws}-{ls}."),
                (f"How many runs did {winner} score in the {s} WBC final?",
                 f"{winner} scored {ws} runs in the {s} WBC final."),
                (f"How many runs did {loser} score in the {s} WBC final?",
                 f"{loser} scored {ls} runs in the {s} WBC final."),
            ]
        elif is_semifinal(rl):
            qas = [
                (f"Who won the {s} WBC semifinal between {winner} and {loser}?",
                 f"{winner} won {ws}-{ls}."),
                (f"Did {winner} advance to the {s} WBC final?",
                 f"Yes, {winner} beat {loser} {ws}-{ls} in the semifinals."),
                (f"Who eliminated {loser} in the {s} WBC semifinals?",
                 f"{winner} eliminated {loser} {ws}-{ls}."),
                (f"Did {loser} make the {s} WBC final?",
                 f"No, {loser} was eliminated by {winner} {ws}-{ls} in the semifinals."),
                (f"What was the score of the {s} WBC semifinal between {winner} and {loser}?",
                 f"{winner} won {ws}-{ls}."),
            ]
        elif is_quarterfinal(rl):
            qas = [
                (f"Who won the {s} WBC quarterfinal between {winner} and {loser}?",
                 f"{winner} won {ws}-{ls}."),
                (f"Who did {winner} beat in the {s} WBC quarterfinals?",
                 f"{winner} defeated {loser} {ws}-{ls}."),
                (f"Was {loser} eliminated in the {s} WBC quarterfinals?",
                 f"Yes, {loser} was knocked out by {winner} {ws}-{ls}."),
                (f"Did {winner} advance to the {s} WBC semifinals?",
                 f"Yes, {winner} beat {loser} {ws}-{ls} in the quarterfinals."),
                (f"What was the score of the {winner} vs {loser} {s} quarterfinal?",
                 f"{winner} {ws}, {loser} {ls}."),
            ]
        else:
            qas = []

        for q, a in qas:
            rows.append({"content": f"Q: {q} A: {a}", "metadata": meta})

    log.info(f"  knockout_qa_pairs: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 4. Mercy rule facts
#    Source: wbc_mart.app_game_results
# ─────────────────────────────────────────────────────────────────────────────

def build_mercy_rule_facts(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, official_date, round_label, pool_group,
               away_team_name, home_team_name,
               away_score, home_score, away_is_winner
        FROM wbc_mart.app_game_results
        WHERE is_mercy_rule = TRUE
          AND away_score IS NOT NULL AND home_score IS NOT NULL
    """
    rows = []
    for r in fetch(conn, sql):
        winner, loser, ws, ls = winner_loser(r)
        rd   = r["pool_group"] or r["round_label"] or "game"
        s    = r["season"]
        date = fmt_date(r["official_date"])
        meta = {"source": "mercy_rule_facts", "game_pk": r["game_pk"], "season": s}

        rows.append({"content": f"{winner} defeated {loser} {ws}-{ls} via the mercy rule in the {s} WBC {rd} on {date}.", "metadata": meta})
        rows.append({"content": f"Q: Was the {s} WBC {rd} game between {winner} and {loser} ended by the mercy rule? A: Yes, {winner} won {ws}-{ls}.", "metadata": meta})
        rows.append({"content": f"Q: Did any {s} WBC games end by mercy rule? A: Yes, one example is {winner} defeating {loser} {ws}-{ls} in the {rd}.", "metadata": meta})

    log.info(f"  mercy_rule_facts: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 5. One-run game facts
#    Source: wbc_mart.app_game_results
# ─────────────────────────────────────────────────────────────────────────────

def build_one_run_game_facts(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, official_date, round_label, pool_group,
               away_team_name, home_team_name,
               away_score, home_score, away_is_winner
        FROM wbc_mart.app_game_results
        WHERE is_one_run_game = TRUE
          AND away_score IS NOT NULL AND home_score IS NOT NULL
    """
    rows = []
    for r in fetch(conn, sql):
        winner, loser, ws, ls = winner_loser(r)
        rd   = r["pool_group"] or r["round_label"] or "game"
        s    = r["season"]
        date = fmt_date(r["official_date"])
        meta = {"source": "one_run_game_facts", "game_pk": r["game_pk"], "season": s}

        rows.append({"content": f"{winner} edged {loser} {ws}-{ls} in a one-run game in the {s} WBC {rd} on {date}.", "metadata": meta})
        rows.append({"content": f"The {s} WBC {rd} game between {winner} and {loser} on {date} was decided by one run ({ws}-{ls}).", "metadata": meta})

    log.info(f"  one_run_game_facts: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 6. High-scoring and blowout game facts
#    Source: wbc_mart.app_game_results
# ─────────────────────────────────────────────────────────────────────────────

def build_high_scoring_blowout_facts(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, official_date, round_label, pool_group,
               away_team_name, home_team_name,
               away_score, home_score, away_is_winner,
               run_margin, total_runs
        FROM wbc_mart.app_game_results
        WHERE away_score IS NOT NULL AND home_score IS NOT NULL
          AND (run_margin >= 7 OR total_runs >= 15)
    """
    rows = []
    for r in fetch(conn, sql):
        winner, loser, ws, ls = winner_loser(r)
        rd     = r["pool_group"] or r["round_label"] or "game"
        s      = r["season"]
        date   = fmt_date(r["official_date"])
        margin = r["run_margin"] or 0
        total  = r["total_runs"] or 0
        meta   = {"source": "high_scoring_blowout_facts", "game_pk": r["game_pk"], "season": s}

        if margin >= 7:
            rows.append({"content": f"{winner} blew out {loser} {ws}-{ls} by {margin} runs in the {s} WBC {rd} on {date}.", "metadata": meta})
        if total >= 15:
            rows.append({"content": f"The {s} WBC {rd} game between {r['away_team_name']} and {r['home_team_name']} on {date} combined for {total} total runs ({ws}-{ls}).", "metadata": meta})

    log.info(f"  high_scoring_blowout_facts: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 7. Venue facts
#    Source: wbc_mart.app_game_results
# ─────────────────────────────────────────────────────────────────────────────

def build_venue_facts(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, official_date, round_label, pool_group,
               away_team_name, home_team_name,
               away_score, home_score, away_is_winner, venue_name
        FROM wbc_mart.app_game_results
        WHERE venue_name IS NOT NULL
          AND away_score IS NOT NULL AND home_score IS NOT NULL
    """
    rows = []
    for r in fetch(conn, sql):
        winner, loser, ws, ls = winner_loser(r)
        rd    = r["pool_group"] or r["round_label"] or "game"
        s     = r["season"]
        date  = fmt_date(r["official_date"])
        venue = r["venue_name"]
        rl    = r["round_label"] or ""
        meta  = {"source": "venue_facts", "game_pk": r["game_pk"], "season": s}

        rows.append({"content": f"The {s} WBC {rd} game between {r['away_team_name']} and {r['home_team_name']} on {date} was played at {venue}.", "metadata": meta})

        if is_championship(rl):
            rows.append({"content": f"The {s} WBC Championship game was held at {venue}.", "metadata": meta})
            rows.append({"content": f"Q: Where was the {s} WBC Championship game played? A: {venue}.", "metadata": meta})
            rows.append({"content": f"{venue} hosted the {s} WBC Championship, where {winner} defeated {loser} {ws}-{ls}.", "metadata": meta})

    log.info(f"  venue_facts: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 8. Inning scoring facts
#    Source: wbc_mart.app_game_results
#    Columns: away_innings, home_innings (integer arrays),
#             away_is_winner, away_team_name, home_team_name
# ─────────────────────────────────────────────────────────────────────────────

def build_inning_scoring_facts(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, official_date, round_label, pool_group,
               away_team_name, home_team_name,
               away_score, home_score, away_is_winner,
               away_innings, home_innings
        FROM wbc_mart.app_game_results
        WHERE away_innings IS NOT NULL AND home_innings IS NOT NULL
          AND away_score IS NOT NULL AND home_score IS NOT NULL
    """
    rows = []
    for r in fetch(conn, sql):
        s       = r["season"]
        date    = fmt_date(r["official_date"])
        rd      = r["pool_group"] or r["round_label"] or "game"
        away    = r["away_team_name"]
        home    = r["home_team_name"]
        a_inn   = r["away_innings"] or []
        h_inn   = r["home_innings"] or []
        meta    = {"source": "inning_scoring_facts", "game_pk": r["game_pk"], "season": s}

        # Big innings (3+ runs)
        for i, runs in enumerate(a_inn, start=1):
            if runs and int(runs) >= 3:
                rows.append({"content": f"{away} scored {runs} runs in inning {i} of their {s} WBC {rd} game on {date} against {home}.", "metadata": meta})
        for i, runs in enumerate(h_inn, start=1):
            if runs and int(runs) >= 3:
                rows.append({"content": f"{home} scored {runs} runs in inning {i} of their {s} WBC {rd} game on {date} against {away}.", "metadata": meta})

        # Walk-off: home team wins and scored in their last inning
        home_won = not r["away_is_winner"]
        if home_won and h_inn and h_inn[-1] and int(h_inn[-1]) > 0:
            inn_num = len(h_inn)
            if inn_num >= 9:
                runs = h_inn[-1]
                rows.append({"content": f"{home} scored {runs} run{'s' if int(runs) != 1 else ''} in the {inn_num}th inning to walk off {away} in the {s} WBC {rd} on {date}.", "metadata": meta})

        # Extra innings
        max_inn = max(len(a_inn), len(h_inn))
        if max_inn > 9:
            rows.append({"content": f"The {s} WBC {rd} game between {away} and {home} on {date} went {max_inn} innings.", "metadata": meta})

    log.info(f"  inning_scoring_facts: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 9. RHE box line facts
#    Source: wbc_mart.app_game_results
#    Columns: away_r, away_h, away_e, home_r, home_h, home_e
# ─────────────────────────────────────────────────────────────────────────────

def build_rhe_facts(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, official_date, round_label, pool_group,
               away_team_name, home_team_name,
               away_r, away_h, away_e,
               home_r, home_h, home_e
        FROM wbc_mart.app_game_results
        WHERE away_r IS NOT NULL AND home_r IS NOT NULL
    """
    rows = []
    for r in fetch(conn, sql):
        s    = r["season"]
        date = fmt_date(r["official_date"])
        rd   = r["pool_group"] or r["round_label"] or "game"
        away = r["away_team_name"]
        home = r["home_team_name"]
        meta = {"source": "rhe_facts", "game_pk": r["game_pk"], "season": s}

        rows.append({
            "content": (
                f"In the {s} WBC {rd} game on {date} ({away} vs {home}), "
                f"the final line was: {away} — {r['away_r']}R {r['away_h']}H {r['away_e']}E; "
                f"{home} — {r['home_r']}R {r['home_h']}H {r['home_e']}E."
            ),
            "metadata": meta,
        })

        if r["away_e"] and int(r["away_e"]) >= 3:
            rows.append({"content": f"{away} committed {r['away_e']} errors in the {s} WBC {rd} game on {date} against {home}.", "metadata": meta})
        if r["home_e"] and int(r["home_e"]) >= 3:
            rows.append({"content": f"{home} committed {r['home_e']} errors in the {s} WBC {rd} game on {date} against {away}.", "metadata": meta})

    log.info(f"  rhe_facts: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 10. Pool standings sentences
#     Source: wbc_mart.app_pool_standings
#     Columns: season, pool_group, team_name, team_abbreviation,
#              pool_wins, pool_losses, pool_win_pct,
#              pool_run_differential, pool_runs_scored, pool_runs_allowed
# ─────────────────────────────────────────────────────────────────────────────

def build_pool_standings_sentences(conn) -> list[dict]:
    sql = """
        SELECT season, pool_group, team_name, team_abbreviation,
               pool_wins, pool_losses, pool_win_pct,
               pool_run_differential, pool_runs_scored, pool_runs_allowed
        FROM wbc_mart.app_pool_standings
    """
    rows = []
    for r in fetch(conn, sql):
        s    = r["season"]
        pool = r["pool_group"]
        team = r["team_name"]
        w    = r["pool_wins"]
        l    = r["pool_losses"]
        rd   = r["pool_run_differential"] or 0
        rds  = f"+{rd}" if rd > 0 else str(rd)
        meta = {"source": "pool_standings", "season": s, "pool_group": pool, "team_name": team}

        rows.append({"content": f"In the {s} WBC {pool}, {team} went {w}-{l} with a {rds} run differential.", "metadata": meta})

        if r["pool_runs_scored"] is not None and r["pool_runs_allowed"] is not None:
            rows.append({"content": f"{team} scored {r['pool_runs_scored']} runs and allowed {r['pool_runs_allowed']} runs in the {s} WBC {pool}.", "metadata": meta})

        if r["pool_win_pct"] is not None:
            pct = f"{float(r['pool_win_pct']):.3f}"
            rows.append({"content": f"{team} had a {pct} win percentage in the {s} WBC {pool}.", "metadata": meta})

    log.info(f"  pool_standings_sentences: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 11. Pool standings expanded (undefeated / winless)
#     Source: wbc_mart.app_pool_standings
# ─────────────────────────────────────────────────────────────────────────────

def build_pool_standings_expanded(conn) -> list[dict]:
    sql = """
        SELECT season, pool_group, team_name, pool_wins, pool_losses
        FROM wbc_mart.app_pool_standings
    """
    rows = []
    for r in fetch(conn, sql):
        s, pool, team, w, l = r["season"], r["pool_group"], r["team_name"], r["pool_wins"], r["pool_losses"]
        meta = {"source": "pool_standings_expanded", "season": s, "pool_group": pool, "team_name": team}

        if l == 0 and w > 0:
            rows.append({"content": f"{team} went undefeated in the {s} WBC {pool} with a perfect {w}-0 record.", "metadata": meta})
            rows.append({"content": f"Q: Did {team} go undefeated in the {s} WBC pool play? A: Yes, {team} finished {w}-0 in {pool}.", "metadata": meta})
        if w == 0 and l > 0:
            rows.append({"content": f"{team} went winless in the {s} WBC {pool}, finishing 0-{l}.", "metadata": meta})

    log.info(f"  pool_standings_expanded: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 12. Pool winners
#     Source: wbc_mart.app_pool_standings
#     (already sorted by pool_rank; DISTINCT ON gives the top team per pool)
# ─────────────────────────────────────────────────────────────────────────────

def build_pool_winners(conn) -> list[dict]:
    sql = """
        SELECT DISTINCT ON (season, pool_group)
            season, pool_group, team_name, team_abbreviation,
            pool_wins, pool_losses
        FROM wbc_mart.app_pool_standings
        ORDER BY season, pool_group, pool_wins DESC, pool_run_differential DESC
    """
    rows = []
    for r in fetch(conn, sql):
        s, pool, team, w, l = r["season"], r["pool_group"], r["team_name"], r["pool_wins"], r["pool_losses"]
        meta = {"source": "pool_winners", "season": s, "pool_group": pool, "team_name": team}

        rows.append({"content": f"{team} won the {s} WBC {pool} with a {w}-{l} record.", "metadata": meta})
        rows.append({"content": f"Q: Who won the {s} WBC {pool}? A: {team} finished first at {w}-{l}.", "metadata": meta})

    log.info(f"  pool_winners: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 13. Team overall season record (all rounds)
#     Source: wbc_mart.app_game_results  (derived in SQL)
# ─────────────────────────────────────────────────────────────────────────────

def build_team_season_record(conn) -> list[dict]:
    sql = """
        WITH all_results AS (
            SELECT season, away_team_name AS team,
                   CASE WHEN away_is_winner THEN 1 ELSE 0 END AS win,
                   CASE WHEN away_is_winner THEN 0 ELSE 1 END AS loss
            FROM wbc_mart.app_game_results
            WHERE away_score IS NOT NULL
            UNION ALL
            SELECT season, home_team_name AS team,
                   CASE WHEN NOT away_is_winner THEN 1 ELSE 0 END AS win,
                   CASE WHEN NOT away_is_winner THEN 0 ELSE 1 END AS loss
            FROM wbc_mart.app_game_results
            WHERE home_score IS NOT NULL
        )
        SELECT season, team, SUM(win) AS wins, SUM(loss) AS losses
        FROM all_results
        GROUP BY season, team
    """
    rows = []
    for r in fetch(conn, sql):
        s, team, w, l = r["season"], r["team"], r["wins"], r["losses"]
        meta = {"source": "team_season_record", "season": s, "team_name": team}
        rows.append({"content": f"{team} finished the {s} WBC with an overall record of {w} wins and {l} losses.", "metadata": meta})

    log.info(f"  team_season_record: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 14. Player season core sentences
#     Source: wbc_mart.app_player_season_stats
#     Columns: person_id, season, full_name, position_type, position,
#              team_abbreviation, games_played, bat_side_code, pitch_hand_code,
#              season_batting_ab, season_batting_hits, season_batting_avg,
#              season_batting_hr, season_batting_rbi, season_batting_bb,
#              season_batting_so, season_batting_sb,
#              season_pitching_era, season_pitching_ip, season_pitching_so,
#              season_pitching_w, season_pitching_l, season_pitching_sv,
#              season_pitching_gs, season_pitching_bf
# ─────────────────────────────────────────────────────────────────────────────

def build_player_season_sentences(conn) -> list[dict]:
    sql = """
        SELECT person_id, season, full_name, position_type, position,
               team_abbreviation, games_played,
               season_batting_ab, season_batting_hits, season_batting_avg,
               season_batting_hr, season_batting_rbi, season_batting_bb,
               season_batting_so, season_batting_sb,
               season_pitching_era, season_pitching_ip, season_pitching_so,
               season_pitching_w, season_pitching_l, season_pitching_sv,
               season_pitching_gs, season_pitching_bf
        FROM wbc_mart.app_player_season_stats
        WHERE games_played > 0
    """
    rows = []
    for r in fetch(conn, sql):
        name  = r["full_name"] or "Unknown"
        team  = r["team_abbreviation"] or "?"
        pos   = r["position"] or "?"
        s     = r["season"]
        gp    = r["games_played"]
        is_p  = (r["position_type"] == "Pitcher") or bool(r["season_pitching_bf"] and r["season_pitching_bf"] > 0)
        meta  = {"source": "player_season_stats", "season": s,
                 "full_name": name, "team_abbreviation": team}

        if is_p:
            era = fmt_era(r["season_pitching_era"])
            ip  = fmt_ip(r["season_pitching_ip"])
            k   = r["season_pitching_so"] or 0
            w   = r["season_pitching_w"] or 0
            l   = r["season_pitching_l"] or 0
            sv  = r["season_pitching_sv"] or 0
            gs  = r["season_pitching_gs"] or 0
            rows.append({
                "content": f"In the {s} WBC, {name} ({team}, {pos}) pitched {ip} IP with a {era} ERA, {k} strikeouts, {w}-{l} record, and {sv} saves in {gp} games ({gs} starts).",
                "metadata": meta,
            })
        else:
            avg = fmt_avg(r["season_batting_avg"])
            h   = r["season_batting_hits"] or 0
            ab  = r["season_batting_ab"] or 0
            hr  = r["season_batting_hr"] or 0
            rbi = r["season_batting_rbi"] or 0
            bb  = r["season_batting_bb"] or 0
            so  = r["season_batting_so"] or 0
            sb  = r["season_batting_sb"] or 0
            rows.append({
                "content": f"In the {s} WBC, {name} ({team}, {pos}) batted {avg} ({h}-for-{ab}) with {hr} HR, {rbi} RBI, {bb} BB, {so} SO, and {sb} SB in {gp} games.",
                "metadata": meta,
            })

    log.info(f"  player_season_sentences: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 15. Player season advanced batting
#     Source: wbc_mart.app_player_season_stats
#     Columns: season_batting_obp, season_batting_slg, season_batting_ops,
#              season_batting_iso, season_batting_babip,
#              season_batting_k_rate, season_batting_bb_rate,
#              season_batting_doubles, season_batting_triples
# ─────────────────────────────────────────────────────────────────────────────

def build_player_season_adv_batting(conn) -> list[dict]:
    sql = """
        SELECT season, full_name, team_abbreviation,
               season_batting_obp, season_batting_slg, season_batting_ops,
               season_batting_iso, season_batting_babip,
               season_batting_k_rate, season_batting_bb_rate,
               season_batting_doubles, season_batting_triples,
               season_batting_ab
        FROM wbc_mart.app_player_season_stats
        WHERE games_played > 0
          AND season_batting_ab > 0
          AND position_type != 'Pitcher'
    """
    rows = []
    for r in fetch(conn, sql):
        name = r["full_name"] or "Unknown"
        team = r["team_abbreviation"] or "?"
        s    = r["season"]
        meta = {"source": "player_season_adv_batting", "season": s,
                "full_name": name, "team_abbreviation": team}

        if r["season_batting_ops"] and float(r["season_batting_ops"]) > 0:
            obp = fmt_avg(r["season_batting_obp"])
            slg = fmt_avg(r["season_batting_slg"])
            ops = f"{float(r['season_batting_ops']):.3f}"
            rows.append({"content": f"{name} ({team}) had an OBP of {obp}, SLG of {slg}, and OPS of {ops} in the {s} WBC.", "metadata": meta})

        if r["season_batting_iso"] and float(r["season_batting_iso"]) > 0:
            rows.append({"content": f"{name} ({team}) had an isolated power (ISO) of {fmt_avg(r['season_batting_iso'])} in the {s} WBC.", "metadata": meta})

        if r["season_batting_babip"] and float(r["season_batting_babip"]) > 0:
            rows.append({"content": f"{name} ({team}) had a BABIP of {fmt_avg(r['season_batting_babip'])} in the {s} WBC.", "metadata": meta})

        if r["season_batting_k_rate"] and float(r["season_batting_k_rate"]) > 0:
            rows.append({"content": f"{name} ({team}) had a {float(r['season_batting_k_rate'])*100:.1f}% strikeout rate in the {s} WBC.", "metadata": meta})

        if r["season_batting_bb_rate"] and float(r["season_batting_bb_rate"]) > 0:
            rows.append({"content": f"{name} ({team}) had a {float(r['season_batting_bb_rate'])*100:.1f}% walk rate in the {s} WBC.", "metadata": meta})

        d = r["season_batting_doubles"] or 0
        t = r["season_batting_triples"] or 0
        if d > 0 or t > 0:
            parts = []
            if d > 0: parts.append(f"{d} double{'s' if d != 1 else ''}")
            if t > 0: parts.append(f"{t} triple{'s' if t != 1 else ''}")
            rows.append({"content": f"{name} ({team}) had {' and '.join(parts)} in the {s} WBC.", "metadata": meta})

    log.info(f"  player_season_adv_batting: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 16. Player season advanced pitching
#     Source: wbc_mart.app_player_season_stats
#     Columns: season_pitching_era, season_pitching_ip, season_pitching_whip,
#              season_pitching_k_per_9, season_pitching_bb_per_9,
#              season_pitching_so, season_pitching_bb,
#              season_pitching_w, season_pitching_l, season_pitching_sv,
#              season_pitching_gs
# ─────────────────────────────────────────────────────────────────────────────

def build_player_season_adv_pitching(conn) -> list[dict]:
    sql = """
        SELECT season, full_name, team_abbreviation,
               season_pitching_era, season_pitching_ip, season_pitching_whip,
               season_pitching_k_per_9, season_pitching_bb_per_9,
               season_pitching_so, season_pitching_bb,
               season_pitching_w, season_pitching_l,
               season_pitching_sv, season_pitching_gs
        FROM wbc_mart.app_player_season_stats
        WHERE games_played > 0
          AND season_pitching_ip > 0
    """
    rows = []
    for r in fetch(conn, sql):
        name = r["full_name"] or "Unknown"
        team = r["team_abbreviation"] or "?"
        s    = r["season"]
        ip   = fmt_ip(r["season_pitching_ip"])
        era  = fmt_era(r["season_pitching_era"])
        w    = r["season_pitching_w"] or 0
        l    = r["season_pitching_l"] or 0
        sv   = r["season_pitching_sv"] or 0
        gs   = r["season_pitching_gs"] or 0
        k    = r["season_pitching_so"] or 0
        bb   = r["season_pitching_bb"] or 0
        meta = {"source": "player_season_adv_pitching", "season": s,
                "full_name": name, "team_abbreviation": team}

        rows.append({"content": f"{name} ({team}) went {w}-{l} with {sv} saves, a {era} ERA, {k} K, {bb} BB, and {ip} IP in the {s} WBC ({gs} starts).", "metadata": meta})

        if r["season_pitching_whip"] and float(r["season_pitching_whip"]) > 0:
            rows.append({"content": f"{name} ({team}) had a WHIP of {float(r['season_pitching_whip']):.3f} in the {s} WBC.", "metadata": meta})

        if r["season_pitching_k_per_9"] and float(r["season_pitching_k_per_9"]) > 0:
            rows.append({"content": f"{name} ({team}) had a K/9 of {float(r['season_pitching_k_per_9']):.2f} in the {s} WBC.", "metadata": meta})

        if r["season_pitching_bb_per_9"] and float(r["season_pitching_bb_per_9"]) > 0:
            rows.append({"content": f"{name} ({team}) had a BB/9 of {float(r['season_pitching_bb_per_9']):.2f} in the {s} WBC.", "metadata": meta})

    log.info(f"  player_season_adv_pitching: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 17. Player season stolen base sentences
#     Source: wbc_mart.app_player_season_stats
# ─────────────────────────────────────────────────────────────────────────────

def build_player_season_xbh_sb(conn) -> list[dict]:
    sql = """
        SELECT season, full_name, team_abbreviation, season_batting_sb
        FROM wbc_mart.app_player_season_stats
        WHERE games_played > 0 AND season_batting_sb > 0
    """
    rows = []
    for r in fetch(conn, sql):
        name = r["full_name"] or "Unknown"
        team = r["team_abbreviation"] or "?"
        s    = r["season"]
        sb   = r["season_batting_sb"]
        meta = {"source": "player_season_xbh_sb", "season": s, "full_name": name}
        rows.append({"content": f"{name} ({team}) stole {sb} base{'s' if sb != 1 else ''} in the {s} WBC.", "metadata": meta})

    log.info(f"  player_season_xbh_sb: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 18. Per-season stat leaders
#     Source: wbc_mart.app_player_season_stats
# ─────────────────────────────────────────────────────────────────────────────

def build_player_season_leaders(conn) -> list[dict]:
    sql = """
        SELECT season, full_name, team_abbreviation, position_type,
               season_batting_avg, season_batting_hits,
               season_batting_hr, season_batting_rbi, season_batting_sb,
               season_batting_ops, season_batting_ab,
               season_pitching_era, season_pitching_so,
               season_pitching_w, season_pitching_ip
        FROM wbc_mart.app_player_season_stats
        WHERE games_played > 0
    """
    bucket: dict = {}
    for r in fetch(conn, sql):
        s    = r["season"]
        name = f"{r['full_name']} ({r['team_abbreviation']})"
        if s not in bucket:
            bucket[s] = {k: [] for k in ("avg", "hits", "hr", "rbi", "sb", "ops", "era", "so", "wins")}

        ab = r["season_batting_ab"] or 0
        if r["season_batting_avg"] and ab >= 10:
            bucket[s]["avg"].append((float(r["season_batting_avg"]), name))
        if r["season_batting_hits"]:
            bucket[s]["hits"].append((r["season_batting_hits"], name))
        if r["season_batting_hr"]:
            bucket[s]["hr"].append((r["season_batting_hr"], name))
        if r["season_batting_rbi"]:
            bucket[s]["rbi"].append((r["season_batting_rbi"], name))
        if r["season_batting_sb"]:
            bucket[s]["sb"].append((r["season_batting_sb"], name))
        if r["season_batting_ops"] and ab >= 10:
            bucket[s]["ops"].append((float(r["season_batting_ops"]), name))
        if r["season_pitching_era"] is not None and r["season_pitching_ip"] and float(r["season_pitching_ip"]) >= 9:
            bucket[s]["era"].append((float(r["season_pitching_era"]), name))
        if r["season_pitching_so"]:
            bucket[s]["so"].append((r["season_pitching_so"], name))
        if r["season_pitching_w"]:
            bucket[s]["wins"].append((r["season_pitching_w"], name))

    rows = []
    for s, cats in bucket.items():
        meta = {"source": "player_season_leaders", "season": s}

        def top(lst, asc=False):
            lst = [(v, n) for v, n in lst if v and v > 0]
            if not lst:
                return None, None
            lst.sort(key=lambda x: x[0], reverse=not asc)
            return lst[0]

        v, n = top(cats["hr"])
        if n: rows.append({"content": f"{n} led the {s} WBC in home runs with {v} HR.", "metadata": meta})

        v, n = top(cats["rbi"])
        if n: rows.append({"content": f"{n} led the {s} WBC in RBI with {v} runs batted in.", "metadata": meta})

        v, n = top(cats["hits"])
        if n: rows.append({"content": f"{n} led the {s} WBC in hits with {v} H.", "metadata": meta})

        v, n = top(cats["avg"])
        if n: rows.append({"content": f"{n} led the {s} WBC in batting average at {fmt_avg(v)}.", "metadata": meta})

        v, n = top(cats["ops"])
        if n: rows.append({"content": f"{n} led the {s} WBC in OPS with {v:.3f}.", "metadata": meta})

        v, n = top(cats["sb"])
        if n: rows.append({"content": f"{n} led the {s} WBC in stolen bases with {v} SB.", "metadata": meta})

        v, n = top(cats["so"])
        if n: rows.append({"content": f"{n} led the {s} WBC in pitching strikeouts with {v} K.", "metadata": meta})

        v, n = top(cats["wins"])
        if n: rows.append({"content": f"{n} led the {s} WBC in pitching wins with {v} W.", "metadata": meta})

        v, n = top(cats["era"], asc=True)
        if n: rows.append({"content": f"{n} had the lowest ERA among qualified pitchers in the {s} WBC at {v:.2f}.", "metadata": meta})

    log.info(f"  player_season_leaders: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 19. Player bio facts
#     Source: wbc_mart.app_game_detail  (DISTINCT ON player_id)
#     Columns: player_id, full_name, birth_date, birth_city, birth_country,
#              height, weight, bat_side_code, pitch_hand_code, primary_number,
#              primary_position_name, primary_position_type,
#              primary_position_abbreviation, mlb_debut_date
# ─────────────────────────────────────────────────────────────────────────────

def build_player_bio_facts(conn) -> list[dict]:
    sql = """
        SELECT DISTINCT ON (player_id)
            player_id, full_name, birth_date, birth_city, birth_country,
            height, weight, bat_side_code, pitch_hand_code, primary_number,
            primary_position_name, primary_position_type,
            primary_position_abbreviation, mlb_debut_date
        FROM wbc_mart.app_game_detail
        WHERE full_name IS NOT NULL
        ORDER BY player_id, season DESC
    """
    rows = []
    for r in fetch(conn, sql):
        name = r["full_name"] or "Unknown"
        meta = {"source": "player_bio_facts", "full_name": name}

        if r["height"] and r["weight"]:
            rows.append({"content": f"{name} stands {r['height']} tall and weighs {r['weight']} lbs.", "metadata": meta})

        bat_map  = {"R": "right-handed", "L": "left-handed", "S": "switch-hitter"}
        hand_map = {"R": "right-handed", "L": "left-handed"}

        if r["bat_side_code"] and r["primary_position_type"] != "Pitcher":
            rows.append({"content": f"{name} bats {bat_map.get(r['bat_side_code'], r['bat_side_code'])}.", "metadata": meta})

        if r["pitch_hand_code"]:
            rows.append({"content": f"{name} throws {hand_map.get(r['pitch_hand_code'], r['pitch_hand_code'])}.", "metadata": meta})

        if r["primary_position_name"] and r["primary_position_abbreviation"]:
            rows.append({"content": f"{name} plays {r['primary_position_name']} ({r['primary_position_abbreviation']}).", "metadata": meta})

        if r["primary_number"]:
            rows.append({"content": f"{name} wore jersey number {r['primary_number']} in the WBC.", "metadata": meta})

        if r["mlb_debut_date"]:
            rows.append({"content": f"{name} made his MLB debut on {fmt_date(r['mlb_debut_date'])} {r['mlb_debut_date'].year}.", "metadata": meta})

        city = r["birth_city"]
        ctry = r["birth_country"]
        if city and ctry:
            rows.append({"content": f"{name} was born in {city}, {ctry}.", "metadata": meta})
        elif ctry:
            rows.append({"content": f"{name} was born in {ctry}.", "metadata": meta})

    log.info(f"  player_bio_facts: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 20. Player game batting sentences
#     Source: wbc_mart.app_game_detail
#     Columns: player_batting_ab, player_batting_hits, player_batting_hr,
#              player_batting_rbi, player_batting_bb, player_batting_so,
#              player_batting_sb, player_batting_runs
# ─────────────────────────────────────────────────────────────────────────────

def build_player_game_batting_sentences(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, official_date, round_label, pool_group,
               full_name, away_team_name, home_team_name,
               player_batting_ab, player_batting_hits,
               player_batting_hr, player_batting_rbi,
               player_batting_bb, player_batting_so, player_batting_sb
        FROM wbc_mart.app_game_detail
        WHERE player_batting_ab > 0
          AND is_on_bench = FALSE
    """
    rows = []
    for r in fetch(conn, sql):
        name    = r["full_name"] or "Unknown"
        s       = r["season"]
        date    = fmt_date(r["official_date"])
        rd      = r["pool_group"] or r["round_label"] or "game"
        matchup = f"{r['away_team_name']} vs {r['home_team_name']}"
        h       = r["player_batting_hits"] or 0
        ab      = r["player_batting_ab"] or 0
        hr      = r["player_batting_hr"] or 0
        rbi     = r["player_batting_rbi"] or 0
        bb      = r["player_batting_bb"] or 0
        sb      = r["player_batting_sb"] or 0
        meta    = {"source": "player_game_batting", "season": s,
                   "game_pk": r["game_pk"], "full_name": name}

        parts = []
        if hr:  parts.append(f"{hr} HR")
        if rbi: parts.append(f"{rbi} RBI")
        if bb:  parts.append(f"{bb} BB")
        if sb:  parts.append(f"{sb} SB")
        suffix = (", " + ", ".join(parts)) if parts else ""

        rows.append({"content": f"In the {s} WBC {rd} game on {date} ({matchup}), {name} went {h}-for-{ab}{suffix}.", "metadata": meta})

    log.info(f"  player_game_batting_sentences: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 21. Player game pitching sentences
#     Source: wbc_mart.app_game_detail
#     Columns: player_pitching_outs, player_pitching_er, player_pitching_so,
#              player_pitching_bb, player_pitching_wins, player_pitching_losses,
#              player_pitching_saves, player_pitching_total_pitches,
#              player_pitching_hits_allowed
# ─────────────────────────────────────────────────────────────────────────────

def build_player_game_pitching_sentences(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, official_date, round_label, pool_group,
               full_name, away_team_name, home_team_name,
               player_pitching_outs, player_pitching_er,
               player_pitching_so, player_pitching_bb,
               player_pitching_wins, player_pitching_losses,
               player_pitching_saves, player_pitching_total_pitches,
               player_pitching_hits_allowed
        FROM wbc_mart.app_game_detail
        WHERE player_pitching_outs > 0
    """
    rows = []
    for r in fetch(conn, sql):
        name    = r["full_name"] or "Unknown"
        s       = r["season"]
        date    = fmt_date(r["official_date"])
        rd      = r["pool_group"] or r["round_label"] or "game"
        matchup = f"{r['away_team_name']} vs {r['home_team_name']}"
        ip      = fmt_ip((r["player_pitching_outs"] or 0) / 3)
        er      = r["player_pitching_er"] or 0
        k       = r["player_pitching_so"] or 0
        bb      = r["player_pitching_bb"] or 0
        ha      = r["player_pitching_hits_allowed"] or 0
        tp      = r["player_pitching_total_pitches"]
        dec     = ""
        if r["player_pitching_wins"]:    dec = ", W"
        elif r["player_pitching_losses"]: dec = ", L"
        elif r["player_pitching_saves"]:  dec = ", SV"
        tp_str  = f", {tp} pitches" if tp else ""
        meta    = {"source": "player_game_pitching", "season": s,
                   "game_pk": r["game_pk"], "full_name": name}

        rows.append({"content": f"In the {s} WBC {rd} game on {date} ({matchup}), {name} pitched {ip} IP, {er} ER, {k} K, {bb} BB, {ha} H{dec}{tp_str}.", "metadata": meta})

    log.info(f"  player_game_pitching_sentences: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 22. Notable batting games (3+ hits, 2+ HR, 4+ RBI, 2+ SB, 3+ BB)
#     Source: wbc_mart.app_game_detail
# ─────────────────────────────────────────────────────────────────────────────

def build_player_game_notable_batting(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, official_date, round_label, pool_group,
               full_name, away_team_name, home_team_name,
               player_batting_hits, player_batting_hr,
               player_batting_rbi, player_batting_sb, player_batting_bb
        FROM wbc_mart.app_game_detail
        WHERE is_on_bench = FALSE
          AND (
            player_batting_hits >= 3 OR
            player_batting_hr   >= 2 OR
            player_batting_rbi  >= 4 OR
            player_batting_sb   >= 2 OR
            player_batting_bb   >= 3
          )
    """
    rows = []
    for r in fetch(conn, sql):
        name    = r["full_name"] or "Unknown"
        s       = r["season"]
        date    = fmt_date(r["official_date"])
        rd      = r["pool_group"] or r["round_label"] or "game"
        matchup = f"{r['away_team_name']} vs {r['home_team_name']}"
        h       = r["player_batting_hits"] or 0
        hr      = r["player_batting_hr"] or 0
        ri      = r["player_batting_rbi"] or 0
        sb      = r["player_batting_sb"] or 0
        bb      = r["player_batting_bb"] or 0
        meta    = {"source": "player_game_notable_batting", "season": s,
                   "game_pk": r["game_pk"], "full_name": name}

        if h >= 3:
            rows.append({"content": f"{name} had {h} hits in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})
            rows.append({"content": f"Q: Who had {h} hits on {date} in the {s} WBC {rd}? A: {name}.", "metadata": meta})
        if hr >= 2:
            rows.append({"content": f"{name} hit {hr} home runs in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})
        if ri >= 4:
            rows.append({"content": f"{name} drove in {ri} runs in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})
        if sb >= 2:
            rows.append({"content": f"{name} stole {sb} bases in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})
        if bb >= 3:
            rows.append({"content": f"{name} drew {bb} walks in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})

    log.info(f"  player_game_notable_batting: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 23. Notable pitching games (10+ K, 7+ IP, 0 ER with 3+ IP)
#     Source: wbc_mart.app_game_detail
# ─────────────────────────────────────────────────────────────────────────────

def build_player_game_notable_pitching(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, official_date, round_label, pool_group,
               full_name, away_team_name, home_team_name,
               player_pitching_outs, player_pitching_so, player_pitching_er
        FROM wbc_mart.app_game_detail
        WHERE player_pitching_outs > 0
          AND (
            player_pitching_so   >= 10 OR
            player_pitching_outs >= 21 OR
            (player_pitching_er = 0 AND player_pitching_outs >= 9)
          )
    """
    rows = []
    for r in fetch(conn, sql):
        name    = r["full_name"] or "Unknown"
        s       = r["season"]
        date    = fmt_date(r["official_date"])
        rd      = r["pool_group"] or r["round_label"] or "game"
        matchup = f"{r['away_team_name']} vs {r['home_team_name']}"
        outs    = r["player_pitching_outs"] or 0
        ip      = fmt_ip(outs / 3)
        k       = r["player_pitching_so"] or 0
        er      = r["player_pitching_er"] or 0
        meta    = {"source": "player_game_notable_pitching", "season": s,
                   "game_pk": r["game_pk"], "full_name": name}

        if k >= 10:
            rows.append({"content": f"{name} struck out {k} batters in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})
        if outs >= 21:
            rows.append({"content": f"{name} pitched {ip} innings in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})
        if er == 0 and outs >= 9:
            rows.append({"content": f"{name} threw {ip} scoreless innings in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})

    log.info(f"  player_game_notable_pitching: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 24. Extra per-game batting facts (doubles, triples, HBP, GIDP)
#     Source: wbc_mart.app_game_detail
#     Columns: player_batting_doubles, player_batting_triples,
#              player_batting_hbp, player_batting_gidp
# ─────────────────────────────────────────────────────────────────────────────

def build_player_game_extra_batting(conn) -> list[dict]:
    sql = """
        SELECT game_pk, season, official_date, round_label, pool_group,
               full_name, away_team_name, home_team_name,
               player_batting_doubles, player_batting_triples,
               player_batting_hbp, player_batting_gidp
        FROM wbc_mart.app_game_detail
        WHERE is_on_bench = FALSE
          AND (
            player_batting_doubles >= 2 OR
            player_batting_triples >= 1 OR
            player_batting_hbp     >= 2 OR
            player_batting_gidp    >= 2
          )
    """
    rows = []
    for r in fetch(conn, sql):
        name    = r["full_name"] or "Unknown"
        s       = r["season"]
        date    = fmt_date(r["official_date"])
        rd      = r["pool_group"] or r["round_label"] or "game"
        matchup = f"{r['away_team_name']} vs {r['home_team_name']}"
        meta    = {"source": "player_game_extra_batting", "season": s,
                   "game_pk": r["game_pk"], "full_name": name}

        d  = r["player_batting_doubles"] or 0
        t  = r["player_batting_triples"] or 0
        hb = r["player_batting_hbp"] or 0
        gi = r["player_batting_gidp"] or 0

        if d >= 2:
            rows.append({"content": f"{name} hit {d} doubles in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})
        if t >= 1:
            rows.append({"content": f"{name} hit a triple in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})
        if hb >= 2:
            rows.append({"content": f"{name} was hit by a pitch {hb} times in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})
        if gi >= 2:
            rows.append({"content": f"{name} grounded into {gi} double plays in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})

    log.info(f"  player_game_extra_batting: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 25. Team game batting box
#     Source: wbc_mart.app_game_detail  (DISTINCT ON game_pk)
#     Columns: away_batting_hits/hr/bb/so/sb/doubles/triples/lob
#              home_batting_hits/hr/bb/so/sb/doubles/triples/lob
# ─────────────────────────────────────────────────────────────────────────────

def build_team_game_batting_box(conn) -> list[dict]:
    sql = """
        SELECT DISTINCT ON (game_pk)
            game_pk, season, official_date, round_label, pool_group,
            away_team_name,
            away_batting_hits, away_batting_hr, away_batting_bb,
            away_batting_so, away_batting_sb,
            away_batting_doubles, away_batting_triples, away_batting_lob,
            home_team_name,
            home_batting_hits, home_batting_hr, home_batting_bb,
            home_batting_so, home_batting_sb,
            home_batting_doubles, home_batting_triples, home_batting_lob
        FROM wbc_mart.app_game_detail
        ORDER BY game_pk
    """
    rows = []
    for r in fetch(conn, sql):
        s       = r["season"]
        date    = fmt_date(r["official_date"])
        rd      = r["pool_group"] or r["round_label"] or "game"
        away    = r["away_team_name"]
        home    = r["home_team_name"]
        matchup = f"{away} vs {home}"
        meta    = {"source": "team_game_batting_box", "season": s, "game_pk": r["game_pk"]}

        for side, px in ((away, "away"), (home, "home")):
            h   = r[f"{px}_batting_hits"] or 0
            hr  = r[f"{px}_batting_hr"] or 0
            bb  = r[f"{px}_batting_bb"] or 0
            so  = r[f"{px}_batting_so"] or 0
            sb  = r[f"{px}_batting_sb"] or 0
            d2  = r[f"{px}_batting_doubles"] or 0
            d3  = r[f"{px}_batting_triples"] or 0
            lob = r[f"{px}_batting_lob"] or 0

            rows.append({"content": f"In the {s} WBC {rd} game on {date} ({matchup}), {side} had {h} hits, {hr} HR, {bb} BB, {so} SO, and {sb} SB as a team.", "metadata": meta})

            if d2 > 0 or d3 > 0:
                xbh = []
                if d2: xbh.append(f"{d2} double{'s' if d2 != 1 else ''}")
                if d3: xbh.append(f"{d3} triple{'s' if d3 != 1 else ''}")
                rows.append({"content": f"In the {s} WBC {rd} game on {date} ({matchup}), {side} hit {' and '.join(xbh)} as a team.", "metadata": meta})

            if lob > 0:
                rows.append({"content": f"{side} left {lob} runners on base in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})

    log.info(f"  team_game_batting_box: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 26. Team game pitching box
#     Source: wbc_mart.app_game_detail  (DISTINCT ON game_pk)
#     Columns: away_pitching_total_pitches/strikes/so/bb/er/wp/hbp/hr_allowed
#              home_pitching_total_pitches/strikes/so/bb/er/wp/hbp/hr_allowed
# ─────────────────────────────────────────────────────────────────────────────

def build_team_game_pitching_box(conn) -> list[dict]:
    sql = """
        SELECT DISTINCT ON (game_pk)
            game_pk, season, official_date, round_label, pool_group,
            away_team_name,
            away_pitching_total_pitches, away_pitching_strikes,
            away_pitching_so, away_pitching_bb, away_pitching_er,
            away_pitching_wp, away_pitching_hbp, away_pitching_hr_allowed,
            home_team_name,
            home_pitching_total_pitches, home_pitching_strikes,
            home_pitching_so, home_pitching_bb, home_pitching_er,
            home_pitching_wp, home_pitching_hbp, home_pitching_hr_allowed
        FROM wbc_mart.app_game_detail
        WHERE away_pitching_total_pitches IS NOT NULL
          AND home_pitching_total_pitches IS NOT NULL
        ORDER BY game_pk
    """
    rows = []
    for r in fetch(conn, sql):
        s       = r["season"]
        date    = fmt_date(r["official_date"])
        rd      = r["pool_group"] or r["round_label"] or "game"
        away    = r["away_team_name"]
        home    = r["home_team_name"]
        matchup = f"{away} vs {home}"
        meta    = {"source": "team_game_pitching_box", "season": s, "game_pk": r["game_pk"]}

        for side, px, opp in ((away, "away", home), (home, "home", away)):
            tp  = r[f"{px}_pitching_total_pitches"] or 0
            st  = r[f"{px}_pitching_strikes"] or 0
            k   = r[f"{px}_pitching_so"] or 0
            bb  = r[f"{px}_pitching_bb"] or 0
            er  = r[f"{px}_pitching_er"] or 0
            wp  = r[f"{px}_pitching_wp"] or 0
            hr  = r[f"{px}_pitching_hr_allowed"] or 0

            if tp > 0:
                pct = f"{st / tp * 100:.1f}%"
                rows.append({"content": f"{side}'s pitchers threw {tp} pitches ({st} strikes, {pct} strike rate) with {k} K, {bb} BB, and {er} ER in the {s} WBC {rd} game on {date} vs {opp}.", "metadata": meta})
            if wp >= 2:
                rows.append({"content": f"{side}'s pitchers threw {wp} wild pitches in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})
            if hr >= 2:
                rows.append({"content": f"{side}'s pitchers allowed {hr} home runs in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})

    log.info(f"  team_game_pitching_box: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 27. Team game fielding facts
#     Source: wbc_mart.app_game_detail  (DISTINCT ON game_pk)
#     Columns: away_fielding_errors/passed_balls
#              home_fielding_errors/passed_balls
# ─────────────────────────────────────────────────────────────────────────────

def build_team_game_fielding_facts(conn) -> list[dict]:
    sql = """
        SELECT DISTINCT ON (game_pk)
            game_pk, season, official_date, round_label, pool_group,
            away_team_name,
            away_fielding_errors, away_fielding_passed_balls,
            home_team_name,
            home_fielding_errors, home_fielding_passed_balls
        FROM wbc_mart.app_game_detail
        WHERE (
            away_fielding_errors       >= 3 OR
            home_fielding_errors       >= 3 OR
            away_fielding_passed_balls >= 2 OR
            home_fielding_passed_balls >= 2
        )
        ORDER BY game_pk
    """
    rows = []
    for r in fetch(conn, sql):
        s       = r["season"]
        date    = fmt_date(r["official_date"])
        rd      = r["pool_group"] or r["round_label"] or "game"
        away    = r["away_team_name"]
        home    = r["home_team_name"]
        matchup = f"{away} vs {home}"
        meta    = {"source": "team_game_fielding_facts", "season": s, "game_pk": r["game_pk"]}

        ae  = r["away_fielding_errors"] or 0
        he  = r["home_fielding_errors"] or 0
        apb = r["away_fielding_passed_balls"] or 0
        hpb = r["home_fielding_passed_balls"] or 0

        if ae >= 3:
            rows.append({"content": f"{away} committed {ae} errors in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})
        if he >= 3:
            rows.append({"content": f"{home} committed {he} errors in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})
        if apb >= 2:
            rows.append({"content": f"{away}'s catcher allowed {apb} passed balls in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})
        if hpb >= 2:
            rows.append({"content": f"{home}'s catcher allowed {hpb} passed balls in the {s} WBC {rd} game on {date} ({matchup}).", "metadata": meta})

    log.info(f"  team_game_fielding_facts: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 28. Player career sentences (multi-season players only)
#     Source: wbc_mart.app_player_season_stats  (aggregated in SQL)
#     Columns: full_name, team_abbreviation, position_type, season,
#              season_batting_ab, season_batting_hits, season_batting_hr,
#              season_batting_rbi, season_batting_sb, season_batting_doubles,
#              season_pitching_so, season_pitching_w, season_pitching_l,
#              season_pitching_sv, games_played
# ─────────────────────────────────────────────────────────────────────────────

def build_player_career_sentences(conn) -> list[dict]:
    sql = """
        SELECT full_name, team_abbreviation, position_type,
               COUNT(DISTINCT season)           AS seasons,
               SUM(games_played)                AS career_gp,
               SUM(season_batting_ab)           AS career_ab,
               SUM(season_batting_hits)         AS career_hits,
               SUM(season_batting_hr)           AS career_hr,
               SUM(season_batting_rbi)          AS career_rbi,
               SUM(season_batting_sb)           AS career_sb,
               SUM(season_batting_doubles)      AS career_2b,
               SUM(season_pitching_so)          AS career_k,
               SUM(season_pitching_w)           AS career_w,
               SUM(season_pitching_l)           AS career_l,
               SUM(season_pitching_sv)          AS career_sv
        FROM wbc_mart.app_player_season_stats
        WHERE games_played > 0
        GROUP BY full_name, team_abbreviation, position_type
        HAVING COUNT(DISTINCT season) > 1
    """
    rows = []
    for r in fetch(conn, sql):
        name    = r["full_name"] or "Unknown"
        team    = r["team_abbreviation"] or "?"
        seasons = r["seasons"]
        gp      = r["career_gp"] or 0
        meta    = {"source": "player_career_sentences", "full_name": name}
        is_p    = r["position_type"] == "Pitcher"

        if is_p:
            w  = r["career_w"] or 0
            l  = r["career_l"] or 0
            sv = r["career_sv"] or 0
            k  = r["career_k"] or 0
            rows.append({"content": f"{name} ({team}) appeared in {seasons} WBC tournaments, going {w}-{l} with {sv} saves and {k} career strikeouts across {gp} games.", "metadata": meta})
        else:
            ab  = r["career_ab"] or 0
            h   = r["career_hits"] or 0
            hr  = r["career_hr"] or 0
            rbi = r["career_rbi"] or 0
            sb  = r["career_sb"] or 0
            d2  = r["career_2b"] or 0
            avg = fmt_avg(h / ab) if ab > 0 else ".000"
            rows.append({"content": f"{name} ({team}) played in {seasons} WBC tournaments, batting {avg} ({h}-for-{ab}) with {hr} career HR and {rbi} career RBI across {gp} games.", "metadata": meta})
            rows.append({"content": f"Over their WBC career, {name} ({team}) hit {hr} home runs, drove in {rbi} runs, and stole {sb} bases.", "metadata": meta})
            if d2 > 0:
                rows.append({"content": f"{name} ({team}) hit {d2} career doubles in the WBC.", "metadata": meta})

    log.info(f"  player_career_sentences: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run():
    log.info("Starting WBC embedding pipeline...")
    conn = get_connection()

    sentences = []

    # Game results (wbc_mart.app_game_results)
    sentences.extend(build_game_result_sentences(conn))
    sentences.extend(build_game_result_variants(conn))
    sentences.extend(build_knockout_qa_pairs(conn))
    sentences.extend(build_mercy_rule_facts(conn))
    sentences.extend(build_one_run_game_facts(conn))
    sentences.extend(build_high_scoring_blowout_facts(conn))
    sentences.extend(build_venue_facts(conn))
    sentences.extend(build_inning_scoring_facts(conn))
    sentences.extend(build_rhe_facts(conn))

    # Standings (wbc_mart.app_pool_standings)
    sentences.extend(build_pool_standings_sentences(conn))
    sentences.extend(build_pool_standings_expanded(conn))
    sentences.extend(build_pool_winners(conn))

    # Team records (derived from wbc_mart.app_game_results)
    sentences.extend(build_team_season_record(conn))

    # Player season stats (wbc_mart.app_player_season_stats)
    sentences.extend(build_player_season_sentences(conn))
    sentences.extend(build_player_season_adv_batting(conn))
    sentences.extend(build_player_season_adv_pitching(conn))
    sentences.extend(build_player_season_xbh_sb(conn))
    sentences.extend(build_player_season_leaders(conn))

    # Player bio (wbc_mart.app_game_detail)
    sentences.extend(build_player_bio_facts(conn))

    # Player game stats (wbc_mart.app_game_detail)
    sentences.extend(build_player_game_batting_sentences(conn))
    sentences.extend(build_player_game_pitching_sentences(conn))
    sentences.extend(build_player_game_notable_batting(conn))
    sentences.extend(build_player_game_notable_pitching(conn))
    sentences.extend(build_player_game_extra_batting(conn))

    # Team game stats (wbc_mart.app_game_detail)
    sentences.extend(build_team_game_batting_box(conn))
    sentences.extend(build_team_game_pitching_box(conn))
    sentences.extend(build_team_game_fielding_facts(conn))

    # Career (wbc_mart.app_player_season_stats)
    sentences.extend(build_player_career_sentences(conn))

    total = len(sentences)
    log.info(f"Total sentences to embed: {total}")

    if total == 0:
        log.warning("No sentences generated — exiting.")
        conn.close()
        return

    log.info(f"Loading model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)

    with conn.cursor() as cur:
        log.info("Preparing vectors.embeddings table...")
        cur.execute("""
            CREATE SCHEMA IF NOT EXISTS vectors;
            CREATE TABLE IF NOT EXISTS vectors.embeddings (
                id        BIGSERIAL PRIMARY KEY,
                content   TEXT    NOT NULL,
                embedding vector(384),
                metadata  JSONB
            );
        """)
        cur.execute("TRUNCATE vectors.embeddings;")

        log.info(f"Embedding and inserting in batches of {EMBED_BATCH_SIZE}...")
        for i in range(0, total, EMBED_BATCH_SIZE):
            batch      = sentences[i : i + EMBED_BATCH_SIZE]
            contents   = [b["content"] for b in batch]
            metadatas  = [json.dumps(b["metadata"]) for b in batch]
            embeddings = model.encode(contents, normalize_embeddings=True)

            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO vectors.embeddings (content, metadata, embedding) VALUES %s",
                [(c, m, e.tolist()) for c, m, e in zip(contents, metadatas, embeddings)],
            )

            done = i + len(batch)
            if done % 1000 == 0 or done == total:
                log.info(f"  {done} / {total} inserted")

        conn.commit()

    conn.close()
    log.info("Embedding pipeline complete.")


if __name__ == "__main__":
    run()
