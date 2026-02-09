from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import os
import json
import datetime
import io
import uuid
import random
import dataclasses
from typing import List, Dict, Optional

# --- CORE LOGIC (Consolidated for Vercel) ---

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

    def update_match_score(self, match_id: str, home_score: int, away_score: int, scorers: List[str] = None):
        for match in self.matches:
            if match.id == match_id:
                match.home_score = home_score
                match.away_score = away_score
                match.scorers = scorers or []
                match.completed = True
                return True
        return False

    def calculate_standings(self):
        standings = {team.id: {
            "name": team.name,
            "owner": team.owner_name,
            "GP": 0, "W": 0, "D": 0, "L": 0,
            "GF": 0, "GA": 0, "GD": 0, "Pts": 0
        } for team in self.teams}

        for match in self.matches:
            if not match.completed: continue
            h_id, a_id = match.home_team.id, match.away_team.id
            h_score, a_score = (match.home_score or 0), (match.away_score or 0)
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

        for t_id in standings: standings[t_id]["GD"] = standings[t_id]["GF"] - standings[t_id]["GA"]
        return sorted(standings.values(), key=lambda x: (x["Pts"], x["GD"], x["GF"]), reverse=True)

    def get_top_scorers(self):
        counts = {}
        for m in self.matches:
            for s in m.scorers: counts[s] = counts.get(s, 0) + 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)

def generate_schedule(teams: List[Team]) -> List[Match]:
    if len(teams) < 2: return []
    matches = [Match(teams[i], teams[j]) for i in range(len(teams)) for j in range(len(teams)) 
               if i != j and teams[i].owner_name != teams[j].owner_name]
    random.shuffle(matches)
    reordered = []
    if matches:
        reordered.append(matches.pop(0))
        while matches:
            lastp = {reordered[-1].home_team.owner_name, reordered[-1].away_team.owner_name}
            best_idx, min_p = 0, 100
            for idx, m in enumerate(matches[:10]):
                p = (1 if m.home_team.owner_name in lastp else 0) + (1 if m.away_team.owner_name in lastp else 0)
                if p == 0:
                    best_idx = idx; break
                if p < min_p: min_p, best_idx = p, idx
            reordered.append(matches.pop(best_idx))
    return reordered

def serialize_tournament(t: Tournament):
    return {
        "name": t.name, "players": t.players,
        "teams": [{"id": tm.id, "name": tm.name, "owner_name": tm.owner_name} for tm in t.teams],
        "matches": [{
            "id": m.id, "home_team_id": m.home_team.id, "away_team_id": m.away_team.id,
            "home_score": m.home_score, "away_score": m.away_score, "completed": m.completed, "scorers": m.scorers
        } for m in t.matches]
    }

def deserialize_tournament(data: dict):
    t = Tournament(data.get("name", "FIFA League"))
    t.players = data.get("players", [])
    teams_map = {td["id"]: Team(td["name"], td["owner_name"], td["id"]) for td in data.get("teams", [])}
    t.teams = list(teams_map.values())
    for md in data.get("matches", []):
        h, a = teams_map.get(md["home_team_id"]), teams_map.get(md["away_team_id"])
        if h and a:
            t.matches.append(Match(h, a, md["home_score"], md["away_score"], md["id"], md["completed"], md.get("scorers", [])))
    return t

# --- FLASK APP ---

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
app.secret_key = 'fifa_league_secret_key'

def get_tournament():
    state = session.get('tournament_state')
    return deserialize_tournament(json.loads(state)) if state else Tournament()

def save_tournament(t):
    session['tournament_state'] = json.dumps(serialize_tournament(t))

@app.route('/')
def index():
    t = get_tournament()
    standings = t.calculate_standings()
    comp = len([m for m in t.matches if m.completed])
    prog = int((comp / len(t.matches) * 100)) if t.matches else 0
    return render_template('standings.html', tournament=t, standings=standings, progress=prog, top_scorers=t.get_top_scorers()[:10])

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    t = get_tournament()
    if request.method == 'POST':
        act = request.form.get('action')
        if act == 'add_player':
            name = request.form.get('player_name')
            if name: t.add_player(name)
        elif act == 'add_team':
            tn, own = request.form.get('team_name'), request.form.get('owner_name')
            if tn and own: t.add_team(tn, own)
        elif act == 'generate':
            t.matches = generate_schedule(t.teams)
            save_tournament(t)
            return redirect(url_for('matches'))
        save_tournament(t); return redirect(url_for('setup'))
    return render_template('setup.html', tournament=t)

@app.route('/matches', methods=['GET', 'POST'])
def matches():
    t = get_tournament()
    if request.method == 'POST':
        mid, hs, ascor, scrs = request.form.get('match_id'), request.form.get('h_score'), request.form.get('a_score'), request.form.get('scorers', '')
        if mid and hs and ascor:
            slis = [s.strip() for s in scrs.split(',')] if scrs else []
            t.update_match_score(mid, int(hs), int(ascor), slis)
            save_tournament(t)
        return redirect(url_for('matches'))
    pend, comp = [m for m in t.matches if not m.completed], [m for m in t.matches if m.completed]
    return render_template('matches.html', tournament=t, pending=pend, completed=reversed(comp))

@app.route('/reset', methods=['POST'])
def reset():
    session.pop('tournament_state', None); return redirect(url_for('setup'))

@app.route('/export/json')
def export_json():
    return jsonify(serialize_tournament(get_tournament()))

@app.route('/export/txt')
def export_txt():
    t = get_tournament()
    s_list = t.calculate_standings()
    out = io.StringIO()
    out.write(f"--- FIFA Tournament Standings ---\n\n")
    out.write(f"{'Team':<20} {'Owner':<15} {'GP':<4} {'W':<4} {'D':<4} {'L':<4} {'Pts':<4}\n")
    for s in s_list:
        out.write(f"{s['name']:<20} {s['owner']:<15} {s['GP']:<4} {s['W']:<4} {s['D']:<4} {s['L']:<4} {s['Pts']:<4}\n")
    mem = io.BytesIO(out.getvalue().encode('utf-8'))
    return send_file(mem, mimetype='text/plain', as_attachment=True, download_name='standings.txt')

@app.route('/import', methods=['POST'])
def import_state():
    f = request.files.get('file')
    if f: session['tournament_state'] = json.dumps(json.load(f))
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
