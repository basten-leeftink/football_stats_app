import os
from flask import Flask, render_template, request, redirect, url_for, g
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.orm import Session

# -------------------------------------------------------------------
# Database setup (Supabase Postgres via DATABASE_BTV)
# -------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_BTV")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://",
                                        "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    date = Column(String, nullable=False)        # store as YYYY-MM-DD string
    opponent = Column(String, nullable=False)
    goals = Column(Integer, nullable=True)
    goals_against = Column(Integer, nullable=True)
    competition = Column(String, nullable=True)
    location = Column(String, nullable=True)


class Training(Base):
    __tablename__ = "trainings"

    id = Column(Integer, primary_key=True)
    date = Column(String, nullable=False)        # store as YYYY-MM-DD string
    location = Column(String, nullable=True)


class MatchPlayerStat(Base):
    __tablename__ = "match_player_stats"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    attended = Column(Boolean, default=False)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    yellow = Column(Integer, default=0)
    red = Column(Integer, default=0)
    goalkeeper = Column(Boolean, default=False)
    referee = Column(Boolean, default=False)


class TrainingAttendance(Base):
    __tablename__ = "training_attendance"

    id = Column(Integer, primary_key=True)
    training_id = Column(Integer, ForeignKey("trainings.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    attended = Column(Boolean, default=True)


# Create tables if they don't exist yet
Base.metadata.create_all(bind=engine)

# -------------------------------------------------------------------
# Flask app setup
# -------------------------------------------------------------------

app = Flask(__name__)


@app.before_request
def create_session():
    g.db: Session = SessionLocal()


@app.teardown_request
def shutdown_session(exc=None):
    db: Session = getattr(g, "db", None)
    if db is not None:
        if exc:
            db.rollback()
        else:
            db.commit()
        db.close()


# -------------------------------------------------------------------
# Helper functions (DB versions of your CSV helpers)
# -------------------------------------------------------------------

def compute_training_attendance(db: Session):
    trainings = db.query(Training).all()
    atts = db.query(TrainingAttendance).all()

    att_by_training = {}
    for row in atts:
        if not row.attended:
            continue
        att_by_training[row.training_id] = att_by_training.get(row.training_id, 0) + 1

    summary = []
    for t in trainings:
        summary.append({
            "training_id": t.id,
            "date": t.date,
            "attendance_count": att_by_training.get(t.id, 0),
        })
    return summary


def compute_player_stats(db: Session):
    players = db.query(Player).all()
    match_players = db.query(MatchPlayerStat).all()
    trainings = db.query(Training).all()
    training_att = db.query(TrainingAttendance).all()

    total_trainings = len(trainings)

    # index by player_id for faster aggregation
    mp_by_player = {}
    for row in match_players:
        mp_by_player.setdefault(row.player_id, []).append(row)

    tr_by_player = {}
    for row in training_att:
        tr_by_player.setdefault(row.player_id, []).append(row)

    stats = []
    for p in players:
        mp_rows = mp_by_player.get(p.id, [])
        tr_rows = tr_by_player.get(p.id, [])

        matches_played = sum(1 for r in mp_rows if r.attended)
        goals = sum(r.goals or 0 for r in mp_rows)
        assists = sum(r.assists or 0 for r in mp_rows)
        yellow = sum(r.yellow or 0 for r in mp_rows)
        red = sum(r.red or 0 for r in mp_rows)

        trainings_attended = sum(1 for r in tr_rows if r.attended)

        training_per_match = (
            trainings_attended / matches_played if matches_played > 0 else 0
        )

        stats.append({
            "player_id": p.id,
            "name": p.name,
            "matches_played": matches_played,
            "goals": goals,
            "assists": assists,
            "yellow_cards": yellow,
            "red_cards": red,
            "trainings_attended": trainings_attended,
            "total_trainings": total_trainings,
            "training_per_match": round(training_per_match, 2),
        })

    return stats


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@app.route("/")
def index():
    db = g.db
    matches = db.query(Match).order_by(Match.date.desc()).all()
    trainings = db.query(Training).order_by(Training.date.desc()).all()
    players = db.query(Player).order_by(Player.name).all()
    player_stats = compute_player_stats(db)
    training_summary = compute_training_attendance(db)
    return render_template(
        "index.html",
        matches=matches,
        trainings=trainings,
        players=players,
        player_stats=player_stats,
        training_summary=training_summary,
    )


@app.route("/players", methods=["GET", "POST"])
def players():
    db = g.db
    if request.method == "POST":
        name = request.form["name"]
        p = Player(name=name)
        db.add(p)
        db.flush()
        return redirect(url_for("players"))

    players = db.query(Player).order_by(Player.name).all()
    return render_template("players.html", players=players)


@app.route("/matches", methods=["GET", "POST"])
def matches():
    db = g.db
    if request.method == "POST":
        date = request.form["date"]
        opponent = request.form["opponent"]
        goals = request.form.get("goals")
        goals_against = request.form.get("goals_against")
        competition = request.form.get("competition", "")
        location = request.form.get("location", "")

        m = Match(
            date=date,
            opponent=opponent,
            goals=int(goals) if goals and goals.isdigit() else None,
            goals_against=int(goals_against) if goals_against and goals_against.isdigit() else None,
            competition=competition,
            location=location,
        )
        db.add(m)
        db.flush()  # assign id
        return redirect(url_for("match_lineup", match_id=m.id))

    matches = db.query(Match).order_by(Match.date.desc()).all()
    players = db.query(Player).order_by(Player.name).all()
    return render_template("matches.html", matches=matches, players=players)


@app.route("/trainings", methods=["GET", "POST"])
def trainings():
    db = g.db
    if request.method == "POST":
        date = request.form["date"]
        t = Training(date=date)
        db.add(t)
        db.flush()
        return redirect(url_for("training_attendance", training_id=t.id))

    trainings = db.query(Training).order_by(Training.date.desc()).all()
    players = db.query(Player).order_by(Player.name).all()
    training_summary = compute_training_attendance(db)
    return render_template(
        "trainings.html",
        trainings=trainings,
        players=players,
        training_summary=training_summary,
    )


@app.route("/matches/<int:match_id>/lineup", methods=["GET", "POST"])
def match_lineup(match_id):
    db = g.db
    players = db.query(Player).order_by(Player.name).all()

    if request.method == "POST":
        # Remove existing stats for this match
        db.query(MatchPlayerStat).filter_by(match_id=match_id).delete()

        for p in players:
            pid = p.id
            attended = request.form.get(f"attended_{pid}") == "on"
            goals = int(request.form.get(f"goals_{pid}", "0") or 0)
            assists = int(request.form.get(f"assists_{pid}", "0") or 0)
            yellow = int(request.form.get(f"yellow_{pid}", "0") or 0)
            red = int(request.form.get(f"red_{pid}", "0") or 0)
            goalkeeper = request.form.get(f"goalkeeper_{pid}") == "on"
            referee = request.form.get(f"referee_{pid}") == "on"

            if (
                attended
                or goals != 0
                or assists != 0
                or yellow != 0
                or red != 0
                or goalkeeper
                or referee
            ):
                row = MatchPlayerStat(
                    match_id=match_id,
                    player_id=pid,
                    attended=attended,
                    goals=goals,
                    assists=assists,
                    yellow=yellow,
                    red=red,
                    goalkeeper=goalkeeper,
                    referee=referee,
                )
                db.add(row)

        return redirect(url_for("matches"))

    # GET: prefill stats
    stats_for_match = db.query(MatchPlayerStat).filter_by(match_id=match_id).all()
    stats_by_player = {}
    for r in stats_for_match:
        stats_by_player[r.player_id] = {
            "attended": "1" if r.attended else "0",
            "goals": str(r.goals or 0),
            "assists": str(r.assists or 0),
            "yellow": str(r.yellow or 0),
            "red": str(r.red or 0),
            "goalkeeper": "1" if r.goalkeeper else "0",
            "referee": "1" if r.referee else "0",
        }

    return render_template(
        "match_lineup.html",
        match_id=match_id,
        players=players,
        stats_by_player=stats_by_player,
    )



@app.route("/players/<int:player_id>")
def player_detail(player_id):
    db = g.db

    player = db.get(Player, player_id)
    if player is None:
        return f"Player {player_id} not found", 404

    matches = db.query(Match).all()
    match_players = db.query(MatchPlayerStat).all()
    trainings = db.query(Training).all()
    training_att = db.query(TrainingAttendance).all()

    # Filter match stats for this player
    mp_rows = [r for r in match_players if r.player_id == player_id]

    matches_played = sum(1 for r in mp_rows if r.attended)
    goals = sum(r.goals or 0 for r in mp_rows)
    assists = sum(r.assists or 0 for r in mp_rows)
    yellow = sum(r.yellow or 0 for r in mp_rows)
    red = sum(r.red or 0 for r in mp_rows)

    # keeper/referee fractional games
    keepers_by_match = {}
    refs_by_match = {}
    for row in match_players:
        mid = row.match_id
        if row.goalkeeper:
            keepers_by_match.setdefault(mid, []).append(row.player_id)
        if row.referee:
            refs_by_match.setdefault(mid, []).append(row.player_id)

    keeper_games = 0.0
    referee_games = 0.0
    for row in mp_rows:
        mid = row.match_id
        if row.goalkeeper:
            keepers = keepers_by_match.get(mid, [])
            n = len(keepers)
            if n > 0:
                keeper_games += 1.0 / n
        if row.referee:
            refs = refs_by_match.get(mid, [])
            n = len(refs)
            if n > 0:
                referee_games += 1.0 / n

    matches_by_id = {m.id: m for m in matches}
    per_match_stats = []
    for r in mp_rows:
        m = matches_by_id.get(r.match_id)
        if not m:
            continue
        per_match_stats.append({
            "match_id": m.id,
            "date": m.date,
            "opponent": m.opponent,
            "competition": m.competition or "",
            "location": m.location or "",
            "attended": "1" if r.attended else "0",
            "goals": str(r.goals or 0),
            "assists": str(r.assists or 0),
            "yellow": str(r.yellow or 0),
            "red": str(r.red or 0),
            "goalkeeper": "1" if r.goalkeeper else "0",
            "referee": "1" if r.referee else "0",
        })

    # trainings for this player
    tr_rows = [r for r in training_att if r.player_id == player_id]
    trainings_by_id = {t.id: t for t in trainings}
    per_training = []
    for r in tr_rows:
        t = trainings_by_id.get(r.training_id)
        if not t:
            continue
        per_training.append({
            "training_id": t.id,
            "date": t.date,
            "location": t.location or "",
            "attended": "1" if r.attended else "0",
        })

    trainings_attended = sum(1 for r in tr_rows if r.attended)
    total_trainings = len(trainings)
    trainings_per_match = (
        trainings_attended / matches_played if matches_played > 0 else 0
    )

    # Sort matches by date for time series
    per_match_stats_sorted = sorted(per_match_stats, key=lambda m: m['date'])
    chart_labels = [m['date'] for m in per_match_stats_sorted]

    # Cumulative matches
    matches_series = list(range(1, len(per_match_stats_sorted) + 1))

    # Cumulative goals and assists
    cumulative_goals = []
    cumulative_assists = []
    goals_total = 0
    assists_total = 0

    for m in per_match_stats_sorted:
        goals_total += int(m.get('goals', 0) or 0)
        assists_total += int(m.get('assists', 0) or 0)
        cumulative_goals.append(goals_total)
        cumulative_assists.append(assists_total)

    # Trainings progress: cumulative attended by training date (unchanged)
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
        goals_series=cumulative_goals,          # now cumulative
        assists_series=cumulative_assists,      # new series
        training_labels=training_labels,
        training_series=training_series,
    )

@app.route("/trainings/<int:training_id>/attendance", methods=["GET", "POST"])
def training_attendance(training_id):
    db = g.db
    players = db.query(Player).order_by(Player.name).all()

    if request.method == "POST":
        # delete existing rows for this training
        db.query(TrainingAttendance).filter_by(training_id=training_id).delete()

        for p in players:
            pid = p.id
            attended = request.form.get(f"attended_{pid}") == "on"
            if attended:
                row = TrainingAttendance(
                    training_id=training_id,
                    player_id=pid,
                    attended=True,
                )
                db.add(row)

        return redirect(url_for("trainings"))

    # GET: prefill attendance
    att_for_training = db.query(TrainingAttendance).filter_by(
        training_id=training_id
    ).all()
    present_ids = {r.player_id for r in att_for_training}

    return render_template(
        "training_attendance.html",
        training_id=training_id,
        players=players,
        present_ids=present_ids,
    )

@app.route("/matches/<int:match_id>/edit", methods=["GET", "POST"])
def edit_match(match_id):
    db = g.db
    match = db.get(Match, match_id)

    if match is None:
        return f"Match {match_id} not found", 404

    if request.method == "POST":
        match.date = request.form["date"]
        match.opponent = request.form["opponent"]
        match.competition = request.form.get("competition", "").strip()
        match.location = request.form.get("location", "").strip()

        goals = request.form.get("goals", "").strip()
        goals_against = request.form.get("goals_against", "").strip()

        match.goals = int(goals) if goals else None
        match.goals_against = int(goals_against) if goals_against else None

        # Your teardown_request function commits g.db automatically.
        return redirect(url_for("matches"))

    return render_template("match_edit.html", match=match)

if __name__ == "__main__":
    app.run(debug=True, port=8000)