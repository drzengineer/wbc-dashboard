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
    # Must check semi/quarter FIRST — "Semifinals" contains "final" as a substring
    # and would incorrectly match without this guard.
    label = (round_label or "").lower()
    if "semi" in label or "quarter" in label:
        return False
    return any(w in label for w in ("championship", "final", "gold"))


def is_semifinal(round_label: str) -> bool:
    # "semi" is unambiguous — no other round label contains it.
    return "semi" in (round_label or "").lower()


def is_quarterfinal(round_label: str) -> bool:
    # "quarter" is unambiguous — no other round label contains it.
    return "quarter" in (round_label or "").lower()


def is_knockout(round_label: str) -> bool:
    """Convenience: any elimination round."""
    return is_championship(round_label) or is_semifinal(round_label) or is_quarterfinal(round_label)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Game result sentences — 1 canonical sentence per completed game
# ─────────────────────────────────────────────────────────────────────────────

def build_game_result_sentences(conn) -> list[dict]:
    sql = """
        SELECT
            season, round_label, pool_display, official_date,
            venue_name, home_team_name, away_team_name,
            home_score, away_score, away_is_winner,
            winning_team_name, is_mercy_rule, game_pk
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
            if r["away_is_winner"]:
                ws, ls = r["away_score"], r["home_score"]
            else:
                ws, ls = r["home_score"], r["away_score"]

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
# 2. Standings sentences — 1 sentence per team per pool/round
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
            content = (
                f"In the {r['season']} WBC {r['pool_display']}, {r['team_name']} "
                f"went {rec} with a {rds} run differential."
            )
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
# 3. Player tournament sentences — 1 sentence per player per season
# ─────────────────────────────────────────────────────────────────────────────

def build_player_tournament_sentences(conn) -> list[dict]:
    """Skip players with no activity (games_played = 0)."""
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
            is_pitcher = r["position_type"] == "Pitcher" or (
                r["season_pitching_bf"] and r["season_pitching_bf"] > 0
            )
            if is_pitcher:
                try:
                    era = f"{float(r['season_pitching_era']):.2f}"
                except (TypeError, ValueError):
                    era = "N/A"
                ip  = f"{float(r['season_pitching_ip']):.1f}" if r["season_pitching_ip"] else "0.0"
                k   = r["season_pitching_so"] or 0
                w   = r["season_pitching_w"] or 0
                sv  = r["season_pitching_sv"] or 0
                content = (
                    f"In the {season} WBC, {name} ({country}, {pos}) had a {era} ERA "
                    f"with {k} strikeouts in {ip} IP ({w} W, {sv} SV) in {gp} games."
                )
            else:
                try:
                    avg_val = min(float(r["season_batting_avg"]), 0.999)
                    avg = f".{int(avg_val * 1000):03d}"
                except (TypeError, ValueError):
                    avg = ".000"
                hr  = r["season_batting_hr"] or 0
                rbi = r["season_batting_rbi"] or 0
                h   = r["season_batting_h"] or 0
                ab  = r["season_batting_ab"] or 0
                content = (
                    f"In the {season} WBC, {name} ({country}, {pos}) batted {avg} "
                    f"({h}-for-{ab}) with {hr} HR and {rbi} RBI in {gp} games."
                )
            rows.append({
                "content": content,
                "metadata": {
                    "source": "player_tournament_stats",
                    "season": season,
                    "full_name": name,
                    "represented_country": country,
                },
            })
    log.info(f"  player_tournament_stats: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 4. Player game sentences — 1 sentence per player per game (largest set)
# ─────────────────────────────────────────────────────────────────────────────

def build_player_game_sentences(conn) -> list[dict]:
    sql = """
        SELECT
            pgs.game_pk, pgs.season, pgs.official_date,
            pgs.full_name, pgs.represented_country,
            pgs.position_abbreviation, pgs.team_name,
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
                dec = ""
                if r["pitching_w"]:    dec = ", W"
                elif r["pitching_l"]:  dec = ", L"
                elif r["pitching_sv"]: dec = ", SV"
                content = (
                    f"In a {r['season']} WBC {round_str} game on {date_s} "
                    f"({matchup}), {name} ({country}) pitched {ip} IP, {er} ER, {k} K{dec}."
                )
            else:
                h  = r["batting_h"] or 0
                ab = r["batting_ab"] or 0
                hr = r["batting_hr"] or 0
                ri = r["batting_rbi"] or 0
                if hr and ri:  suffix = f" with {hr} HR and {ri} RBI"
                elif hr:       suffix = f" with {hr} HR"
                elif ri:       suffix = f" with {ri} RBI"
                else:          suffix = ""
                content = (
                    f"In a {r['season']} WBC {round_str} game on {date_s} "
                    f"({matchup}), {name} ({country}) went {h}-for-{ab}{suffix}."
                )
            rows.append({
                "content": content,
                "metadata": {
                    "source": "player_game_stats",
                    "season": r["season"],
                    "game_pk": r["game_pk"],
                    "full_name": name,
                },
            })
    log.info(f"  player_game_stats: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 5. Game result variants — 2 alternate phrasings per game
#    (variant 3 "was the winner" dropped — redundant with canonical sentence)
# ─────────────────────────────────────────────────────────────────────────────

def build_game_result_variants(conn) -> list[dict]:
    """
    2 alternate phrasings per completed game covering natural question vocabulary:
    'who won', 'who beat', 'champion', 'title', 'winner', 'defeated', 'beat'.
    Championship/semifinal/quarterfinal games get round-specific bonus phrases.
    """
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
            if r["away_is_winner"]:
                ws, ls = r["away_score"], r["home_score"]
            else:
                ws, ls = r["home_score"], r["away_score"]

            meta = {
                "source": "game_result_variants",
                "game_pk": r["game_pk"],
                "season": season,
                "round_label": rl,
            }

            # Variant 1 — "beat" phrasing
            rows.append({
                "content": f"{winner} beat {loser} {ws}-{ls} in the {season} WBC {rd}.",
                "metadata": meta,
            })

            # Variant 2 — "defeated" phrasing (neutral, no championship implication)
            rows.append({
                "content": f"In the {season} WBC {rd}, {winner} defeated {loser} {ws}-{ls}.",
                "metadata": meta,
            })

            # Bonus variants for knockout rounds
            if is_championship(rl):
                rows.append({
                    "content": (
                        f"{winner} won the {season} World Baseball Classic championship, "
                        f"defeating {loser} {ws}-{ls} in the final."
                    ),
                    "metadata": meta,
                })
                rows.append({
                    "content": f"The {season} WBC champion was {winner}. They defeated {loser} {ws}-{ls}.",
                    "metadata": meta,
                })
                rows.append({
                    "content": f"{winner} is the {season} WBC title holder, having beaten {loser} {ws}-{ls}.",
                    "metadata": meta,
                })

            elif is_semifinal(rl):
                rows.append({
                    "content": (
                        f"In the {season} WBC semifinals, {winner} eliminated {loser} {ws}-{ls} "
                        f"to advance to the championship."
                    ),
                    "metadata": meta,
                })

            elif is_quarterfinal(rl):
                rows.append({
                    "content": (
                        f"In the {season} WBC quarterfinals, {winner} knocked out {loser} {ws}-{ls}."
                    ),
                    "metadata": meta,
                })

    log.info(f"  game_result_variants: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 6. Knockout Q&A pairs — explicit question-answer sentences for every
#    championship, semifinal, and quarterfinal game.
# ─────────────────────────────────────────────────────────────────────────────

def build_knockout_qa_pairs(conn) -> list[dict]:
    """
    Explicit Q&A pair sentences for every knockout round game.
    Championship games get 10 pairs, semifinals and quarterfinals get 6 pairs each.
    These score 0.7+ against natural question phrasing vs ~0.4 for prose sentences.
    """
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
                LOWER(round_label) LIKE '%championship%'
             OR LOWER(round_label) LIKE '%gold%'
             OR LOWER(round_label) LIKE '%semi%'
             OR LOWER(round_label) LIKE '%quarter%'
             OR (
                  LOWER(round_label) LIKE '%final%'
                  AND LOWER(round_label) NOT LIKE '%semi%'
                  AND LOWER(round_label) NOT LIKE '%quarter%'
                )
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
            if r["away_is_winner"]:
                ws, ls = r["away_score"], r["home_score"]
            else:
                ws, ls = r["home_score"], r["away_score"]

            meta = {
                "source": "knockout_qa_pairs",
                "game_pk": r["game_pk"],
                "season": season,
                "round_label": rl,
            }

            if is_championship(rl):
                pairs = [
                    f"Who won the {season} WBC? {winner}.",
                    f"Who won the {season} World Baseball Classic? {winner}.",
                    f"Who won the {season} WBC championship? {winner}, defeating {loser} {ws}-{ls}.",
                    f"Who is the {season} WBC champion? {winner}.",
                    f"Who is the {season} World Baseball Classic champion? {winner}.",
                    f"Who won in {season}? {winner} won the WBC championship.",
                    f"What team won in {season}? {winner} won the World Baseball Classic.",
                    f"Who won the {season} WBC title? {winner} beat {loser} {ws}-{ls}.",
                    f"Who took home the {season} WBC trophy? {winner}.",
                    f"{loser} lost the {season} WBC championship to {winner} {ls}-{ws}.",
                ]
            elif is_semifinal(rl):
                pairs = [
                    f"Who won the {season} WBC semifinal? {winner}, defeating {loser} {ws}-{ls}.",
                    f"Who did {winner} beat in the {season} WBC semifinals? {loser} {ws}-{ls}.",
                    f"Who advanced to the {season} WBC championship from the semifinals? {winner}.",
                    f"Who was eliminated in the {season} WBC semifinals? {loser}, losing to {winner} {ls}-{ws}.",
                    f"Who won in the {season} WBC semis? {winner} over {loser} {ws}-{ls}.",
                    f"{winner} beat {loser} {ws}-{ls} in the {season} WBC semifinal.",
                ]
            elif is_quarterfinal(rl):
                pairs = [
                    f"Who won the {season} WBC quarterfinal? {winner}, defeating {loser} {ws}-{ls}.",
                    f"Who did {winner} beat in the {season} WBC quarterfinals? {loser} {ws}-{ls}.",
                    f"Who advanced past the {season} WBC quarterfinals? {winner}.",
                    f"Who was eliminated in the {season} WBC quarterfinals? {loser}, losing to {winner} {ls}-{ws}.",
                    f"Who won in the {season} WBC quarters? {winner} over {loser} {ws}-{ls}.",
                    f"{winner} beat {loser} {ws}-{ls} in the {season} WBC quarterfinal.",
                ]
            else:
                pairs = []

            for p in pairs:
                rows.append({"content": p, "metadata": meta})

    log.info(f"  knockout_qa_pairs: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 7. Team season summaries — overall record + champion flag per team/season
#    FIX vs Day 8: wins now counted from game_results (not standings),
#    so knockout round wins are included in the champion's record.
# ─────────────────────────────────────────────────────────────────────────────

def build_team_season_summaries(conn) -> list[dict]:
    """
    One summary sentence per team per season covering their full tournament record
    (pool + knockout rounds combined) and whether they won the championship.
    Answers: 'how did [team] do in [year]', 'who was undefeated', 'who won it all'.
    """
    sql = """
        WITH all_game_results AS (
            -- Count actual wins and losses from game_results (includes all rounds)
            SELECT season, winning_team_name AS team_name, 1 AS is_win
            FROM analytics.game_results
            WHERE abstract_game_state = 'Final'
              AND home_score IS NOT NULL

            UNION ALL

            SELECT
                season,
                CASE WHEN away_is_winner THEN home_team_name ELSE away_team_name END AS team_name,
                0 AS is_win
            FROM analytics.game_results
            WHERE abstract_game_state = 'Final'
              AND home_score IS NOT NULL
        ),
        team_totals AS (
            SELECT
                season,
                team_name,
                SUM(is_win)       AS total_wins,
                SUM(1 - is_win)   AS total_losses,
                COUNT(*)          AS total_gp
            FROM all_game_results
            GROUP BY season, team_name
        ),
        champions AS (
            SELECT DISTINCT season, winning_team_name AS champion
            FROM analytics.game_results
            WHERE abstract_game_state = 'Final'
              AND (
                    LOWER(round_label) LIKE '%championship%'
                 OR LOWER(round_label) LIKE '%gold%'
                 OR (
                      LOWER(round_label) LIKE '%final%'
                      AND LOWER(round_label) NOT LIKE '%semi%'
                      AND LOWER(round_label) NOT LIKE '%quarter%'
                    )
              )
        ),
        -- Pool run differential still comes from standings (it's pool-only by design)
        pool_rd AS (
            SELECT season, team_name, SUM(pool_run_differential) AS total_rd
            FROM analytics.standings
            GROUP BY season, team_name
        )
        SELECT
            tt.season,
            tt.team_name,
            tt.total_wins,
            tt.total_losses,
            tt.total_gp,
            COALESCE(rd.total_rd, 0) AS total_rd,
            (c.champion IS NOT NULL)  AS won_championship
        FROM team_totals tt
        LEFT JOIN pool_rd rd ON rd.season = tt.season AND rd.team_name = tt.team_name
        LEFT JOIN champions c ON c.season = tt.season AND c.champion = tt.team_name
        ORDER BY tt.season, tt.total_wins DESC
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            team   = r["team_name"]
            season = r["season"]
            wins   = r["total_wins"]
            losses = r["total_losses"]
            rd     = r["total_rd"] or 0
            rds    = f"+{rd}" if rd > 0 else str(rd)
            champ  = r["won_championship"]

            if champ:
                content = (
                    f"In the {season} WBC, {team} finished {wins}-{losses} overall "
                    f"with a {rds} run differential and won the championship."
                )
            else:
                content = (
                    f"In the {season} WBC, {team} finished {wins}-{losses} overall "
                    f"with a {rds} run differential."
                )

            rows.append({
                "content": content,
                "metadata": {
                    "source": "team_season_summary",
                    "season": season,
                    "team_name": team,
                    "won_championship": champ,
                },
            })

    log.info(f"  team_season_summary: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 8. Pool winner sentences — NEW in Day 9
#    "Japan won the 2023 WBC Pool A, finishing 4-0."
# ─────────────────────────────────────────────────────────────────────────────

def build_pool_winner_sentences(conn) -> list[dict]:
    """
    One sentence per pool per season for the team with the best pool record.
    Answers: 'who won Pool A', 'which team topped Pool B in 2023'.
    Only emits for pool-play rounds (not knockout rounds).
    """
    sql = """
        SELECT DISTINCT ON (season, pool_display)
            season, pool_display, team_name, pool_wins, pool_losses
        FROM analytics.standings
        WHERE pool_display IS NOT NULL
          AND LOWER(pool_display) LIKE '%pool%'
        ORDER BY season, pool_display, pool_wins DESC, pool_losses ASC
    """
    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            team   = r["team_name"]
            season = r["season"]
            pool   = r["pool_display"]
            wins   = r["pool_wins"]
            losses = r["pool_losses"]
            content = (
                f"{team} won the {season} WBC {pool}, finishing {wins}-{losses}."
            )
            rows.append({
                "content": content,
                "metadata": {
                    "source": "pool_winners",
                    "season": season,
                    "pool_display": pool,
                    "team_name": team,
                },
            })
    log.info(f"  pool_winners: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 9. Season stat leaders — batting avg / HR / RBI / ERA leaders per season
# ─────────────────────────────────────────────────────────────────────────────

def build_season_stat_leaders(conn) -> list[dict]:
    """
    Batting avg leader, HR leader, RBI leader, ERA leader (min 5 IP) per season.
    Answers: 'who led in HR', 'batting average leader', 'best ERA in [year]'.
    """
    rows = []

    batting_sql = """
        SELECT DISTINCT ON (season)
            season, full_name, represented_country,
            season_batting_avg, season_batting_h, season_batting_ab
        FROM analytics.player_tournament_stats
        WHERE season_batting_ab >= 10
          AND games_played > 0
        ORDER BY season, season_batting_avg DESC NULLS LAST
    """
    hr_sql = """
        SELECT DISTINCT ON (season)
            season, full_name, represented_country, season_batting_hr
        FROM analytics.player_tournament_stats
        WHERE games_played > 0
          AND season_batting_hr > 0
        ORDER BY season, season_batting_hr DESC NULLS LAST
    """
    rbi_sql = """
        SELECT DISTINCT ON (season)
            season, full_name, represented_country, season_batting_rbi
        FROM analytics.player_tournament_stats
        WHERE games_played > 0
          AND season_batting_rbi > 0
        ORDER BY season, season_batting_rbi DESC NULLS LAST
    """
    era_sql = """
        SELECT DISTINCT ON (season)
            season, full_name, represented_country,
            season_pitching_era, season_pitching_ip, season_pitching_so
        FROM analytics.player_tournament_stats
        WHERE season_pitching_ip >= 5
          AND games_played > 0
        ORDER BY season, season_pitching_era ASC NULLS LAST
    """

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:

        cur.execute(batting_sql)
        for r in cur.fetchall():
            try:
                avg_val = min(float(r["season_batting_avg"]), 0.999)
                avg = f".{int(avg_val * 1000):03d}"
            except (TypeError, ValueError):
                avg = ".000"
            h  = r["season_batting_h"] or 0
            ab = r["season_batting_ab"] or 0
            rows.append({
                "content": (
                    f"The batting average leader in the {r['season']} WBC was "
                    f"{r['full_name']} ({r['represented_country']}) at {avg} ({h}-for-{ab})."
                ),
                "metadata": {
                    "source": "season_stat_leaders",
                    "season": r["season"],
                    "stat": "batting_avg",
                    "full_name": r["full_name"],
                },
            })

        cur.execute(hr_sql)
        for r in cur.fetchall():
            hr = r["season_batting_hr"] or 0
            rows.append({
                "content": (
                    f"The home run leader in the {r['season']} WBC was "
                    f"{r['full_name']} ({r['represented_country']}) with {hr} HR."
                ),
                "metadata": {
                    "source": "season_stat_leaders",
                    "season": r["season"],
                    "stat": "hr",
                    "full_name": r["full_name"],
                },
            })

        cur.execute(rbi_sql)
        for r in cur.fetchall():
            rbi = r["season_batting_rbi"] or 0
            rows.append({
                "content": (
                    f"The RBI leader in the {r['season']} WBC was "
                    f"{r['full_name']} ({r['represented_country']}) with {rbi} RBI."
                ),
                "metadata": {
                    "source": "season_stat_leaders",
                    "season": r["season"],
                    "stat": "rbi",
                    "full_name": r["full_name"],
                },
            })

        cur.execute(era_sql)
        for r in cur.fetchall():
            try:
                era = f"{float(r['season_pitching_era']):.2f}"
            except (TypeError, ValueError):
                era = "N/A"
            ip = f"{float(r['season_pitching_ip']):.1f}" if r["season_pitching_ip"] else "0.0"
            k  = r["season_pitching_so"] or 0
            rows.append({
                "content": (
                    f"The ERA leader in the {r['season']} WBC (min. 5 IP) was "
                    f"{r['full_name']} ({r['represented_country']}) "
                    f"with a {era} ERA in {ip} IP and {k} strikeouts."
                ),
                "metadata": {
                    "source": "season_stat_leaders",
                    "season": r["season"],
                    "stat": "era",
                    "full_name": r["full_name"],
                },
            })

    log.info(f"  season_stat_leaders: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 10. Top performer per game — best hitter + best pitcher per completed game
# ─────────────────────────────────────────────────────────────────────────────

def build_top_performer_per_game(conn) -> list[dict]:
    """
    Best hitter (most RBI, tiebreak: HR then H) and best pitcher (most K, min 1 IP)
    per completed game.  Only emits hitters with at least 1 RBI or HR.
    Answers: 'who had the best game', 'standout performer', 'who drove in the most runs'.
    """
    hitter_sql = """
        SELECT DISTINCT ON (pgs.game_pk)
            pgs.game_pk, pgs.season, pgs.official_date,
            pgs.full_name, pgs.represented_country,
            pgs.batting_h, pgs.batting_ab, pgs.batting_hr, pgs.batting_rbi,
            gr.round_label, gr.pool_display,
            gr.home_team_name, gr.away_team_name
        FROM analytics.player_game_stats pgs
        JOIN analytics.game_results gr ON gr.game_pk = pgs.game_pk
        WHERE gr.abstract_game_state = 'Final'
          AND pgs.batting_ab > 0
        ORDER BY
            pgs.game_pk,
            pgs.batting_rbi DESC NULLS LAST,
            pgs.batting_hr  DESC NULLS LAST,
            pgs.batting_h   DESC NULLS LAST
    """
    pitcher_sql = """
        SELECT DISTINCT ON (pgs.game_pk)
            pgs.game_pk, pgs.season, pgs.official_date,
            pgs.full_name, pgs.represented_country,
            pgs.pitching_ip, pgs.pitching_er, pgs.pitching_so,
            pgs.pitching_w, pgs.pitching_sv,
            gr.round_label, gr.pool_display,
            gr.home_team_name, gr.away_team_name
        FROM analytics.player_game_stats pgs
        JOIN analytics.game_results gr ON gr.game_pk = pgs.game_pk
        WHERE gr.abstract_game_state = 'Final'
          AND pgs.pitching_ip >= 1
        ORDER BY
            pgs.game_pk,
            pgs.pitching_so DESC NULLS LAST,
            pgs.pitching_ip DESC NULLS LAST
    """

    rows = []
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:

        cur.execute(hitter_sql)
        for r in cur.fetchall():
            name    = r["full_name"] or "Unknown"
            country = r["represented_country"] or "?"
            date_s  = fmt_date(r["official_date"])
            rd      = r["pool_display"] or r["round_label"] or "game"
            matchup = f"{r['away_team_name']} vs {r['home_team_name']}"
            h   = r["batting_h"] or 0
            ab  = r["batting_ab"] or 0
            hr  = r["batting_hr"] or 0
            rbi = r["batting_rbi"] or 0

            # Skip zero-impact hitters
            if rbi == 0 and hr == 0:
                continue

            if hr and rbi:  perf = f"went {h}-for-{ab} with {hr} HR and {rbi} RBI"
            elif rbi:       perf = f"went {h}-for-{ab} with {rbi} RBI"
            elif hr:        perf = f"went {h}-for-{ab} with {hr} HR"
            else:           perf = f"went {h}-for-{ab}"

            rows.append({
                "content": (
                    f"The standout hitter in the {r['season']} WBC {rd} game on {date_s} "
                    f"({matchup}) was {name} ({country}), who {perf}."
                ),
                "metadata": {
                    "source": "top_performer_per_game",
                    "game_pk": r["game_pk"],
                    "season": r["season"],
                    "role": "hitter",
                    "full_name": name,
                },
            })

        cur.execute(pitcher_sql)
        for r in cur.fetchall():
            name    = r["full_name"] or "Unknown"
            country = r["represented_country"] or "?"
            date_s  = fmt_date(r["official_date"])
            rd      = r["pool_display"] or r["round_label"] or "game"
            matchup = f"{r['away_team_name']} vs {r['home_team_name']}"
            ip  = f"{float(r['pitching_ip']):.1f}"
            er  = r["pitching_er"] or 0
            k   = r["pitching_so"] or 0
            dec = ""
            if r["pitching_w"]:    dec = ", earning the win"
            elif r["pitching_sv"]: dec = ", earning the save"

            rows.append({
                "content": (
                    f"The standout pitcher in the {r['season']} WBC {rd} game on {date_s} "
                    f"({matchup}) was {name} ({country}), who threw {ip} IP, {er} ER, {k} K{dec}."
                ),
                "metadata": {
                    "source": "top_performer_per_game",
                    "game_pk": r["game_pk"],
                    "season": r["season"],
                    "role": "pitcher",
                    "full_name": name,
                },
            })

    log.info(f"  top_performer_per_game: {len(rows)} sentences")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Local embedding
# ─────────────────────────────────────────────────────────────────────────────

def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch using SentenceTransformer (local, free, fast)."""
    global model
    embeddings = model.encode(
        texts,
        batch_size=EMBED_BATCH_SIZE,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


# ─────────────────────────────────────────────────────────────────────────────
# Upsert
# ─────────────────────────────────────────────────────────────────────────────

def truncate_embeddings(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("TRUNCATE vectors.embeddings RESTART IDENTITY;")
    conn.commit()
    log.info("Truncated vectors.embeddings — starting fresh insert.")


def upsert_embeddings(conn, rows: list[dict], embeddings: list[list[float]]) -> None:
    records = [
        (row["content"], psycopg2.extras.Json(row["metadata"]), embedding)
        for row, embedding in zip(rows, embeddings)
    ]
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO vectors.embeddings (content, metadata, embedding) VALUES %s",
            records,
            template="(%s, %s, %s::vector)",
            page_size=500,
        )
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestration
# ─────────────────────────────────────────────────────────────────────────────

def run() -> None:
    global model
    log.info("=== WBC Embedding Refresh — Local all-MiniLM-L6-v2 ===")

    log.info(f"Loading {EMBED_MODEL}...")
    model = SentenceTransformer(EMBED_MODEL)
    log.info("Model loaded.")

    conn = get_connection()
    log.info("Connected to Supabase.")

    log.info("Building sentences from analytics tables...")
    all_rows = (
        # ── Core builders ────────────────────────────────────────────────────
        build_game_result_sentences(conn)       # 1. 1 sentence per game
        + build_standings_sentences(conn)        # 2. 1 sentence per team per pool/round
        + build_player_tournament_sentences(conn) # 3. 1 sentence per player per season
        + build_player_game_sentences(conn)      # 4. 1 sentence per player per game (~14k)
        # ── Enrichment builders ──────────────────────────────────────────────
        + build_game_result_variants(conn)       # 5. 2 alt phrasings + knockout bonuses
        + build_knockout_qa_pairs(conn)          # 6. Q&A pairs for knockout rounds
        + build_team_season_summaries(conn)      # 7. overall record (from game_results)
        + build_pool_winner_sentences(conn)      # 8. pool winner sentences (NEW)
        + build_season_stat_leaders(conn)        # 9. avg/HR/RBI/ERA leaders per season
        + build_top_performer_per_game(conn)     # 10. standout hitter + pitcher per game
        # head_to_head removed — low ROI, misleading multi-game aggregation
    )
    total = len(all_rows)
    log.info(f"Total sentences to embed: {total:,}")

    truncate_embeddings(conn)

    num_batches = (total + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE
    log.info(f"Embedding in {num_batches} batches of {EMBED_BATCH_SIZE}...")

    for batch_idx in range(num_batches):
        start = batch_idx * EMBED_BATCH_SIZE
        end   = min(start + EMBED_BATCH_SIZE, total)
        batch = all_rows[start:end]
        texts = [r["content"] for r in batch]

        source_tag = batch[0]["metadata"].get("source", "?")
        log.info(f"  Batch {batch_idx + 1}/{num_batches} ({len(texts)} sentences, {source_tag})")

        try:
            vectors = embed_batch(texts)
        except Exception as exc:
            log.error(f"  Batch {batch_idx + 1} failed: {exc}")
            sys.exit(1)

        upsert_embeddings(conn, batch, vectors)

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM vectors.embeddings;")
        count = cur.fetchone()[0]
    log.info(f"Done! vectors.embeddings now has {count:,} rows (dim={EMBED_DIM}).")

    conn.close()


if __name__ == "__main__":
    run()