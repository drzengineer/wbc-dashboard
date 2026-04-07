import { supabase } from "$lib/server/db";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async () => {
    console.log('🔍 Loading main page data...');

    // Get all unique seasons
    const { data: seasons, error } = await supabase
        .from("dim_games")
        .select("season")
        .order("season", { ascending: false });

    const uniqueSeasons = [...new Set(seasons?.map(s => s.season))].filter(Boolean);
    console.log('✅ Unique seasons loaded:', uniqueSeasons);

    // Game summary stats directly from dim_games - all pre-calculated flags
    const { data: gameStats, error: statsError } = await supabase
        .from("dim_games")
        .select(`
            game_pk,
            season,
            pool_group,
            is_one_run_game,
            is_mercy_rule,
            run_margin,
            total_runs
        `)
        .order("official_date", { ascending: false });

    if (statsError) {
        console.error('❌ Error loading game stats:', statsError);
    }

    // Pool Standings - Pre-aggregated directly from database mart
    const { data: poolStandings, error: poolError } = await supabase
        .from("app_pool_standings")
        .select(`
            season,
            pool_group,
            team_id,
            team_name,
            team_abbreviation,
            pool_wins,
            pool_losses,
            pool_win_pct,
            pool_run_differential,
            pool_runs_scored,
            pool_runs_allowed
        `);

    if (poolError) {
        console.error('❌ Error loading pool standings:', poolError);
    }

    // Build nested map structure - already sorted correctly in database
    const finalPools = new Map<number | string, Map<string, any[]>>();

    for (const team of (poolStandings || [])) {
        if (!finalPools.has(team.season)) {
            finalPools.set(team.season, new Map<string, any[]>());
        }

        const seasonPools = finalPools.get(team.season)!;
        if (!seasonPools.has(team.pool_group)) {
            seasonPools.set(team.pool_group, []);
        }

        seasonPools.get(team.pool_group)!.push(team);
    }

    // Calculate aggregate metrics
    const totalGames = gameStats?.length || 0;
    const oneRunGames = gameStats?.filter(g => g.is_one_run_game).length || 0;
    const mercyRuleGames = gameStats?.filter(g => g.is_mercy_rule).length || 0;

    // All Game Results - direct from mart, exact schema match for GameCard
    const { data: allGames, error: gamesError } = await supabase
        .from("app_game_results")
        .select(`
            game_pk,
            season,
            official_date,
            game_type,
            round_label,
            round_order,
            series_game_number,
            away_team_name,
            away_team_abbreviation,
            away_score,
            away_is_winner,
            home_team_name,
            home_team_abbreviation,
            home_score,
            home_is_winner,
            is_mercy_rule,
            venue_name,
            away_innings,
            home_innings,
            away_r,
            away_h,
            away_e,
            home_r,
            home_h,
            home_e
        `)
        .order("official_date", { ascending: false })
        .order("game_pk", { ascending: false });

    if (gamesError) {
        console.error('❌ Error loading game results:', gamesError);
    }

    // Recent games are just the last 10
    const recentGames = allGames?.slice(0, 10) || [];

    // Build bracket structure correctly using actual game progression relationships
    const brackets = new Map<number | string, any>();

    // Group all knockout games by season first
    const seasonKnockoutGames = new Map<number | string, any[]>();
    for (const game of (allGames || [])) {
        if (!['Quarterfinals', 'Semifinals', 'Championship'].includes(game.round_label)) {
            continue;
        }
        if (!seasonKnockoutGames.has(game.season)) {
            seasonKnockoutGames.set(game.season, []);
        }
        seasonKnockoutGames.get(game.season)!.push(game);
    }

    // Build each season's bracket properly from Championship backwards
    for (const [season, games] of seasonKnockoutGames) {
        const finalGame = games.find((g: any) => g.round_label === 'Championship') || null;
        const sfGames = games.filter((g: any) => g.round_label === 'Semifinals');
        const qfGames = games.filter((g: any) => g.round_label === 'Quarterfinals');

        // Create winner lookup map: team name -> game they won
        const winnerMap = new Map<string, any>();
        for (const game of games) {
            const winningTeam = game.away_is_winner ? game.away_team_name : game.home_team_name;
            winnerMap.set(winningTeam, game);
        }

        // 1. Resolve Semifinal positions - they feed into Final
        const orderedSf: any[] = [];
        if (finalGame) {
            // Final has exactly 2 teams. These are the winners of the 2 semifinal games
            const finalTeams = [finalGame.away_team_name, finalGame.home_team_name];
            for (const team of finalTeams) {
                const semifinalGame = winnerMap.get(team);
                if (semifinalGame && semifinalGame.round_label === 'Semifinals') {
                    orderedSf.push(semifinalGame);
                }
            }
        }

        // If we couldn't resolve from final (tournament incomplete) add remaining SF games
        for (const sf of sfGames) {
            if (!orderedSf.find(g => g.game_pk === sf.game_pk)) {
                orderedSf.push(sf);
            }
        }

        // 2. Resolve Quarterfinal positions - they feed into Semifinals
        const orderedQf: any[] = [];
        for (const semifinal of orderedSf) {
            const semiTeams = [semifinal.away_team_name, semifinal.home_team_name];
            for (const team of semiTeams) {
                const qfGame = winnerMap.get(team);
                if (qfGame && qfGame.round_label === 'Quarterfinals') {
                    orderedQf.push(qfGame);
                }
            }
        }

        // Add remaining QF games that haven't been placed yet
        for (const qf of qfGames) {
            if (!orderedQf.find(g => g.game_pk === qf.game_pk)) {
                orderedQf.push(qf);
            }
        }

        // Store bracket in correct positional order for frontend
        brackets.set(season, {
            qf: orderedQf,
            sf: orderedSf,
            final: finalGame
        });
    }

    // Calculate SEASON-WIDE team totals (all games: pool + knockout)
    const seasonTeamTotals = new Map<number | string, Map<string, any>>();
    
    for (const game of (allGames || [])) {
        // Initialize season map if needed
        if (!seasonTeamTotals.has(game.season)) {
            seasonTeamTotals.set(game.season, new Map<string, any>());
        }
        
        const seasonTeams = seasonTeamTotals.get(game.season)!;
        
        // Update AWAY team stats
        if (!seasonTeams.has(game.away_team_name)) {
            seasonTeams.set(game.away_team_name, {
                team_name: game.away_team_name,
                team_abbreviation: game.away_team_abbreviation,
                total_runs_scored: 0,
                total_runs_allowed: 0,
                total_run_differential: 0
            });
        }
        const awayTeam = seasonTeams.get(game.away_team_name)!;
        awayTeam.total_runs_scored += game.away_score;
        awayTeam.total_runs_allowed += game.home_score;
        awayTeam.total_run_differential += (game.away_score - game.home_score);
        
        // Update HOME team stats
        if (!seasonTeams.has(game.home_team_name)) {
            seasonTeams.set(game.home_team_name, {
                team_name: game.home_team_name,
                team_abbreviation: game.home_team_abbreviation,
                total_runs_scored: 0,
                total_runs_allowed: 0,
                total_run_differential: 0
            });
        }
        const homeTeam = seasonTeams.get(game.home_team_name)!;
        homeTeam.total_runs_scored += game.home_score;
        homeTeam.total_runs_allowed += game.away_score;
        homeTeam.total_run_differential += (game.home_score - game.away_score);
    }

    console.log(`✅ Loaded: ${uniqueSeasons.length} seasons | ${totalGames} total games | ${brackets.size} brackets | ${recentGames.length} recent games`);

    return {
        seasons: uniqueSeasons,
        games: gameStats || [],
        pools: finalPools,
        brackets: brackets,
        recentGames: recentGames || [],
        allGames: allGames || [],
        seasonTeamTotals: seasonTeamTotals
    };
};
