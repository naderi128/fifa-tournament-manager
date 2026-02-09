from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import os
import sys
import json
import datetime
import io

from . import persistence
from .models import Tournament
from .scheduler import generate_double_round_robin_schedule

app = Flask(__name__, template_folder='templates')
app.secret_key = 'fifa_league_secret_key'

def get_tournament():
    # Try to load from session first (for serverless persistence)
    state = session.get('tournament_state')
    if state:
        return persistence.load_tournament(json.loads(state))
    # Fallback to local file (works in local dev)
    return persistence.load_tournament()

def save_tournament(tournament):
    state = persistence.save_tournament(tournament)
    session['tournament_state'] = json.dumps(state)

@app.route('/')
def index():
    tournament = get_tournament()
    standings = tournament.calculate_standings()
    total_matches = len(tournament.matches)
    completed_matches = len([m for m in tournament.matches if m.completed])
    progress = (completed_matches / total_matches * 100) if total_matches > 0 else 0
    top_scorers = tournament.get_top_scorers()[:10]
    
    return render_template('standings.html', 
                           tournament=tournament, 
                           standings=standings, 
                           progress=int(progress),
                           top_scorers=top_scorers)

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    tournament = get_tournament()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_player':
            name = request.form.get('player_name')
            if name:
                tournament.add_player(name)
        elif action == 'add_team':
            team_name = request.form.get('team_name')
            owner = request.form.get('owner_name')
            if team_name and owner:
                tournament.add_team(team_name, owner)
        elif action == 'generate':
            matches = generate_double_round_robin_schedule(tournament.teams)
            tournament.matches = matches
            save_tournament(tournament)
            return redirect(url_for('matches'))
        
        save_tournament(tournament)
        return redirect(url_for('setup'))
        
    return render_template('setup.html', tournament=tournament)

@app.route('/matches', methods=['GET', 'POST'])
def matches():
    tournament = get_tournament()
    if request.method == 'POST':
        match_id = request.form.get('match_id')
        h_score = request.form.get('h_score')
        a_score = request.form.get('a_score')
        scorers = request.form.get('scorers', '')
        
        if match_id and h_score and a_score:
            scorers_list = [s.strip() for s in scorers.split(',')] if scorers else []
            tournament.update_match_score(match_id, int(h_score), int(a_score), scorers_list)
            save_tournament(tournament)
            
        return redirect(url_for('matches'))

    pending = [m for m in tournament.matches if not m.completed]
    completed = [m for m in tournament.matches if m.completed]
    return render_template('matches.html', tournament=tournament, pending=pending, completed=reversed(completed))

@app.route('/reset', methods=['POST'])
def reset():
    session.pop('tournament_state', None)
    persistence.reset_data()
    return redirect(url_for('setup'))

@app.route('/export/json')
def export_json():
    tournament = get_tournament()
    state = persistence.save_tournament(tournament)
    return jsonify(state)

@app.route('/export/txt')
def export_txt():
    tournament = get_tournament()
    standings = tournament.calculate_standings()
    
    output = io.StringIO()
    output.write(f"--- FIFA Tournament Standings ---\n")
    output.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    output.write(f"{'Team':<20} {'Owner':<15} {'GP':<4} {'W':<4} {'D':<4} {'L':<4} {'GF':<4} {'GA':<4} {'GD':<4} {'Pts':<4}\n")
    output.write("-" * 80 + "\n")
    for s in standings:
        output.write(f"{s['name']:<20} {s['owner']:<15} {s['GP']:<4} {s['W']:<4} {s['D']:<4} {s['L']:<4} {s['GF']:<4} {s['GA']:<4} {s['GD']:<4} {s['Pts']:<4}\n")
    
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    
    return send_file(mem, mimetype='text/plain', as_attachment=True, download_name='standings.txt')

@app.route('/import', methods=['POST'])
def import_state():
    file = request.files.get('file')
    if file:
        data = json.load(file)
        session['tournament_state'] = json.dumps(data)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
