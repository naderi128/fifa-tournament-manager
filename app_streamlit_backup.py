import streamlit as st
import pandas as pd
import persistence
from models import Tournament
from scheduler import generate_double_round_robin_schedule
import datetime

# --- Page Config ---
st.set_page_config(page_title="FIFA Tournament Manager", layout="wide")

# --- Initialize Session State ---
if 'tournament' not in st.session_state:
    st.session_state.tournament = persistence.load_tournament()

def save():
    persistence.save_tournament(st.session_state.tournament)

# --- Sidebar ---
st.sidebar.title("🎮 FIFA Manager")
menu = st.sidebar.radio("Navigation", ["Setup", "Matches", "Standings", "History"])

if st.sidebar.button("🗑️ Reset Tournament"):
    if st.sidebar.checkbox("Confirm Reset"):
        persistence.reset_data()
        st.session_state.tournament = Tournament()
        st.rerun()

# --- Setup Tab ---
if menu == "Setup":
    st.header("🏟️ Tournament Setup")
    
    with st.expander("Step 1: Add Players", expanded=not st.session_state.tournament.players):
        player_name = st.text_input("Player Name")
        if st.button("Add Player"):
            if player_name:
                st.session_state.tournament.add_player(player_name)
                save()
                st.rerun()
        
        if st.session_state.tournament.players:
            st.write("**Current Players:**")
            st.write(", ".join(st.session_state.tournament.players))

    with st.expander("Step 2: Define Teams", expanded=bool(st.session_state.tournament.players) and not st.session_state.tournament.teams):
        if not st.session_state.tournament.players:
            st.warning("Please add players first.")
        else:
            for player in st.session_state.tournament.players:
                st.subheader(f"Teams for {player}")
                # We'll allow adding multiple teams for each player
                existing_teams = [t.name for t in st.session_state.tournament.teams if t.owner_name == player]
                st.write(f"Has: {', '.join(existing_teams) if existing_teams else 'No teams'}")
                
                new_team = st.text_input(f"New Team for {player}", key=f"team_in_{player}")
                if st.button(f"Add Team for {player}", key=f"btn_{player}"):
                    if new_team:
                        st.session_state.tournament.add_team(new_team, player)
                        save()
                        st.rerun()

    with st.expander("Step 3: Generate Schedule", expanded=bool(st.session_state.tournament.teams) and not st.session_state.tournament.matches):
        if not st.session_state.tournament.teams:
            st.warning("Please add teams first.")
        else:
            st.write(f"Total Teams: {len(st.session_state.tournament.teams)}")
            if st.button("🚀 Generate Double Round Robin Schedule"):
                matches = generate_double_round_robin_schedule(st.session_state.tournament.teams)
                st.session_state.tournament.matches = matches
                save()
                st.success(f"Generated {len(matches)} matches!")
                st.rerun()

# --- Matches Tab ---
elif menu == "Matches":
    st.header("⚽ Match Management")
    
    if not st.session_state.tournament.matches:
        st.info("No matches scheduled yet. Go to 'Setup' to generate the schedule.")
    else:
        pending_matches = [m for m in st.session_state.tournament.matches if not m.completed]
        
        if not pending_matches:
            st.success("All matches completed! Check the Standings.")
        else:
            # Show next up
            next_match = pending_matches[0]
            st.subheader("🔥 Next Match")
            col1, col2, col3 = st.columns([2, 1, 2])
            
            with col1:
                st.markdown(f"### {next_match.home_team.name}")
                st.caption(f"Owner: {next_match.home_team.owner_name}")
            with col2:
                st.markdown("### VS")
            with col3:
                st.markdown(f"### {next_match.away_team.name}")
                st.caption(f"Owner: {next_match.away_team.owner_name}")
            
            with st.form("score_entry"):
                c1, c2 = st.columns(2)
                h_score = c1.number_input(f"{next_match.home_team.name} Score", min_value=0, step=1)
                a_score = c2.number_input(f"{next_match.away_team.name} Score", min_value=0, step=1)
                
                scorers_str = st.text_input("Scorers (comma separated, optional)", placeholder="Messi, Messi, Ronaldo")
                
                if st.form_submit_button("Submit Result"):
                    scorers_list = [s.strip() for s in scorers_str.split(",")] if scorers_str else []
                    st.session_state.tournament.update_match_score(next_match.id, int(h_score), int(a_score), scorers_list)
                    save()
                    st.rerun()

        st.divider()
        st.subheader("Upcoming Fixtures")
        fixture_data = []
        for i, m in enumerate(pending_matches[1:11]): # Show next 10
            fixture_data.append({
                "Seq": i + 2,
                "Home": f"{m.home_team.name} ({m.home_team.owner_name})",
                "Away": f"{m.away_team.name} ({m.away_team.owner_name})"
            })
        if fixture_data:
            st.table(fixture_data)
        else:
            st.write("No more upcoming fixtures.")

# --- Standings Tab ---
elif menu == "Standings":
    st.header("🏆 League Table")
    
    standings = st.session_state.tournament.calculate_standings()
    if not standings:
        st.info("Setup teams and matches to see standings.")
    else:
        df = pd.DataFrame(standings)
        # Reorder columns for better view
        df = df[["name", "owner", "GP", "W", "D", "L", "GF", "GA", "GD", "Pts"]]
        df.columns = ["Team", "Owner", "GP", "W", "D", "L", "GF", "GA", "GD", "Pts"]
        
        st.dataframe(df.style.highlight_max(axis=0, subset=['Pts']), use_container_width=True)
        
        # Progress Bar
        total_matches = len(st.session_state.tournament.matches)
        completed_matches = len([m for m in st.session_state.tournament.matches if m.completed])
        if total_matches > 0:
            progress = completed_matches / total_matches
            st.write(f"**Tournament Progress: {int(progress*100)}%**")
            st.progress(progress)

        # Top Scorers
        st.divider()
        st.header("👟 Golden Boot (Top Scorers)")
        top_scorers = st.session_state.tournament.get_top_scorers()
        if top_scorers:
            scorer_df = pd.DataFrame(top_scorers, columns=["Player", "Goals"])
            st.table(scorer_df.head(10))
        else:
            st.caption("No goals recorded yet.")
            
        # Export Button
        if st.button("📄 Export Standings to Text"):
            table_str = df.to_string(index=False)
            filename = f"standings_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"--- FIFA Tournament: {st.session_state.tournament.name} ---\n")
                f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(table_str)
            st.success(f"Standings exported to {filename}")

# --- History Tab ---
elif menu == "History":
    st.header("📜 Match History")
    completed = [m for m in st.session_state.tournament.matches if m.completed]
    
    if not completed:
        st.info("No matches completed yet.")
    else:
        history_data = []
        for m in reversed(completed):
            history_data.append({
                "Home": f"{m.home_team.name} ({m.home_team.owner_name})",
                "Score": f"{m.home_score} - {m.away_score}",
                "Away": f"{m.away_team.name} ({m.away_team.owner_name})",
                "Scorers": ", ".join(m.scorers)
            })
        st.table(history_data)
