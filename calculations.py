import streamlit as st
import math

def recalculate_related_odds(player_name, changed_game_index):
    """
    Preračunava sve povezane kvote na osnovu promene jedne vrednosti.
    Ova funkcija je sada odvojena radi bolje organizacije koda.
    """
    player_games = st.session_state.selected_players.get(player_name, [])
    if not player_games:
        return

    # Provera da li je ključ validan pre pristupa
    key = f"odds_{player_name}_{changed_game_index}"
    if key not in st.session_state:
        return

    changed_game = player_games[changed_game_index]
    market_raw = changed_game['market'].replace("(Settled using Opta data)", "").strip()
    new_odds = st.session_state[key]

    try:
        # --- Rekalkulacija na osnovu igre "Daje gol" ---
        if market_raw == "To Score":
            p_score = 1 / new_odds
            lambda_goals = -math.log(1 - p_score)

            for i, game in enumerate(player_games):
                g_market_raw = game['market'].replace("(Settled using Opta data)", "").strip()
                
                if g_market_raw == 'To score at least 2 goals':
                    p_at_least_2 = 1 - math.exp(-lambda_goals) * (1 + lambda_goals)
                    if p_at_least_2 > 0: st.session_state[f"odds_{player_name}_{i}"] = round(1 / p_at_least_2, 2)
                
                elif g_market_raw == 'To score at least 3 goals':
                    p_at_least_3 = 1 - math.exp(-lambda_goals) * (1 + lambda_goals + (lambda_goals**2 / 2))
                    if p_at_least_3 > 0: st.session_state[f"odds_{player_name}_{i}"] = round(1 / p_at_least_3, 2)
                
                elif game['market'] == 'daje gol u 1. poluvremenu':
                    lambda_1h = lambda_goals * 0.44
                    p_1h = 1 - math.exp(-lambda_1h)
                    if p_1h > 0: st.session_state[f"odds_{player_name}_{i}"] = round(1 / p_1h, 2)

                elif game['market'] == 'daje gol u 2. poluvremenu':
                    lambda_2h = lambda_goals * 0.56
                    p_2h = 1 - math.exp(-lambda_2h)
                    if p_2h > 0: st.session_state[f"odds_{player_name}_{i}"] = round(1 / p_2h, 2)
                
                elif g_market_raw == 'To Score Or Assist':
                    p_assist = p_score * 0.65
                    p_s_or_a = p_score + p_assist - (p_score * p_assist)
                    if p_s_or_a > 0: st.session_state[f"odds_{player_name}_{i}"] = round(1 / p_s_or_a, 2)

        # --- Rekalkulacija za igre sa linijama (šutevi, faulovi) ---
        line_markets = ["Player's shots on target", "Player's shots", "Player's fouls conceded"]
        if market_raw in line_markets and changed_game.get('line') in [0.5, 1.0]:
            p_at_least_one = 1 / new_odds
            lambda_market = -math.log(1 - p_at_least_one)
            
            for i, game in enumerate(player_games):
                if game['market'].replace("(Settled using Opta data)", "").strip() == market_raw:
                    line = game.get('line')
                    if line in [1.5, 2.0]:
                        p_at_least_2 = 1 - math.exp(-lambda_market) * (1 + lambda_market)
                        if p_at_least_2 > 0: st.session_state[f"odds_{player_name}_{i}"] = round(1 / p_at_least_2, 2)
                    elif line in [2.5, 3.0]:
                        p_at_least_3 = 1 - math.exp(-lambda_market) * (1 + lambda_market + (lambda_market**2 / 2))
                        if p_at_least_3 > 0: st.session_state[f"odds_{player_name}_{i}"] = round(1 / p_at_least_3, 2)

    except (ValueError, ZeroDivisionError):
        pass
