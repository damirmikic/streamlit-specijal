import streamlit as st
import math

def apply_margin_and_get_odds(probability, line=0.5):
    """
    Izračunava finalnu kvotu primenom linearne margine zasnovane na liniji.
    Niži 'margin_factor' znači višu marginu.
    """
    margin_factor = 1.0
    
    # Definisanje margine na osnovu vrednosti linije
    if line is None or line <= 1.0: # Za binarne ishode kao što su 1+, Daje Gol, 1P/2P gol
        margin_factor = 0.95 # ~5% margina
    elif line <= 2.0: # Za 2+ linije
        margin_factor = 0.93 # ~7% margina
    elif line <= 3.0: # Za 3+ linije
        margin_factor = 0.91 # ~9% margina
    else: # Za više linije
        margin_factor = 0.89 # ~11% margina

    if probability is not None and probability > 0:
        final_probability = probability * margin_factor
        if final_probability > 0:
             return round(1 / final_probability, 2)
    return None # Vraća None ako je verovatnoća nula ili nevalidna

def recalculate_related_odds(player_name, changed_game_index):
    """
    Preračunava sve povezane kvote na osnovu promene jedne vrednosti, sada sa primenom margine.
    """
    player_games = st.session_state.selected_players.get(player_name, [])
    if not player_games:
        return

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
                    calculated_odds = apply_margin_and_get_odds(p_at_least_2, 2.0)
                    if calculated_odds is not None: st.session_state[f"odds_{player_name}_{i}"] = calculated_odds
                
                elif g_market_raw == 'To score at least 3 goals':
                    p_at_least_3 = 1 - math.exp(-lambda_goals) * (1 + lambda_goals + (lambda_goals**2 / 2))
                    calculated_odds = apply_margin_and_get_odds(p_at_least_3, 3.0)
                    if calculated_odds is not None: st.session_state[f"odds_{player_name}_{i}"] = calculated_odds
                
                elif game['market'] == 'daje gol u 1. poluvremenu':
                    lambda_1h = lambda_goals * 0.44
                    p_1h = 1 - math.exp(-lambda_1h)
                    calculated_odds = apply_margin_and_get_odds(p_1h)
                    if calculated_odds is not None: st.session_state[f"odds_{player_name}_{i}"] = calculated_odds

                elif game['market'] == 'daje gol u 2. poluvremenu':
                    lambda_2h = lambda_goals * 0.56
                    p_2h = 1 - math.exp(-lambda_2h)
                    calculated_odds = apply_margin_and_get_odds(p_2h)
                    if calculated_odds is not None: st.session_state[f"odds_{player_name}_{i}"] = calculated_odds
                
                elif g_market_raw == 'To Score Or Assist':
                    p_assist = p_score * 0.65
                    p_s_or_a = p_score + p_assist - (p_score * p_assist)
                    calculated_odds = apply_margin_and_get_odds(p_s_or_a)
                    if calculated_odds is not None: st.session_state[f"odds_{player_name}_{i}"] = calculated_odds

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
                        calculated_odds = apply_margin_and_get_odds(p_at_least_2, 2.0)
                        if calculated_odds is not None: st.session_state[f"odds_{player_name}_{i}"] = calculated_odds
                    elif line in [2.5, 3.0]:
                        p_at_least_3 = 1 - math.exp(-lambda_market) * (1 + lambda_market + (lambda_market**2 / 2))
                        calculated_odds = apply_margin_and_get_odds(p_at_least_3, 3.0)
                        if calculated_odds is not None: st.session_state[f"odds_{player_name}_{i}"] = calculated_odds

    except (ValueError, ZeroDivisionError):
        pass

