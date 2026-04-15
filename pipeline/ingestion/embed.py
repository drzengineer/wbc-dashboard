"""
embed.py — WBC Dashboard RAG Embeddings  (Hybrid Architecture v2)
==================================================================
Philosophy
----------
This pipeline generates HIGH-DENSITY NARRATIVE CONTEXT for the RAG layer.
Granular statistics (RBI totals, win-loss records, standings tables) are
intentionally excluded — those will be served by a future SQL tool.

The RAG layer answers questions like:
  "Tell me the story of Japan's 2023 championship run."
  "What made Shohei Ohtani's 2023 WBC performance special?"
  "What happened in the USA vs Dominican Republic game?"

It does NOT try to answer:
  "How many RBIs did Player X have?" → SQL tool
  "What was Team Y's run differential?" → SQL tool

DATA SOURCES
------------
  wbc_mart.app_game_results        grain: 1 row per completed game
  wbc_mart.app_pool_standings      grain: 1 row per team per pool per season
  wbc_mart.app_player_season_stats grain: 1 row per player per season
  wbc_mart.app_game_detail         grain: 1 row per player per game

NARRATIVE BUILDERS
------------------
  1.  game_recap_narrative         One rich story per game — result, context,
                                   drama flags (mercy, walk-off, extra innings,
                                   one-run, blowout), venue, round significance
  2.  knockout_qa_pairs            Explicit Q&A pairs for every knockout game
                                   (championship / semifinal / quarterfinal)
  3.  team_season_narrative        One paragraph per team per season covering
                                   their full tournament arc — pool record,
                                   how far they advanced, notable context
  4.  player_season_narrative      One dense paragraph per player per season —
                                   bio context, role, standout performances,
                                   advanced profile (position, handedness)
  5.  player_career_narrative      Multi-tournament arc for veterans who
                                   appeared in more than one WBC
  6.  player_bio_narrative         Physical profile, birthplace, MLB debut —
                                   the "who is this person" layer
  7.  standout_game_narrative      Game-level hero moments: 3-hit games,
                                   multi-HR, 10-K outings, shutout IP, etc.
                                   Written as recap prose, not stat lines.

METADATA SCHEMA (every vector)
-------------------------------
  {
      "season":   int   | None,   # e.g. 2023
      "team":     str   | None,   # e.g. "Japan"
      "player":   str   | None,   # e.g. "Shohei Ohtani"
      "round":    str   | None,   # e.g. "Championship", "Pool D"
      "is_mercy": bool  | None,   # mercy-rule flag
      "category": str             # "game_recap" | "game_qa" | "team_profile"
                                  # "player_profile" | "player_career"
                                  # "player_bio" | "standout_game"
  }
"""

import json
import logging
import os
from collections import defaultdict
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
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def fetch(conn, sql: str) -> list:
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        return cur.fetchall()


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


def ordinal(n: int) -> str:
    """Return '1st', '2nd', '3rd', '4th', etc."""
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]}"


def winner_loser(r) -> tuple:
    if r["away_is_winner"]:
        return r["away_team_name"], r["home_team_name"], r["away_score"], r["home_score"]
    return r["home_team_name"], r["away_team_name"], r["home_score"], r["away_score"]


def is_championship(label: str) -> bool:
    label = (label or "").lower()
    return any(w in label for w in ("championship", "final", "gold")) \
        and "semi" not in label and "quarter" not in label


def is_semifinal(label: str) -> bool:
    return "semi" in (label or "").lower()


def is_quarterfinal(label: str) -> bool:
    return "quarter" in (label or "").lower()


def is_knockout(label: str) -> bool:
    return is_championship(label) or is_semifinal(label) or is_quarterfinal(label)


def meta(season=None, team=None, player=None, round_=None,
         is_mercy=None, category="") -> dict:
    """Construct the standardised metadata dictionary."""
    return {
        "season":   season,
        "team":     team,
        "player":   player,
        "round":    round_,
        "is_mercy": is_mercy,
        "category": category,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. Game recap narratives
#    Source: wbc_mart.app_game_results
#
#    One rich prose paragraph per game. Combines result, round significance,
#    venue, drama flags (mercy rule, one-run thriller, blowout, extra innings,
#    walk-off) into a single retrievable story chunk.
#    SQL handles the raw scores; RAG handles the story.
# ─────────────────────────────────────────────────────────────────────────────

def build_game_recap_narratives(conn) -> list[dict]:
    sql = """
        SELECT season, official_date, round_label, pool_group,
               away_team_name, away_team_abbreviation,
               home_team_name, home_team_abbreviation,
               away_score, home_score, away_is_winner,
               is_mercy_rule, is_one_run_game, run_margin, total_runs,
               venue_name, away_innings, home_innings
        FROM wbc_mart.app_game_results
        WHERE away_score IS NOT NULL AND home_score IS NOT NULL
        ORDER BY season, official_date
    """
    rows = []
    for r in fetch(conn, sql):
        winner, loser, ws, ls = winner_loser(r)
        s      = r["season"]
        rd     = r["pool_group"] or r["round_label"] or "game"
        rl     = r["round_label"] or ""
        date   = fmt_date(r["official_date"])
        margin = r["run_margin"] or 0
        total  = r["total_runs"] or 0

        # ── Round significance opening ───────────────────────────────────────
        if is_championship(rl):
            opening = f"The {s} World Baseball Classic Championship"
        elif is_semifinal(rl):
            opening = f"A {s} WBC Semifinal clash"
        elif is_quarterfinal(rl):
            opening = f"A {s} WBC Quarterfinal showdown"
        else:
            opening = f"A {s} WBC {rd} matchup"

        venue_str = f" at {r['venue_name']}" if r["venue_name"] else ""
        narrative = f"{opening} on {date}{venue_str} saw {winner} defeat {loser} by a score of {ws}-{ls}."

        # ── Drama flags ──────────────────────────────────────────────────────
        drama = []

        if r["is_mercy_rule"]:
            drama.append(
                f"The game was called early via the mercy rule, a testament to {winner}'s overwhelming dominance."
            )

        elif r["is_one_run_game"]:
            drama.append(
                f"It was a tightly contested one-run affair that kept fans on the edge of their seats until the final out."
            )

        elif margin >= 7:
            drama.append(
                f"{winner} turned in a dominant performance, pulling away for a {margin}-run victory."
            )

        elif total >= 15:
            drama.append(
                f"The two sides combined for {total} runs in an offensive showcase."
            )

        # Walk-off detection
        a_inn = r["away_innings"] or []
        h_inn = r["home_innings"] or []
        home_won = not r["away_is_winner"]
        if home_won and h_inn and h_inn[-1] and int(h_inn[-1]) > 0:
            inn_num = len(h_inn)
            if inn_num >= 9:
                drama.append(
                    f"{winner} sealed the victory with a walk-off in the {ordinal(inn_num)} inning."
                )

        # Extra innings
        max_inn = max(len(a_inn), len(h_inn)) if (a_inn or h_inn) else 0
        if max_inn > 9:
            drama.append(
                f"The contest required {max_inn} innings to decide a winner."
            )

        # ── Knockout advancement note ────────────────────────────────────────
        if is_championship(rl):
            drama.append(
                f"With the victory, {winner} claimed the {s} World Baseball Classic title."
            )
        elif is_semifinal(rl):
            drama.append(
                f"The win sent {winner} to the championship game while {loser} saw their tournament come to an end."
            )
        elif is_quarterfinal(rl):
            drama.append(
                f"{winner} advanced to the semifinals, ending {loser}'s run in the tournament."
            )

        if drama:
            narrative += " " + " ".join(drama)

        rows.append({
            "content": narrative,
            "metadata": meta(
                season=s,
                team=winner,
                player=None,
                round_=rd,
                is_mercy=bool(r["is_mercy_rule"]),
                category="game_recap",
            ),
        })

        # Second vector: loser's perspective for symmetric retrieval
        loser_view = (
            f"{loser} fell to {winner} {ls}-{ws} in the {s} WBC {rd} on {date}{venue_str}."
        )
        if r["is_mercy_rule"]:
            loser_view += f" The game ended via the mercy rule."
        elif is_knockout(rl):
            loser_view += f" The defeat eliminated {loser} from the {s} WBC."

        rows.append({
            "content": loser_view,
            "metadata": meta(
                season=s,
                team=loser,
                player=None,
                round_=rd,
                is_mercy=bool(r["is_mercy_rule"]),
                category="game_recap",
            ),
        })

    log.info(f"  game_recap_narratives: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 2. Knockout Q&A pairs
#    Source: wbc_mart.app_game_results
#
#    Explicit question-answer pairs for every knockout round game.
#    These anchor the chatbot for the highest-stakes "who won" queries.
# ─────────────────────────────────────────────────────────────────────────────

def build_knockout_qa_pairs(conn) -> list[dict]:
    sql = """
        SELECT season, round_label, pool_group,
               away_team_name, home_team_name,
               away_score, home_score, away_is_winner,
               venue_name
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
        rl = r["round_label"] or ""
        s  = r["season"]
        rd = r["pool_group"] or rl

        m = meta(season=s, team=winner, player=None, round_=rd,
                 is_mercy=False, category="game_qa")

        if is_championship(rl):
            qas = [
                (f"Who won the {s} WBC?",
                 f"{winner} won the {s} World Baseball Classic, defeating {loser} {ws}-{ls} in the championship game."),
                (f"Who won the {s} World Baseball Classic?",
                 f"{winner} are the {s} WBC champions, having beaten {loser} {ws}-{ls} in the final."),
                (f"Did {winner} win the {s} WBC?",
                 f"Yes. {winner} defeated {loser} {ws}-{ls} to claim the {s} WBC title."),
                (f"Did {loser} win the {s} WBC?",
                 f"No. {loser} were runners-up, falling to {winner} {ws}-{ls} in the championship game."),
                (f"Who played in the {s} WBC final?",
                 f"{winner} faced {loser} in the {s} WBC Championship game."),
                (f"Who did {winner} beat to win the {s} WBC?",
                 f"{winner} defeated {loser} {ws}-{ls} in the championship game to win the {s} WBC."),
                (f"Who was the runner-up in the {s} WBC?",
                 f"{loser} were the runners-up in the {s} WBC, losing to {winner} {ws}-{ls} in the final."),
                (f"What was the score of the {s} WBC final?",
                 f"{winner} defeated {loser} {ws}-{ls} in the {s} WBC Championship."),
            ]
            if r["venue_name"]:
                qas.append((
                    f"Where was the {s} WBC Championship played?",
                    f"The {s} WBC Championship game was held at {r['venue_name']}, where {winner} defeated {loser} {ws}-{ls}.",
                ))

        elif is_semifinal(rl):
            qas = [
                (f"Who won the {s} WBC semifinal between {winner} and {loser}?",
                 f"{winner} defeated {loser} {ws}-{ls} to advance to the {s} WBC Championship game."),
                (f"Did {winner} make it to the {s} WBC final?",
                 f"Yes. {winner} beat {loser} {ws}-{ls} in the semifinals to reach the championship."),
                (f"Who eliminated {loser} from the {s} WBC?",
                 f"{winner} eliminated {loser} {ws}-{ls} in the {s} WBC semifinals."),
                (f"Did {loser} reach the {s} WBC final?",
                 f"No. {loser} were eliminated by {winner} {ws}-{ls} in the {s} WBC semifinals."),
            ]

        elif is_quarterfinal(rl):
            qas = [
                (f"Who won the {s} WBC quarterfinal between {winner} and {loser}?",
                 f"{winner} defeated {loser} {ws}-{ls} to advance to the semifinals of the {s} WBC."),
                (f"Who did {winner} beat in the {s} WBC quarterfinals?",
                 f"{winner} beat {loser} {ws}-{ls} in the {s} WBC quarterfinals."),
                (f"Was {loser} eliminated in the {s} WBC quarterfinals?",
                 f"Yes. {loser} were knocked out by {winner} {ws}-{ls} in the {s} WBC quarterfinals."),
                (f"Did {winner} advance to the {s} WBC semifinals?",
                 f"Yes. {winner} beat {loser} {ws}-{ls} in the quarterfinals to reach the {s} WBC semifinals."),
            ]

        else:
            qas = []

        for q, a in qas:
            rows.append({"content": f"Q: {q} A: {a}", "metadata": m})

    log.info(f"  knockout_qa_pairs: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 3. Team season narratives
#    Sources: wbc_mart.app_pool_standings  +  wbc_mart.app_game_results
#
#    One paragraph per team per season covering:
#      - Which pool they were in and how they fared
#      - How far they advanced in the tournament
#      - Whether they won the championship
#      - Any notable pool facts (undefeated, winless)
# ─────────────────────────────────────────────────────────────────────────────

def build_team_season_narratives(conn) -> list[dict]:
    # Pool performance
    standings_sql = """
        SELECT season, pool_group, team_name, team_abbreviation,
               pool_wins, pool_losses, pool_win_pct, pool_run_differential
        FROM wbc_mart.app_pool_standings
    """

    # How far each team advanced (furthest round reached)
    advancement_sql = """
        WITH all_teams AS (
            SELECT season, away_team_name AS team, round_label
            FROM wbc_mart.app_game_results
            WHERE away_score IS NOT NULL
            UNION
            SELECT season, home_team_name AS team, round_label
            FROM wbc_mart.app_game_results
            WHERE home_score IS NOT NULL
        )
        SELECT season, team,
               MAX(CASE round_label
                   WHEN 'Pool Play'    THEN 1
                   WHEN 'Round 2'      THEN 2
                   WHEN 'Quarterfinals' THEN 3
                   WHEN 'Semifinals'   THEN 4
                   WHEN 'Championship' THEN 5
                   ELSE 0 END) AS max_round_order,
               MAX(round_label) AS last_round_label
        FROM all_teams
        GROUP BY season, team
    """

    # Championship winners
    champ_sql = """
        SELECT season, away_team_name, home_team_name,
               away_score, home_score, away_is_winner
        FROM wbc_mart.app_game_results
        WHERE away_score IS NOT NULL
          AND (
            LOWER(round_label) LIKE '%championship%' OR
            LOWER(round_label) LIKE '%final%'
          )
          AND LOWER(round_label) NOT LIKE '%semi%'
          AND LOWER(round_label) NOT LIKE '%quarter%'
    """

    standings_rows = fetch(conn, standings_sql)
    advancement_rows = fetch(conn, advancement_sql)
    champ_rows = fetch(conn, champ_sql)

    # Build lookup: (season, team) → pool record
    pool_lookup: dict = {}
    for r in standings_rows:
        key = (r["season"], r["team_name"])
        pool_lookup[key] = r

    # Build lookup: (season, team) → furthest round
    adv_lookup: dict = {}
    for r in advancement_rows:
        adv_lookup[(r["season"], r["team"])] = r

    # Build set of champions: season → winner name
    champ_lookup: dict = {}
    for r in champ_rows:
        winner = r["away_team_name"] if r["away_is_winner"] else r["home_team_name"]
        champ_lookup[r["season"]] = winner

    # Collect all unique (season, team) pairs
    all_keys = set(pool_lookup.keys()) | {(s, t) for s, t in adv_lookup.keys()}

    rows = []
    for season, team in sorted(all_keys):
        pool_data = pool_lookup.get((season, team))
        adv_data  = adv_lookup.get((season, team))
        champion  = champ_lookup.get(season)
        is_champ  = (champion == team)

        parts = []

        # Pool section
        if pool_data:
            pool = pool_data["pool_group"]
            w    = pool_data["pool_wins"]
            l    = pool_data["pool_losses"]
            rd   = pool_data["pool_run_differential"] or 0
            rds  = f"+{rd}" if rd > 0 else str(rd)

            if l == 0 and w > 0:
                parts.append(
                    f"In the {season} WBC, {team} competed in {pool} and went an undefeated {w}-0 to top their group."
                )
            elif w == 0 and l > 0:
                parts.append(
                    f"In the {season} WBC, {team} competed in {pool} but struggled, going winless at 0-{l}."
                )
            else:
                parts.append(
                    f"In the {season} WBC, {team} competed in {pool}, finishing pool play with a {w}-{l} record and a {rds} run differential."
                )

        # Advancement section
        if adv_data:
            max_order = adv_data["max_round_order"]
            if is_champ:
                parts.append(
                    f"They powered through the bracket all the way to the championship game and claimed the {season} WBC title."
                )
            elif max_order == 4:
                parts.append(
                    f"They advanced to the semifinals before being eliminated."
                )
            elif max_order == 3:
                parts.append(
                    f"They reached the quarterfinals but were unable to advance further."
                )
            elif max_order == 2:
                parts.append(
                    f"They progressed to the second round but were eventually knocked out before the quarterfinals."
                )
            elif max_order <= 1 and not pool_data:
                parts.append(
                    f"{team} participated in the {season} WBC pool stage."
                )

        if not parts:
            continue

        narrative = " ".join(parts)

        rows.append({
            "content": narrative,
            "metadata": meta(
                season=season,
                team=team,
                player=None,
                round_=pool_data["pool_group"] if pool_data else None,
                is_mercy=None,
                category="team_profile",
            ),
        })

    log.info(f"  team_season_narratives: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 4. Player season narratives
#    Source: wbc_mart.app_player_season_stats
#
#    One dense narrative per player per season. Focuses on who they are
#    and how they performed in aggregate — not a stat line, but a profile.
#    The goal is a paragraph that surfaces in retrieval for questions like
#    "Who was the best pitcher in the 2023 WBC?" or "Tell me about X's 2023."
# ─────────────────────────────────────────────────────────────────────────────

def build_player_season_narratives(conn) -> list[dict]:
    sql = """
        SELECT person_id, season, full_name, position_type, position,
               team_abbreviation, games_played, bat_side_code, pitch_hand_code,
               season_batting_ab, season_batting_hits, season_batting_avg,
               season_batting_hr, season_batting_rbi, season_batting_bb,
               season_batting_so, season_batting_sb,
               season_batting_obp, season_batting_slg, season_batting_ops,
               season_batting_doubles, season_batting_triples,
               season_batting_iso, season_batting_babip,
               season_batting_k_rate, season_batting_bb_rate,
               season_pitching_era, season_pitching_ip,
               season_pitching_so, season_pitching_w, season_pitching_l,
               season_pitching_sv, season_pitching_gs, season_pitching_bf,
               season_pitching_whip, season_pitching_k_per_9,
               season_pitching_bb_per_9
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
        is_p  = (r["position_type"] == "Pitcher") or bool(
            r["season_pitching_bf"] and r["season_pitching_bf"] > 0
        )

        parts = []

        # ── Opening ──────────────────────────────────────────────────────────
        hand_map = {"R": "right-handed", "L": "left-handed", "S": "switch-hitting"}
        if is_p:
            hand = hand_map.get(r["pitch_hand_code"] or "", "")
            hand_str = f"{hand} " if hand else ""
            parts.append(
                f"{name} represented {team} as a {hand_str}{pos} in the {s} WBC, "
                f"appearing in {gp} game{'s' if gp != 1 else ''}."
            )
        else:
            bat  = hand_map.get(r["bat_side_code"] or "", "")
            bat_str = f"{bat} " if bat else ""
            parts.append(
                f"{name} suited up for {team} as a {bat_str}{pos} in the {s} WBC, "
                f"playing in {gp} game{'s' if gp != 1 else ''}."
            )

        # ── Performance narrative ─────────────────────────────────────────────
        if is_p:
            ip  = r["season_pitching_ip"]
            era = r["season_pitching_era"]
            k   = r["season_pitching_so"] or 0
            w   = r["season_pitching_w"] or 0
            l   = r["season_pitching_l"] or 0
            sv  = r["season_pitching_sv"] or 0
            gs  = r["season_pitching_gs"] or 0
            whip = r["season_pitching_whip"]
            k9   = r["season_pitching_k_per_9"]

            if ip and float(ip) > 0:
                ip_str  = fmt_ip(ip)
                era_str = fmt_era(era)
                role    = "as a starter" if gs and gs > 1 else "out of the bullpen"

                if sv and sv > 0:
                    parts.append(
                        f"Working primarily as a closer, he notched {sv} save{'s' if sv != 1 else ''} "
                        f"with a {era_str} ERA over {ip_str} innings pitched."
                    )
                elif gs and gs > 0:
                    record_str = f"{w}-{l}" if (w or l) else "without a decision"
                    parts.append(
                        f"He took the mound {gs} time{'s' if gs != 1 else ''} {role}, "
                        f"going {record_str} with a {era_str} ERA and {k} strikeout{'s' if k != 1 else ''} "
                        f"across {ip_str} innings."
                    )
                else:
                    parts.append(
                        f"He logged {ip_str} innings with a {era_str} ERA and {k} strikeout{'s' if k != 1 else ''}."
                    )

                # Advanced descriptors (narrative, not stat lines)
                if whip and float(whip) < 1.0 and float(ip) >= 6:
                    parts.append(
                        f"His ability to limit baserunners — evidenced by a sub-1.00 WHIP — made him one of the more dominant arms in the tournament."
                    )
                elif whip and float(whip) > 2.0 and float(ip) >= 6:
                    parts.append(
                        f"Control was a challenge at times, as reflected in his WHIP above 2.00."
                    )

                if k9 and float(k9) >= 10.0 and float(ip) >= 6:
                    parts.append(
                        f"He was particularly electric as a strikeout pitcher, posting double-digit K/9 for the tournament."
                    )

        else:
            avg = r["season_batting_avg"]
            ab  = r["season_batting_ab"] or 0
            h   = r["season_batting_hits"] or 0
            hr  = r["season_batting_hr"] or 0
            rbi = r["season_batting_rbi"] or 0
            sb  = r["season_batting_sb"] or 0
            bb  = r["season_batting_bb"] or 0
            so  = r["season_batting_so"] or 0
            ops = r["season_batting_ops"]
            obp = r["season_batting_obp"]
            slg = r["season_batting_slg"]
            d2  = r["season_batting_doubles"] or 0
            d3  = r["season_batting_triples"] or 0
            iso = r["season_batting_iso"]
            bb_rate = r["season_batting_bb_rate"]
            k_rate  = r["season_batting_k_rate"]

            if ab > 0:
                avg_str = fmt_avg(avg)
                parts.append(
                    f"At the plate, he batted {avg_str} across {ab} at-bats, "
                    f"contributing {hr} home run{'s' if hr != 1 else ''} and {rbi} RBI."
                )

            # Power profile
            if hr >= 3:
                parts.append(
                    f"He was one of the more dangerous power hitters in the field, launching {hr} home runs during the tournament."
                )
            elif iso and float(iso) >= 0.250:
                parts.append(
                    f"He showed impressive extra-base power throughout the tournament."
                )

            # On-base / discipline
            if ops and float(ops) >= 0.900:
                parts.append(
                    f"His exceptional on-base skills and power combined for an OPS above .900, placing him among the elite offensive performers in the tournament."
                )
            elif ops and float(ops) >= 0.800:
                parts.append(
                    f"He was a consistent and well-rounded offensive contributor, posting an OPS above .800."
                )

            if bb_rate and float(bb_rate) >= 0.15:
                parts.append(
                    f"He demonstrated exceptional plate discipline, drawing walks at an elite rate."
                )

            # Speed
            if sb >= 3:
                parts.append(
                    f"He was also a threat on the basepaths, swiping {sb} bags during the tournament."
                )

            # Extra-base hits
            xbh_parts = []
            if d2 >= 3: xbh_parts.append(f"{d2} doubles")
            if d3 >= 1: xbh_parts.append(f"{d3} triple{'s' if d3 != 1 else ''}")
            if xbh_parts:
                parts.append(f"He also added {' and '.join(xbh_parts)} to round out his offensive output.")

            # Strikeout concern
            if k_rate and float(k_rate) >= 0.30 and ab >= 10:
                parts.append(
                    f"Strikeouts were a factor in his game, though his power upside offset the contact concerns."
                )

        narrative = " ".join(parts)

        rows.append({
            "content": narrative,
            "metadata": meta(
                season=s,
                team=team,
                player=name,
                round_=None,
                is_mercy=None,
                category="player_profile",
            ),
        })

    log.info(f"  player_season_narratives: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 5. Player career narratives
#    Source: wbc_mart.app_player_season_stats  (multi-season aggregation)
#
#    For players who appeared in more than one WBC: a career arc summary
#    that captures their legacy across tournaments.
# ─────────────────────────────────────────────────────────────────────────────

def build_player_career_narratives(conn) -> list[dict]:
    # Aggregate career totals
    career_sql = """
        SELECT full_name, team_abbreviation, position_type,
               COUNT(DISTINCT season)      AS seasons,
               SUM(games_played)           AS career_gp,
               SUM(season_batting_ab)      AS career_ab,
               SUM(season_batting_hits)    AS career_hits,
               SUM(season_batting_hr)      AS career_hr,
               SUM(season_batting_rbi)     AS career_rbi,
               SUM(season_batting_sb)      AS career_sb,
               SUM(season_batting_doubles) AS career_2b,
               SUM(season_pitching_so)     AS career_k,
               SUM(season_pitching_w)      AS career_w,
               SUM(season_pitching_l)      AS career_l,
               SUM(season_pitching_sv)     AS career_sv,
               STRING_AGG(DISTINCT season::text, ', ' ORDER BY season::text) AS season_list
        FROM wbc_mart.app_player_season_stats
        WHERE games_played > 0
        GROUP BY full_name, team_abbreviation, position_type
        HAVING COUNT(DISTINCT season) > 1
    """
    rows = []
    for r in fetch(conn, career_sql):
        name    = r["full_name"] or "Unknown"
        team    = r["team_abbreviation"] or "?"
        seasons = r["seasons"]
        gp      = r["career_gp"] or 0
        slist   = r["season_list"] or ""
        is_p    = r["position_type"] == "Pitcher"

        parts = [
            f"{name} is one of the WBC's multi-tournament veterans, having represented {team} "
            f"across {seasons} separate tournaments ({slist}) and appearing in {gp} total games."
        ]

        if is_p:
            w  = r["career_w"] or 0
            l  = r["career_l"] or 0
            sv = r["career_sv"] or 0
            k  = r["career_k"] or 0
            parts.append(
                f"On the mound, he compiled a career WBC record of {w}-{l} with {sv} save{'s' if sv != 1 else ''} "
                f"and {k} strikeout{'s' if k != 1 else ''} across his appearances."
            )
            if k >= 20:
                parts.append(
                    f"His ability to miss bats — {k} career strikeouts in the WBC — cements his legacy as one of the more fearsome pitchers the tournament has seen."
                )
        else:
            ab  = r["career_ab"] or 0
            h   = r["career_hits"] or 0
            hr  = r["career_hr"] or 0
            rbi = r["career_rbi"] or 0
            sb  = r["career_sb"] or 0
            d2  = r["career_2b"] or 0
            avg = fmt_avg(h / ab) if ab > 0 else ".000"

            parts.append(
                f"Over his WBC career he batted {avg} with {hr} home run{'s' if hr != 1 else ''}, "
                f"{rbi} RBI, and {sb} stolen base{'s' if sb != 1 else ''} across {ab} at-bats."
            )
            if hr >= 5:
                parts.append(
                    f"His {hr} career WBC home runs rank him among the most productive power hitters in tournament history."
                )
            if d2 >= 5:
                parts.append(
                    f"He also showed a knack for the gaps, accumulating {d2} doubles across his WBC career."
                )

        rows.append({
            "content": " ".join(parts),
            "metadata": meta(
                season=None,
                team=team,
                player=name,
                round_=None,
                is_mercy=None,
                category="player_career",
            ),
        })

    log.info(f"  player_career_narratives: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 6. Player bio narratives
#    Source: wbc_mart.app_game_detail  (DISTINCT ON player_id)
#
#    The "who is this person" layer: birthplace, physical profile,
#    handedness, position, MLB debut. Deliberately separate from
#    performance so both can be retrieved independently.
# ─────────────────────────────────────────────────────────────────────────────

def build_player_bio_narratives(conn) -> list[dict]:
    sql = """
        SELECT DISTINCT ON (player_id)
            player_id, full_name, birth_date, birth_city, birth_country,
            height, weight, bat_side_code, pitch_hand_code,
            primary_number, primary_position_name, primary_position_type,
            primary_position_abbreviation, mlb_debut_date,
            away_team_abbreviation, home_team_abbreviation, team_id,
            season
        FROM wbc_mart.app_game_detail
        WHERE full_name IS NOT NULL
        ORDER BY player_id, season DESC
    """
    rows = []
    for r in fetch(conn, sql):
        name     = r["full_name"] or "Unknown"
        pos_name = r["primary_position_name"] or r["primary_position_abbreviation"] or "player"
        pos_type = r["primary_position_type"] or ""

        bat_map  = {"R": "right-handed", "L": "left-handed", "S": "switch-hitter"}
        hand_map = {"R": "right-handed", "L": "left-handed"}

        parts = [f"{name} is a professional {pos_name}."]

        # Physical profile
        if r["height"] and r["weight"]:
            parts.append(f"He stands {r['height']} and weighs {r['weight']} lbs.")
        elif r["height"]:
            parts.append(f"He stands {r['height']}.")

        # Handedness
        hand_parts = []
        if r["bat_side_code"] and pos_type != "Pitcher":
            hand_parts.append(f"bats {bat_map.get(r['bat_side_code'], r['bat_side_code'])}")
        if r["pitch_hand_code"]:
            hand_parts.append(f"throws {hand_map.get(r['pitch_hand_code'], r['pitch_hand_code'])}")
        if hand_parts:
            parts.append(f"He {' and '.join(hand_parts)}.")

        # Birthplace
        city = r["birth_city"]
        ctry = r["birth_country"]
        if city and ctry:
            parts.append(f"He was born in {city}, {ctry}.")
        elif ctry:
            parts.append(f"He was born in {ctry}.")

        # MLB debut
        if r["mlb_debut_date"]:
            debut = fmt_date(r["mlb_debut_date"])
            parts.append(
                f"He made his MLB debut on {debut} {r['mlb_debut_date'].year}."
            )

        # Jersey number
        if r["primary_number"]:
            parts.append(f"He has worn jersey number {r['primary_number']}.")

        rows.append({
            "content": " ".join(parts),
            "metadata": meta(
                season=None,
                team=None,
                player=name,
                round_=None,
                is_mercy=None,
                category="player_bio",
            ),
        })

    log.info(f"  player_bio_narratives: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 7. Standout game narratives
#    Source: wbc_mart.app_game_detail
#
#    Hero moments written as recap prose — not stat lines.
#    Thresholds: 3+ hits, 2+ HR, 4+ RBI, 10+ K, 7+ IP, scoreless 3+ IP.
#    One vector per standout performance, framing the player as the subject.
# ─────────────────────────────────────────────────────────────────────────────

def build_standout_game_narratives(conn) -> list[dict]:
    sql = """
        SELECT season, official_date, round_label, pool_group,
               full_name, primary_position_type,
               away_team_name, home_team_name,
               team_id, away_team_id,
               player_batting_hits, player_batting_hr, player_batting_rbi,
               player_batting_sb, player_batting_bb,
               player_batting_doubles, player_batting_triples,
               player_pitching_outs, player_pitching_so, player_pitching_er,
               player_pitching_wins, player_pitching_saves,
               player_pitching_total_pitches
        FROM wbc_mart.app_game_detail
        WHERE is_on_bench = FALSE
          AND (
            player_batting_hits    >= 3  OR
            player_batting_hr      >= 2  OR
            player_batting_rbi     >= 4  OR
            player_batting_sb      >= 2  OR
            player_pitching_so     >= 10 OR
            player_pitching_outs   >= 21 OR
            (player_pitching_er = 0 AND player_pitching_outs >= 9)
          )
    """
    rows = []
    for r in fetch(conn, sql):
        name    = r["full_name"] or "Unknown"
        s       = r["season"]
        date    = fmt_date(r["official_date"])
        rd      = r["pool_group"] or r["round_label"] or "game"
        rl      = r["round_label"] or ""
        away    = r["away_team_name"]
        home    = r["home_team_name"]
        matchup = f"{away} vs {home}"

        # Determine which team the player is on
        on_away = (r["team_id"] == r["away_team_id"])
        player_team = away if on_away else home
        opp_team    = home if on_away else away

        # Round context
        if is_championship(rl):
            round_ctx = f"the {s} WBC Championship game"
        elif is_semifinal(rl):
            round_ctx = f"a {s} WBC semifinal"
        elif is_quarterfinal(rl):
            round_ctx = f"a {s} WBC quarterfinal"
        else:
            round_ctx = f"a {s} WBC {rd} game"

        h   = r["player_batting_hits"] or 0
        hr  = r["player_batting_hr"] or 0
        rbi = r["player_batting_rbi"] or 0
        sb  = r["player_batting_sb"] or 0
        bb  = r["player_batting_bb"] or 0
        d2  = r["player_batting_doubles"] or 0
        d3  = r["player_batting_triples"] or 0

        outs = r["player_pitching_outs"] or 0
        k    = r["player_pitching_so"] or 0
        er   = r["player_pitching_er"] if r["player_pitching_er"] is not None else -1
        ip   = fmt_ip(outs / 3) if outs else "0.0"
        tp   = r["player_pitching_total_pitches"]

        narratives_for_row = []

        # ── Batting heroics ───────────────────────────────────────────────────
        if h >= 3 or hr >= 2 or rbi >= 4:
            bat_feats = []

            if hr >= 2:
                bat_feats.append(f"clubbing {hr} home runs")
            elif hr == 1:
                bat_feats.append("going deep once")

            if rbi >= 4:
                bat_feats.append(f"driving in {rbi} runs")
            elif rbi > 0 and hr == 0:
                bat_feats.append(f"knocking in {rbi} run{'s' if rbi != 1 else ''}")

            if h >= 3:
                hit_desc = f"collecting {h} hits"
                if d2 >= 1 or d3 >= 1:
                    xbh = []
                    if d3 >= 1: xbh.append(f"a triple")
                    if d2 >= 1: xbh.append(f"{d2} double{'s' if d2 != 1 else ''}")
                    hit_desc += f", including {' and '.join(xbh)}"
                bat_feats.append(hit_desc)

            if sb >= 2:
                bat_feats.append(f"swiping {sb} bases")

            if bat_feats:
                feat_str = ", ".join(bat_feats[:-1])
                if len(bat_feats) > 1:
                    feat_str += f", and {bat_feats[-1]}"
                else:
                    feat_str = bat_feats[0]

                narrative = (
                    f"{name} delivered a standout offensive performance for {player_team} in {round_ctx} "
                    f"against {opp_team} on {date}, {feat_str}."
                )
                narratives_for_row.append(narrative)

        elif sb >= 2:
            narrative = (
                f"{name} was a menace on the basepaths for {player_team} in {round_ctx} "
                f"against {opp_team} on {date}, stealing {sb} bases."
            )
            narratives_for_row.append(narrative)

        # ── Pitching heroics ─────────────────────────────────────────────────
        if outs > 0:
            pitch_feats = []
            dec = ""
            if r["player_pitching_wins"]:  dec = ", earning the win"
            elif r["player_pitching_saves"]: dec = ", notching the save"

            if k >= 10:
                pitch_feats.append(f"striking out {k} batters")
            if er == 0 and outs >= 9:
                pitch_feats.append(f"tossing {ip} scoreless innings")
            elif outs >= 21:
                pitch_feats.append(f"going a deep {ip} innings")

            if pitch_feats:
                feat_str = " and ".join(pitch_feats)
                tp_note  = f" on {tp} pitches" if tp else ""
                narrative = (
                    f"{name} was dominant on the mound for {player_team} in {round_ctx} "
                    f"against {opp_team} on {date}, {feat_str}{tp_note}{dec}."
                )
                narratives_for_row.append(narrative)

        for narrative in narratives_for_row:
            rows.append({
                "content": narrative,
                "metadata": meta(
                    season=s,
                    team=player_team,
                    player=name,
                    round_=rd,
                    is_mercy=None,
                    category="standout_game",
                ),
            })

    log.info(f"  standout_game_narratives: {len(rows)}")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run():
    log.info("Starting WBC RAG embedding pipeline (Hybrid Architecture v2)...")
    conn = get_connection()

    sentences = []

    # ── Game stories ──────────────────────────────────────────────────────────
    sentences.extend(build_game_recap_narratives(conn))    # category: game_recap
    sentences.extend(build_knockout_qa_pairs(conn))        # category: game_qa

    # ── Team stories ─────────────────────────────────────────────────────────
    sentences.extend(build_team_season_narratives(conn))   # category: team_profile

    # ── Player stories ────────────────────────────────────────────────────────
    sentences.extend(build_player_season_narratives(conn)) # category: player_profile
    sentences.extend(build_player_career_narratives(conn)) # category: player_career
    sentences.extend(build_player_bio_narratives(conn))    # category: player_bio

    # ── Hero moments ─────────────────────────────────────────────────────────
    sentences.extend(build_standout_game_narratives(conn)) # category: standout_game

    total = len(sentences)
    log.info(f"Total narratives to embed: {total}")

    if total == 0:
        log.warning("No narratives generated — exiting.")
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
            contents   = [b["content"]  for b in batch]
            metadatas  = [json.dumps(b["metadata"]) for b in batch]
            embeddings = model.encode(contents, normalize_embeddings=True)

            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO vectors.embeddings (content, metadata, embedding) VALUES %s",
                [(c, m, e.tolist()) for c, m, e in zip(contents, metadatas, embeddings)],
            )

            done = i + len(batch)
            if done % 500 == 0 or done == total:
                log.info(f"  {done} / {total} inserted")

        conn.commit()

    conn.close()
    log.info("Pipeline complete.")


if __name__ == "__main__":
    run()
