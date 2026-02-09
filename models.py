import dataclasses
from typing import List, Dict, Optional
import uuid

@dataclasses.dataclass
class Team:
    name: str
    owner_name: str
    id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))

@dataclasses.dataclass
class Match:
    home_team: Team
    away_team: Team
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))
    completed: bool = False
    scorers: List[str] = dataclasses.field(default_factory=list)

class Tournament:
    def __init__(self, name: str = "FIFA League"):
        self.name = name
        self.players: List[str] = []
        self.teams: List[Team] = []
        self.matches: List[Match] = []
        
    def add_player(self, player_name: str):
        if player_name not in self.players:
            self.players.append(player_name)

    def add_team(self, team_name: str, owner_name: str):
        team = Team(name=team_name, owner_name=owner_name)
        self.teams.append(team)
        return team

    def get_team_by_id(self, team_id: str) -> Optional[Team]:
        for team in self.teams:
            if team.id == team_id:
                return team
        return None

    def update_match_score(self, match_id: str, home_score: int, away_score: int, scorers: List[str] = None):
        for match in self.matches:
            if match.id == match_id:
                match.home_score = home_score
                match.away_score = away_score
                match.scorers = scorers or []
                match.completed = True
                return True
        return False

    def reset_matches(self):
        self.matches = []

    def calculate_standings(self):
        # Stats: GP, W, D, L, GF, GA, GD, Pts
        standings = {team.id: {
            "name": team.name,
            "owner": team.owner_name,
            "GP": 0, "W": 0, "D": 0, "L": 0,
            "GF": 0, "GA": 0, "GD": 0, "Pts": 0
        } for team in self.teams}

        for match in self.matches:
            if not match.completed:
                continue
            
            h_id = match.home_team.id
            a_id = match.away_team.id
            h_score = match.home_score
            a_score = match.away_score

            standings[h_id]["GP"] += 1
            standings[a_id]["GP"] += 1
            standings[h_id]["GF"] += h_score
            standings[h_id]["GA"] += a_score
            standings[a_id]["GF"] += a_score
            standings[a_id]["GA"] += h_score

            if h_score > a_score:
                standings[h_id]["W"] += 1
                standings[h_id]["Pts"] += 3
                standings[a_id]["L"] += 1
            elif a_score > h_score:
                standings[a_id]["W"] += 1
                standings[a_id]["Pts"] += 3
                standings[h_id]["L"] += 1
            else:
                standings[h_id]["D"] += 1
                standings[h_id]["Pts"] += 1
                standings[a_id]["D"] += 1
                standings[a_id]["Pts"] += 1

        for team_id in standings:
            standings[team_id]["GD"] = standings[team_id]["GF"] - standings[team_id]["GA"]

        # Sort: Points (desc), GD (desc), GF (desc)
        sorted_standings = sorted(
            standings.values(),
            key=lambda x: (x["Pts"], x["GD"], x["GF"]),
            reverse=True
        )
        return sorted_standings

    def get_top_scorers(self):
        scorer_counts = {}
        for match in self.matches:
            for scorer in match.scorers:
                scorer_counts[scorer] = scorer_counts.get(scorer, 0) + 1
        
        sorted_scorers = sorted(scorer_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_scorers
