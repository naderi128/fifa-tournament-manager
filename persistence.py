import json
import os
from models import Tournament, Team, Match

DATA_FILE = "tournament_data.json"

def save_tournament(tournament: Tournament):
    data = {
        "name": tournament.name,
        "players": tournament.players,
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "owner_name": t.owner_name
            } for t in tournament.teams
        ],
        "matches": [
            {
                "id": m.id,
                "home_team_id": m.home_team.id,
                "away_team_id": m.away_team.id,
                "home_score": m.home_score,
                "away_score": m.away_score,
                "completed": m.completed,
                "scorers": m.scorers
            } for m in tournament.matches
        ]
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except OSError:
        # Happens on read-only filesystems like Vercel
        pass
    return data

def load_tournament(data_dict: dict = None) -> Tournament:
    if data_dict:
        data = data_dict
    elif not os.path.exists(DATA_FILE):
        return Tournament()
    else:
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            return Tournament()
    
    tournament = Tournament(name=data.get("name", "FIFA League"))
    tournament.players = data.get("players", [])
    
    # Restore teams
    teams_map = {}
    for t_data in data.get("teams", []):
        team = Team(
            id=t_data["id"],
            name=t_data["name"],
            owner_name=t_data["owner_name"]
        )
        tournament.teams.append(team)
        teams_map[team.id] = team
        
    # Restore matches
    for m_data in data.get("matches", []):
        home_team = teams_map.get(m_data["home_team_id"])
        away_team = teams_map.get(m_data["away_team_id"])
        
        if home_team and away_team:
            match = Match(
                id=m_data["id"],
                home_team=home_team,
                away_team=away_team,
                home_score=m_data["home_score"],
                away_score=m_data["away_score"],
                completed=m_data["completed"],
                scorers=m_data.get("scorers", [])
            )
            tournament.matches.append(match)
    
    return tournament

def reset_data():
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
