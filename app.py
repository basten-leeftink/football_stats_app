from flask import Flask, render_template, request, redirect, url_for
import csv
from pathlib import Path

app = Flask(__name__)

DATA_DIR = Path('data')
MATCHES_FILE = DATA_DIR / 'matches.csv'
TRAININGS_FILE = DATA_DIR / 'trainings.csv'
PLAYERS_FILE = DATA_DIR / 'players.csv'
MATCH_PLAYERS_FILE = DATA_DIR / 'match_players.csv'
TRAINING_ATTENDANCE_FILE = DATA_DIR / 'training_attendance.csv'

DATA_DIR.mkdir(exist_ok=True)

# Ensure CSV files exist with headers
if not MATCHES_FILE.exists():
    with MATCHES_FILE.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id','date','opponent','competition','location'])

if not TRAININGS_FILE.exists():
    with TRAININGS_FILE.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id','date','location'])

if not PLAYERS_FILE.exists():
    with PLAYERS_FILE.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id','name'])


def read_csv(path):
    with path.open() as f:
        reader = csv.DictReader(f)
        return list(reader)


def append_csv(path, row_dict):
    exists = path.exists()
    with path.open('a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=row_dict.keys())
        if not exists:
            writer.writeheader()
        writer.writerow(row_dict)

def compute_training_attendance():
    trainings = read_csv(TRAININGS_FILE)
    training_att = read_csv(TRAINING_ATTENDANCE_FILE)

    summary = []

    for t in trainings:
        tid = t['id']
        # Count rows in training_attendance for this training with attended == '1'
        count_present = sum(
            1
            for row in training_att
            if row.get('training_id') == tid and row.get('attended') == '1'
        )

        summary.append({
            'training_id': tid,
            'date': t['date'],
            'attendance_count': count_present,
        })

    return summary

def compute_player_stats():
    players = read_csv(PLAYERS_FILE)
    match_players = read_csv(MATCH_PLAYERS_FILE)
    trainings = read_csv(TRAININGS_FILE)
    training_att = read_csv(TRAINING_ATTENDANCE_FILE)
    

    total_trainings = len(trainings)

    stats = []

    # Build a dict keyed by player_id
    for p in players:
        pid = p['id']
        # Filter rows for this player
        mp_rows = [row for row in match_players if row['player_id'] == pid]
        tr_rows = [row for row in training_att if row['player_id'] == pid]

        matches_played = sum(1 for r in mp_rows if r.get('attended') == '1')
        goals = sum(int(r.get('goals', 0) or 0) for r in mp_rows)
        assists = sum(int(r.get('assists', 0) or 0) for r in mp_rows)
        yellow = sum(int(r.get('yellow', 0) or 0) for r in mp_rows)
        red = sum(int(r.get('red', 0) or 0) for r in mp_rows)

        trainings_attended = sum(1 for r in tr_rows if r.get('attended') == '1')

        training_per_match = (
            trainings_attended / matches_played
            if matches_played > 0 else 0
        )

        stats.append({
            'player_id': pid,
            'name': p['name'],
            'matches_played': matches_played,
            'goals': goals,
            'assists': assists,
            'yellow_cards': yellow,
            'red_cards': red,
            'trainings_attended': trainings_attended,
            'total_trainings': total_trainings,
            'training_per_match': round(training_per_match, 2),
        })

    return stats

def write_match_players(rows):
    """Overwrite match_players.csv with the given list of dict rows."""
    fieldnames = ['id', 'match_id', 'player_id', 'attended',
                  'goals', 'assists', 'yellow', 'red', 'goalkeeper', 'referee']
    with MATCH_PLAYERS_FILE.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        # Reassign ids sequentially to keep them clean
        for idx, row in enumerate(rows, start=1):
            row['id'] = idx
            writer.writerow(row)

def write_training_attendance(rows):
    fieldnames = ['id', 'training_id', 'player_id', 'attended']
    with TRAINING_ATTENDANCE_FILE.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for idx, row in enumerate(rows, start=1):
            row['id'] = idx
            writer.writerow(row)


@app.route('/')
def index():
    matches = read_csv(MATCHES_FILE)
    trainings = read_csv(TRAININGS_FILE)
    players = read_csv(PLAYERS_FILE)
    player_stats = compute_player_stats()
    training_summary = compute_training_attendance()  

    return render_template(
        'index.html',
        matches=matches,
        trainings=trainings,
        players=players,
        player_stats=player_stats,
        training_summary=training_summary  
    )


@app.route('/players', methods=['GET','POST'])
def players():
    if request.method == 'POST':
        players = read_csv(PLAYERS_FILE)
        new_id = len(players) + 1
        name = request.form['name']
        append_csv(PLAYERS_FILE, {'id': new_id, 'name': name})
        return redirect(url_for('players'))
    players = read_csv(PLAYERS_FILE)
    return render_template('players.html', players=players)


@app.route('/matches', methods=['GET', 'POST'])
def matches():
    if request.method == 'POST':
        matches = read_csv(MATCHES_FILE)
        new_id = len(matches) + 1
        date = request.form['date']
        opponent = request.form['opponent']
        goals = request.form.get('goals', '-')
        goals_against = request.form.get('goals_against', '-')
        competition = request.form.get('competition', '')
        location = request.form.get('location', '')
        append_csv(MATCHES_FILE, {
            'id': new_id,
            'date': date,
            'opponent': opponent,
            'goals': goals,
            'goals_against': goals_against,
            'competition': competition,
            'location': location
        })
        return redirect(url_for('match_lineup', match_id=new_id))

    matches = read_csv(MATCHES_FILE)
    players = read_csv(PLAYERS_FILE)
    return render_template('matches.html', matches=matches, players=players)


@app.route('/trainings', methods=['GET', 'POST'])
def trainings():
    if request.method == 'POST':
        trainings = read_csv(TRAININGS_FILE)
        new_id = len(trainings) + 1
        date = request.form['date']
        append_csv(TRAININGS_FILE, {
            'id': new_id,
            'date': date,
        })

        return redirect(url_for('training_attendance', training_id=new_id))

    trainings = read_csv(TRAININGS_FILE)
    players = read_csv(PLAYERS_FILE)
    training_summary = compute_training_attendance()
    return render_template('trainings.html', trainings=trainings, players=players, training_summary=training_summary)

@app.route('/matches/<int:match_id>/lineup', methods=['GET', 'POST'])
def match_lineup(match_id):
    players = read_csv(PLAYERS_FILE)
    all_stats = read_csv(MATCH_PLAYERS_FILE)

    if request.method == 'POST':
        all_stats = read_csv(MATCH_PLAYERS_FILE)

        # keep rows for other matches
        other_rows = [r for r in all_stats if r.get('match_id') != str(match_id)]

        new_rows_for_match = []
        for p in players:
            pid = p['id']
            attended = request.form.get(f'attended_{pid}') == 'on'
            goals = request.form.get(f'goals_{pid}', '0')
            assists = request.form.get(f'assists_{pid}', '0')
            yellow = request.form.get(f'yellow_{pid}', '0')
            red = request.form.get(f'red_{pid}', '0')
            goalkeeper = request.form.get(f'goalkeeper_{pid}') == 'on'
            referee = request.form.get(f'referee_{pid}') == 'on'

            if (
                attended or goals != '0' or assists != '0'
                or yellow != '0' or red != '0'
                or goalkeeper or referee
            ):
                new_rows_for_match.append({
                    'match_id': str(match_id),
                    'player_id': pid,
                    'attended': '1' if attended else '0',
                    'goals': goals,
                    'assists': assists,
                    'yellow': yellow,
                    'red': red,
                    'goalkeeper': '1' if goalkeeper else '0',
                    'referee': '1' if referee else '0',
                })

        final_rows = other_rows + new_rows_for_match
        write_match_players(final_rows)
        return redirect(url_for('matches'))


    # GET branch (prefill stats) stays as before
    stats_for_match = [row for row in all_stats if row.get('match_id') == str(match_id)]
    stats_by_player = {row['player_id']: row for row in stats_for_match if 'player_id' in row}
    return render_template(
        'match_lineup.html',
        match_id=match_id,
        players=players,
        stats_by_player=stats_by_player
    )
@app.route('/players/<int:player_id>')
def player_detail(player_id):
    # Read all data
    players = read_csv(PLAYERS_FILE)
    matches = read_csv(MATCHES_FILE)
    match_players = read_csv(MATCH_PLAYERS_FILE)
    trainings = read_csv(TRAININGS_FILE)
    training_att = read_csv(TRAINING_ATTENDANCE_FILE)

    pid = str(player_id)

    # Find this player record
    player = next((p for p in players if p['id'] == pid), None)
    if player is None:
        return f'Player {player_id} not found', 404

    # Filter match stats for this player
    mp_rows = [row for row in match_players if row.get('player_id') == pid]

    # Aggregate general stats
    matches_played = sum(1 for r in mp_rows if r.get('attended') == '1')
    goals = sum(int(r.get('goals', 0) or 0) for r in mp_rows)
    assists = sum(int(r.get('assists', 0) or 0) for r in mp_rows)
    yellow = sum(int(r.get('yellow', 0) or 0) for r in mp_rows)
    red = sum(int(r.get('red', 0) or 0) for r in mp_rows)

    # Build lookup: match_id -> list of GKs / refs in that match
    keepers_by_match = {}
    refs_by_match = {}
    for row in match_players:
        mid = row.get('match_id')
        if not mid:
            continue
        if row.get('goalkeeper') == '1':
            keepers_by_match.setdefault(mid, []).append(row['player_id'])
        if row.get('referee') == '1':
            refs_by_match.setdefault(mid, []).append(row['player_id'])

    # Fractional keeper / referee games
    keeper_games = 0.0
    referee_games = 0.0
    for row in mp_rows:
        mid = row.get('match_id')
        if not mid:
            continue

        if row.get('goalkeeper') == '1':
            keepers = keepers_by_match.get(mid, [])
            n = len(keepers)
            if n > 0:
                keeper_games += 1.0 / n

        if row.get('referee') == '1':
            refs = refs_by_match.get(mid, [])
            n = len(refs)
            if n > 0:
                referee_games += 1.0 / n

    # Build per-match table: join stats row with match metadata
    matches_by_id = {m['id']: m for m in matches}
    per_match_stats = []
    for r in mp_rows:
        mid = r['match_id']
        m = matches_by_id.get(mid)
        if not m:
            continue

        per_match_stats.append({
            'match_id': mid,
            'date': m['date'],
            'opponent': m['opponent'],
            'competition': m.get('competition', ''),
            'location': m.get('location', ''),
            'attended': r.get('attended'),
            'goals': r.get('goals', '0'),
            'assists': r.get('assists', '0'),
            'yellow': r.get('yellow', '0'),
            'red': r.get('red', '0'),
            'goalkeeper': r.get('goalkeeper', '0'),
            'referee': r.get('referee', '0'),
        })

    # Filter training attendance for this player
    tr_rows = [row for row in training_att if row.get('player_id') == pid]
    trainings_by_id = {t['id']: t for t in trainings}
    per_training = []
    for r in tr_rows:
        tid = r['training_id']
        t = trainings_by_id.get(tid)
        if not t:
            continue
        per_training.append({
            'training_id': tid,
            'date': t['date'],
            'location': t.get('location', ''),
            'attended': r.get('attended'),
        })

    trainings_attended = sum(1 for r in tr_rows if r.get('attended') == '1')
    total_trainings = len(trainings)
    trainings_per_match = (
        trainings_attended / matches_played if matches_played > 0 else 0
    )

    # --- Chart data for progress graph ---

    # Sort matches by date for time series
    per_match_stats_sorted = sorted(per_match_stats, key=lambda m: m['date'])
    chart_labels = [m['date'] for m in per_match_stats_sorted]

    # Simple progress series: cumulative matches, goals per match
    matches_series = list(range(1, len(per_match_stats_sorted) + 1))
    goals_series = [int(m['goals'] or 0) for m in per_match_stats_sorted]

    # Trainings progress: cumulative attended by training date
    per_training_sorted = sorted(per_training, key=lambda t: t['date'])
    training_labels = [t['date'] for t in per_training_sorted]
    training_series = []
    count = 0
    for t in per_training_sorted:
        if t['attended'] == '1':
            count += 1
        training_series.append(count)

    return render_template(
        'player_detail.html',
        player=player,
        matches_played=matches_played,
        goals=goals,
        assists=assists,
        yellow=yellow,
        red=red,
        keeper_games=keeper_games,
        referee_games=referee_games,
        trainings_attended=trainings_attended,
        total_trainings=total_trainings,
        trainings_per_match=trainings_per_match,
        per_match_stats=per_match_stats_sorted,
        per_training=per_training_sorted,
        chart_labels=chart_labels,
        matches_series=matches_series,
        goals_series=goals_series,
        training_labels=training_labels,
        training_series=training_series,
    )

@app.route('/trainings/<int:training_id>/attendance', methods=['GET', 'POST'])
def training_attendance(training_id):
    players = read_csv(PLAYERS_FILE)
    all_att = read_csv(TRAINING_ATTENDANCE_FILE)

    if request.method == 'POST':
        # 1. Keep rows for other trainings
        other_rows = [
            r for r in all_att
            if r.get('training_id') != str(training_id)
        ]

        # 2. Build new rows for this training based on form input
        new_rows_for_training = []
        for p in players:
            pid = p['id']
            attended = request.form.get(f'attended_{pid}') == 'on'
            if attended:
                new_rows_for_training.append({
                    'training_id': str(training_id),
                    'player_id': pid,
                    'attended': '1',
                })

        # 3. Combine and write back
        final_rows = other_rows + new_rows_for_training
        write_training_attendance(final_rows)

        return redirect(url_for('trainings'))

    # GET: prefill attendance
    att_for_training = [
        row for row in all_att
        if row.get('training_id') == str(training_id)
    ]
    present_ids = {row['player_id'] for row in att_for_training}

    return render_template(
        'training_attendance.html',
        training_id=training_id,
        players=players,
        present_ids=present_ids
    )

if __name__ == '__main__':
    app.run(debug=True, port=8000)
