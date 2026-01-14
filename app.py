from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user
)
from flask_migrate import Migrate
from config import Config
from models import EntryMedia, db, User, Entry, WeeklyReflection

from datetime import datetime, timedelta, date
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from werkzeug.utils import secure_filename
import io



# ================== APP SETUP ==================
app = Flask(__name__)
app.config.from_object(Config)

UPLOAD_FOLDER = os.path.join(app.root_path, 'static/uploads/images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ================== AUTH ROUTES ==================
@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))

        user = User(username=username)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('Account created. Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Invalid credentials')

    return render_template('login.html')


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if not user:
            flash('User not found')
            return redirect(url_for('reset_password'))

        user.set_password(new_password)
        db.session.commit()

        flash('Password reset successful. Please login.')
        return redirect(url_for('login'))

    return render_template('reset_password.html')


# ================== DASHBOARD ==================
@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user

    # Latest entries
    entries = Entry.query.filter_by(user_id=user.id)\
        .order_by(Entry.created_at.desc())\
        .limit(100)\
        .all()

    # ---- WEEKLY ANALYTICS ----
    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_entries = Entry.query.filter(
        Entry.user_id == user.id,
        Entry.created_at >= week_ago
    ).all()

    if weekly_entries:
        moods = [e.mood for e in weekly_entries]
        emotions = [e.emotion for e in weekly_entries]

        avg_mood = round(sum(moods) / len(moods), 1)
        max_mood = max(moods)
        min_mood = min(moods)
        common_emotion = max(set(emotions), key=emotions.count)

        sleeps = [e.sleep for e in weekly_entries if e.sleep]
        avg_sleep = round(sum(sleeps) / len(sleeps), 1) if sleeps else None
    else:
        avg_mood = max_mood = min_mood = common_emotion = avg_sleep = None

    # ---- STREAK LOGIC ----
    streak = 0
    if entries:
        dates = sorted({e.created_at.date() for e in entries}, reverse=True)
        today = date.today()

        for i, d in enumerate(dates):
            if d == today - timedelta(days=i):
                streak += 1
            else:
                break
    # ---- WEEKLY REFLECTION ----
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday

    weekly_reflection = WeeklyReflection.query.filter_by(
        user_id=user.id,
        week_start=week_start
    ).first()

    return render_template(
        'dashboard.html',
        user=user,
        entries=entries,
        weekly_entries=weekly_entries,
        avg_mood=avg_mood,
        max_mood=max_mood,
        min_mood=min_mood,
        common_emotion=common_emotion,
        avg_sleep=avg_sleep,
        streak=streak,
        weekly_reflection=weekly_reflection
    )


@app.route('/about')
def about():
    return render_template('about.html')

# ================== JOURNAL ENTRIES ==================
@app.route('/add-entry', methods=['POST'])
@login_required
def add_entry():
    content = request.form['content']
    mood = request.form['mood']
    emotion = request.form.get('emotion')
    energy = request.form.get('energy')
    sleep = request.form.get('sleep')
    
    jaw_tension = request.form.get('jaw_tension')
    shoulder_tension = request.form.get('shoulder_tension')
    stomach_discomfort = request.form.get('stomach_discomfort')
    headache = request.form.get('headache')

    if not content.strip():
        flash('Journal entry cannot be empty')
        return redirect(url_for('dashboard'))

    entry = Entry(
        content=content,
        mood=int(mood),
        emotion=emotion,
        energy=int(energy) if energy else None,
        sleep=int(sleep) if sleep else None,
        
        jaw_tension=int(jaw_tension) if jaw_tension else None,
        shoulder_tension=int(shoulder_tension) if shoulder_tension else None,
        stomach_discomfort=int(stomach_discomfort) if stomach_discomfort else None,
        headache=int(headache) if headache else None,

        trigger_event=request.form.get('trigger_event'),
        negative_thought=request.form.get('negative_thought'),
        reframed_thought=request.form.get('reframed_thought'),

        gratitude_1=request.form.get('gratitude_1'),
        gratitude_2=request.form.get('gratitude_2'),
        gratitude_3=request.form.get('gratitude_3'),
        affirmation=request.form.get('affirmation'),

        user_id=current_user.id
    )

    db.session.add(entry)
    db.session.commit()

        # ---- IMAGE UPLOAD ----
    if 'image' in request.files:
        file = request.files['image']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            media = EntryMedia(
                entry_id=entry.id,
                file_path=f'uploads/images/{filename}',
                media_type='image'
            )
            db.session.add(media)
            db.session.commit()

    flash('Journal entry saved with image 📸')
    return redirect(url_for('dashboard'))

@app.route('/edit-entry/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_entry(id):
    entry = Entry.query.get_or_404(id)

    if entry.user_id != current_user.id:
        flash('Unauthorized')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        entry.content = request.form['content']
        entry.mood = int(request.form['mood'])
        entry.emotion = request.form.get('emotion')
        entry.energy = int(request.form.get('energy'))
        entry.sleep = int(request.form.get('sleep'))

        db.session.commit()
        flash('Entry updated')
        return redirect(url_for('dashboard'))

    return render_template('edit_entry.html', entry=entry)

@app.route('/weekly-reflection', methods=['POST'])
@login_required
def save_weekly_reflection():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday

    reflection = WeeklyReflection.query.filter_by(
        user_id=current_user.id,
        week_start=week_start
    ).first()

    if not reflection:
        reflection = WeeklyReflection(
            user_id=current_user.id,
            week_start=week_start
        )

    reflection.boundary_check = request.form.get('boundary_check')
    reflection.weekly_goal = request.form.get('weekly_goal')

    db.session.add(reflection)
    db.session.commit()

    flash("Weekly reflection saved 🌱", "success")
    return redirect(url_for('dashboard'))

@app.route('/delete-entry/<int:id>')
@login_required
def delete_entry(id):
    entry = Entry.query.get_or_404(id)

    if entry.user_id != current_user.id:
        flash('Unauthorized')
        return redirect(url_for('dashboard'))

    db.session.delete(entry)
    db.session.commit()

    flash('Entry deleted')
    return redirect(url_for('dashboard'))


# ================== PROFILE ==================
@app.route('/profile')
@login_required
def profile():
    total_entries = Entry.query.filter_by(user_id=current_user.id).count()

    return render_template(
        'profile.html',
        user=current_user,
        total_entries=total_entries
    )


# ================== EXPORT PDF ==================
@app.route('/export-pdf')
@login_required
def export_pdf():
    entries = Entry.query.filter_by(user_id=current_user.id)\
        .order_by(Entry.created_at.desc())\
        .all()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    text = pdf.beginText(40, 750)
    text.setFont("Helvetica", 10)

    text.textLine("Mental Health Journal")
    text.textLine(f"User: {current_user.username}")
    text.textLine("-" * 50)

    for entry in entries:
        text.textLine("")
        text.textLine(entry.created_at.strftime('%Y-%m-%d %H:%M'))
        text.textLine(f"Mood: {entry.mood}/5 | Emotion: {entry.emotion}")
        text.textLine(entry.content)

    pdf.drawText(text)
    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="journal_entries.pdf",
        mimetype="application/pdf"
    )


# ================== LOGOUT ==================
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)

