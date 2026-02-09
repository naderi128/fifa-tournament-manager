from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import os
import json
import datetime
import io
import uuid
import random

# --- COMPLETE REWRITE: SINGLE-FILE CORE LOGIC ---

class Team:
    def __init__(self, name, owner_name, team_id=None):
        self.name = name
        self.owner_name = owner_name
        self.id = team_id or str(uuid.uuid4())

class Match:
    def __init__(self, home_team, away_team, h_score=None, a_score=None, match_id=None, completed=False, scorers=None):
        self.home_team = home_team
        self.away_team = away_team
        self.home_score = h_score
        self.away_score = a_score
        self.id = match_id or str(uuid.uuid4())
        self.completed = completed
        self.scorers = scorers or []

class Tournament:
    def __init__(self, name="FIFA League"):
        self.name = name
        self.players = []
        self.teams = []
        self.matches = []
        
    def add_player(self, player_name):
        if player_name and player_name not in self.players:
            self.players.append(player_name)

    def add_team(self, team_name, owner_name):
        if team_name and owner_name:
            team = Team(team_name, owner_name)
            self.teams.append(team)
            return team
        return None

    def update_match_score(self, match_id, h_score, a_score, scorers_list=None):
        for m in self.matches:
            if m.id == match_id:
                m.home_score = int(h_score)
                m.away_score = int(a_score)
                m.scorers = scorers_list or []
                m.completed = True
                return True
        return False

    def calculate_standings(self):
        standings = {t.id: {
            "name": t.name,
            "owner": t.owner_name,
            "GP": 0, "W": 0, "D": 0, "L": 0,
            "GF": 0, "GA": 0, "GD": 0, "Pts": 0
        } for t in self.teams}

        for m in self.matches:
            if not m.completed:
                continue
            
            h_id = m.home_team.id
            a_id = m.away_team.id
            h_score = m.home_score or 0
            a_score = m.away_score or 0

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

        for t_id in standings:
            standings[t_id]["GD"] = standings[t_id]["GF"] - standings[t_id]["GA"]

        return sorted(
            standings.values(),
            key=lambda x: (x["Pts"], x["GD"], x["GF"]),
            reverse=True
        )

    def get_top_scorers(self):
        counts = {}
        for m in self.matches:
            for s in m.scorers:
                counts[s] = counts.get(s, 0) + 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)

def generate_schedule(teams):
    if len(teams) < 2:
        return []

    # Valid Home/Away pairings (no same owner)
    matches = []
    for i in range(len(teams)):
        for j in range(len(teams)):
            if i != j and teams[i].owner_name != teams[j].owner_name:
                matches.append(Match(teams[i], teams[j]))

    random.shuffle(matches)
    
    # Minimize back-to-back games for the same person
    reordered = []
    if matches:
        reordered.append(matches.pop(0))
        while matches:
            last = reordered[-1]
            last_players = {last.home_team.owner_name, last.away_team.owner_name}
            
            best_idx = 0
            min_penalty = 100
            
            for idx, m in enumerate(matches[:10]):
                penalty = 0
                if m.home_team.owner_name in last_players: penalty += 1
                if m.away_team.owner_name in last_players: penalty += 1
                
                if penalty == 0:
                    best_idx = idx
                    break
                if penalty < min_penalty:
                    min_penalty = penalty
                    best_idx = idx
            
            reordered.append(matches.pop(best_idx))

    return reordered

def tournament_to_dict(t):
    return {
        "name": t.name,
        "players": t.players,
        "teams": [{"id": tm.id, "name": tm.name, "owner_name": tm.owner_name} for tm in t.teams],
        "matches": [{
            "id": m.id, "home_team_id": m.home_team.id, "away_team_id": m.away_team.id,
            "home_score": m.home_score, "away_score": m.away_score, "completed": m.completed, "scorers": m.scorers
        } for m in t.matches]
    }

def dict_to_tournament(data):
    t = Tournament(data.get("name", "FIFA League"))
    t.players = data.get("players", [])
    
    teams_map = {}
    for td in data.get("teams", []):
        team = Team(td["name"], td["owner_name"], td["id"])
        t.teams.append(team)
        teams_map[team.id] = team
            
    for md in data.get("matches", []):
        h = teams_map.get(md["home_team_id"])
        a = teams_map.get(md["away_team_id"])
        if h and a:
            match = Match(h, a, md["home_score"], md["away_score"], md["id"], md["completed"], md.get("scorers", []))
            t.matches.append(match)
    return t

# --- FLASK SETUP ---

# Use absolute path for templates to ensure Vercel can find them
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))
app.secret_key = 'fifa-tournament-secret-128'

def get_session_tournament():
    state = session.get('state')
    if state:
        try:
            return dict_to_tournament(json.loads(state))
        except:
            return Tournament()
    return Tournament()

def save_session_tournament(t):
    session['state'] = json.dumps(tournament_to_dict(t))

@app.route('/')
def index():
    t = get_session_tournament()
    standings = t.calculate_standings()
    completed = len([m for m in t.matches if m.completed])
    progress = int((completed / len(t.matches) * 100)) if t.matches else 0
    return render_template('standings.html', 
                           tournament=t, 
                           standings=standings, 
                           progress=progress, 
                           top_scorers=t.get_top_scorers()[:10])

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    t = get_session_tournament()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_player':
            t.add_player(request.form.get('player_name'))
        elif action == 'add_team':
            t.add_team(request.form.get('team_name'), request.form.get('owner_name'))
        elif action == 'generate':
            t.matches = generate_schedule(t.teams)
            save_session_tournament(t)
            return redirect(url_for('matches'))
        
        save_session_tournament(t)
        return redirect(url_for('setup'))
    return render_template('setup.html', tournament=t)

@app.route('/matches', methods=['GET', 'POST'])
def matches():
    t = get_session_tournament()
    if request.method == 'POST':
        match_id = request.form.get('match_id')
        h_s = request.form.get('h_score')
        a_s = request.form.get('a_score')
        scrs = request.form.get('scorers', '')
        
        if match_id and h_s and a_s:
            s_list = [s.strip() for s in scrs.split(',')] if scrs else []
            t.update_match_score(match_id, h_s, a_s, s_list)
            save_session_tournament(t)
        return redirect(url_for('matches'))

    pending = [m for m in t.matches if not m.completed]
    history = [m for m in t.matches if m.completed]
    return render_template('matches.html', tournament=t, pending=pending, completed=reversed(history))

@app.route('/reset', methods=['POST'])
def reset():
    session.pop('state', None)
    return redirect(url_for('setup'))

@app.route('/export/json')
def export_json():
    t = get_session_tournament()
    return jsonify(tournament_to_dict(t))

@app.route('/export/txt')
def export_txt():
    t = get_session_tournament()
    stan = t.calculate_standings()
    sio = io.StringIO()
    sio.write(f"--- FIFA League Standings ---\n\n")
    sio.write(f"{'Team':<20} {'Owner':<15} {'GP':<4} {'Pts':<4}\n")
    for s in stan:
        sio.write(f"{s['name']:<20} {s['owner']:<15} {s['GP']:<4} {s['Pts']:<4}\n")
    
    buf = io.BytesIO(sio.getvalue().encode('utf-8'))
    return send_file(buf, mimetype='text/plain', as_attachment=True, download_name='standings.txt')

@app.route('/import', methods=['POST'])
def import_state():
    f = request.files.get('file')
    if f:
        try:
            data = json.load(f)
            session['state'] = json.dumps(data)
        except:
            pass
    return redirect(url_for('index'))

# Export the app object for Vercel
app = app
