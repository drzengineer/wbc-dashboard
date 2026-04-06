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
            pool,
            is_one_run_game,
            is_mercy_rule,
            run_margin,
            total_runs
        `)
        .order("official_date", { ascending: false });

    if (statsError) {
        console.error('❌ Error loading game stats:', statsError);
    }

    // Calculate aggregate metrics
    const totalGames = gameStats?.length || 0;
    const oneRunGames = gameStats?.filter(g => g.is_one_run_game).length || 0;
    const mercyRuleGames = gameStats?.filter(g => g.is_mercy_rule).length || 0;

    console.log(`✅ Game stats loaded: ${totalGames} total, ${oneRunGames} 1-run, ${mercyRuleGames} mercy rule`);

    return {
        seasons: uniqueSeasons,
        games: gameStats || [],
        summary: {
            totalGames,
            oneRunGames,
            mercyRuleGames,
            oneRunPercentage: totalGames > 0 ? Math.round((oneRunGames / totalGames) * 100) : 0,
            mercyRulePercentage: totalGames > 0 ? Math.round((mercyRuleGames / totalGames) * 100) : 0
        },
        teamStats: [],
        recentGames: [],
        knockoutGames: [],
        gameResults: []
    };
};
