import random
from typing import List
from models import Team, Match

def generate_double_round_robin_schedule(teams: List[Team]) -> List[Match]:
    """
    Generates a Double Round Robin schedule.
    Constraint: Teams owned by the same player cannot play each other.
    """
    if len(teams) < 2:
        return []

    # Filter out teams owned by the same player
    def can_play(team1: Team, team2: Team):
        return team1.owner_name != team2.owner_name

    matches = []
    
    # Generate all valid unique pairings for Home and Away
    # First half (Home)
    for i in range(len(teams)):
        for j in range(len(teams)):
            if i != j and can_play(teams[i], teams[j]):
                matches.append(Match(home_team=teams[i], away_team=teams[j]))

    # To balance the distribution so players don't wait too long:
    # We'll shuffle the matches but try to alternate players as much as possible.
    # Simple approach: shuffle then sort by a heuristic or just shuffle.
    # A more complex round-robin scheduling algorithm (like Circle Method) 
    # is harder with the "same owner" constraint, so we'll shuffle and then 
    # apply a basic "gap" logic if needed.
    
    random.shuffle(matches)
    
    # Let's try to re-order to minimize back-to-back games for the same player
    reordered = []
    if matches:
        reordered.append(matches.pop(0))
        
        while matches:
            last_match = reordered[-1]
            last_players = {last_match.home_team.owner_name, last_match.away_team.owner_name}
            
            best_idx = 0
            best_penalty = 100
            
            # Look ahead for a match that doesn't involve the last players
            for idx, m in enumerate(matches[:10]): # Look ahead bit
                penalty = 0
                if m.home_team.owner_name in last_players: penalty += 1
                if m.away_team.owner_name in last_players: penalty += 1
                
                if penalty == 0:
                    best_idx = idx
                    break
                if penalty < best_penalty:
                    best_penalty = penalty
                    best_idx = idx
            
            reordered.append(matches.pop(best_idx))

    return reordered
