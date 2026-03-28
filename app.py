from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import json
import datetime
import random
import os

app = Flask(__name__, static_folder='.')
CORS(app)

# Admin email - change to your email
ADMIN_EMAIL = 'mjoga289@gmail.com'
DB_NAME = 'data.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        ffid TEXT,
        phone TEXT,
        coins INTEGER DEFAULT 0,
        verified BOOLEAN DEFAULT 0,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        reward INTEGER,
        type TEXT,
        link TEXT,
        code TEXT,
        image_url TEXT,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tournaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        type TEXT,
        map TEXT,
        entry_fee INTEGER,
        max_players INTEGER,
        prize_pool TEXT,
        start_time TEXT,
        status TEXT,
        image_url TEXT,
        room_details TEXT,
        current_participants INTEGER DEFAULT 0,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tournament_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER,
        user_id INTEGER,
        ffid TEXT,
        phone TEXT,
        email TEXT,
        status TEXT,
        selection_round INTEGER,
        joined_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tournament_selections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER,
        round INTEGER,
        selected_count INTEGER,
        selected_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS completed_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task_id INTEGER,
        completed_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS popups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_url TEXT,
        link TEXT,
        text TEXT,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS about (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT,
        image_url TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # Insert default data if empty
    c.execute("SELECT * FROM about LIMIT 1")
    if not c.fetchone():
        c.execute("INSERT INTO about (content, image_url) VALUES (?, ?)",
                  ("১. চিটিং নিষিদ্ধ\n২. লেভেল ৫০+", ""))
    
    c.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
              ("global_notice", "নতুন টুর্নামেন্ট শীঘ্রই আসছে..."))
    
    c.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
              ("support", json.dumps({"whatsapp": "8801234567890", "telegram": "https://t.me/tunff09"})))
    
    # Insert demo admin user if not exists
    c.execute("SELECT * FROM users WHERE email=?", (ADMIN_EMAIL,))
    if not c.fetchone():
        c.execute("INSERT INTO users (email, password, ffid, phone, coins, created_at) VALUES (?,?,?,?,?,?)",
                  (ADMIN_EMAIL, "admin123", "ADMIN_FFID", "8801234567890", 1000, datetime.datetime.now().isoformat()))
    
    # Insert demo task if empty
    c.execute("SELECT * FROM tasks LIMIT 1")
    if not c.fetchone():
        c.execute('''INSERT INTO tasks (title, description, reward, type, link, code, image_url, created_at)
                     VALUES (?,?,?,?,?,?,?,?)''',
                  ("স্যাম্পল টাস্ক", "টাস্ক সম্পন্ন করলে ১০ কয়েন পাবেন", 10, "daily", None, None, None,
                   datetime.datetime.now().isoformat()))
    
    # Insert demo tournament if empty
    c.execute("SELECT * FROM tournaments LIMIT 1")
    if not c.fetchone():
        c.execute('''INSERT INTO tournaments
                     (name, type, map, entry_fee, max_players, prize_pool, start_time, status, image_url, current_participants, created_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                  ("টেস্ট টুর্নামেন্ট", "solo", "bermuda", 5, 50, "500", 
                   "2025-04-01T20:00:00", "upcoming", None, 0, datetime.datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- User routes ----------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    ffid = data.get('ffid')
    phone = data.get('phone')
    if not all([email, password, ffid, phone]):
        return jsonify({'error': 'Missing fields'}), 400
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (email, password, ffid, phone, coins, created_at) VALUES (?,?,?,?,?,?)",
                  (email, password, ffid, phone, 20, datetime.datetime.now().isoformat()))
        conn.commit()
        user_id = c.lastrowid
        user = dict(c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
        conn.close()
        return jsonify({'success': True, 'user': user})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email already exists'}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    conn = get_db()
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()
    conn.close()
    if user:
        return jsonify({'success': True, 'user': dict(user)})
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/users', methods=['GET'])
def get_users():
    admin_email = request.args.get('admin_email')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

@app.route('/api/give_coins', methods=['POST'])
def give_coins():
    data = request.json
    admin_email = data.get('admin_email')
    user_id = data.get('user_id')
    amount = data.get('amount')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("UPDATE users SET coins = coins + ? WHERE id=?", (amount, user_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/delete_user', methods=['DELETE'])
def delete_user():
    data = request.json
    admin_email = data.get('admin_email')
    user_id = data.get('user_id')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.execute("DELETE FROM completed_tasks WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM tournament_participants WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/bulk_add_coins', methods=['POST'])
def bulk_add_coins():
    data = request.json
    admin_email = data.get('admin_email')
    emails = data.get('emails', [])
    amount = data.get('amount')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    for email in emails:
        conn.execute("UPDATE users SET coins = coins + ? WHERE email=?", (amount, email))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ---------- Task routes ----------
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    conn = get_db()
    tasks = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(t) for t in tasks])

@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.json
    admin_email = data.get('admin_email')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO tasks (title, description, reward, type, link, code, image_url, created_at)
                 VALUES (?,?,?,?,?,?,?,?)''',
              (data['title'], data['description'], data['reward'], data['type'],
               data.get('link'), data.get('code'), data.get('image_url'),
               datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    data = request.json
    admin_email = data.get('admin_email')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/complete_task', methods=['POST'])
def complete_task():
    data = request.json
    user_id = data.get('user_id')
    task_id = data.get('task_id')
    code_input = data.get('code')
    conn = get_db()
    done = conn.execute("SELECT * FROM completed_tasks WHERE user_id=? AND task_id=?", (user_id, task_id)).fetchone()
    if done:
        return jsonify({'error': 'Already completed'}), 400
    task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    if task['type'] == 'youtube_code' and code_input != task['code']:
        return jsonify({'error': 'Invalid code'}), 400
    conn.execute("INSERT INTO completed_tasks (user_id, task_id, completed_at) VALUES (?,?,?)",
                 (user_id, task_id, datetime.datetime.now().isoformat()))
    conn.execute("UPDATE users SET coins = coins + ? WHERE id=?", (task['reward'], user_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'reward': task['reward']})

# ---------- Tournament routes ----------
@app.route('/api/tournaments', methods=['GET'])
def get_tournaments():
    conn = get_db()
    tours = conn.execute("SELECT * FROM tournaments ORDER BY created_at DESC").fetchall()
    result = []
    for t in tours:
        d = dict(t)
        if d['room_details']:
            try:
                d['room_details'] = json.loads(d['room_details'])
            except:
                d['room_details'] = None
        result.append(d)
    conn.close()
    return jsonify(result)

@app.route('/api/tournaments', methods=['POST'])
def create_tournament():
    data = request.json
    admin_email = data.get('admin_email')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO tournaments
                 (name, type, map, entry_fee, max_players, prize_pool, start_time, status, image_url, current_participants, created_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
              (data['name'], data['type'], data['map'], data['entry_fee'], data['max_players'],
               data['prize_pool'], data['start_time'], 'upcoming', data.get('image_url'),
               0, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/tournaments/<int:tid>', methods=['DELETE'])
def delete_tournament(tid):
    data = request.json
    admin_email = data.get('admin_email')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("DELETE FROM tournaments WHERE id=?", (tid,))
    conn.execute("DELETE FROM tournament_participants WHERE tournament_id=?", (tid,))
    conn.execute("DELETE FROM tournament_selections WHERE tournament_id=?", (tid,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/join_tournament', methods=['POST'])
def join_tournament():
    data = request.json
    user_id = data.get('user_id')
    tournament_id = data.get('tournament_id')
    entry_fee = data.get('entry_fee')
    conn = get_db()
    existing = conn.execute("SELECT * FROM tournament_participants WHERE tournament_id=? AND user_id=?", (tournament_id, user_id)).fetchone()
    if existing:
        return jsonify({'error': 'Already joined'}), 400
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if user['coins'] < entry_fee:
        return jsonify({'error': 'Insufficient coins'}), 400
    conn.execute("UPDATE users SET coins = coins - ? WHERE id=?", (entry_fee, user_id))
    conn.execute("INSERT INTO tournament_participants (tournament_id, user_id, ffid, phone, email, status, joined_at) VALUES (?,?,?,?,?,?,?)",
                 (tournament_id, user_id, user['ffid'], user['phone'], user['email'], 'joined', datetime.datetime.now().isoformat()))
    conn.execute("UPDATE tournaments SET current_participants = current_participants + 1 WHERE id=?", (tournament_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/tournament_participants/<int:tid>', methods=['GET'])
def get_participants(tid):
    conn = get_db()
    parts = conn.execute("SELECT * FROM tournament_participants WHERE tournament_id=?", (tid,)).fetchall()
    conn.close()
    return jsonify([dict(p) for p in parts])

@app.route('/api/tournament_selections/<int:tid>', methods=['GET'])
def get_selections(tid):
    conn = get_db()
    selections = conn.execute("SELECT * FROM tournament_selections WHERE tournament_id=? ORDER BY round", (tid,)).fetchall()
    conn.close()
    return jsonify([dict(s) for s in selections])

@app.route('/api/select_random', methods=['POST'])
def select_random():
    data = request.json
    admin_email = data.get('admin_email')
    tournament_id = data.get('tournament_id')
    count = data.get('count')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    selected_before = conn.execute("SELECT user_id FROM tournament_participants WHERE tournament_id=? AND status IN ('selected', 'room_received')", (tournament_id,)).fetchall()
    selected_ids = [s['user_id'] for s in selected_before]
    eligible = conn.execute("SELECT * FROM tournament_participants WHERE tournament_id=? AND status='joined'", (tournament_id,)).fetchall()
    eligible = [p for p in eligible if p['user_id'] not in selected_ids]
    if not eligible:
        return jsonify({'error': 'No eligible players'}), 400
    selected = random.sample(eligible, min(count, len(eligible)))
    round_num = conn.execute("SELECT COUNT(*) as r FROM tournament_selections WHERE tournament_id=?", (tournament_id,)).fetchone()['r'] + 1
    for p in selected:
        conn.execute("UPDATE tournament_participants SET status='selected', selection_round=? WHERE id=?", (round_num, p['id']))
    conn.execute("INSERT INTO tournament_selections (tournament_id, round, selected_count, selected_at) VALUES (?,?,?,?)",
                 (tournament_id, round_num, len(selected), datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'selected_count': len(selected), 'round': round_num})

@app.route('/api/set_room', methods=['POST'])
def set_room():
    data = request.json
    admin_email = data.get('admin_email')
    tournament_id = data.get('tournament_id')
    room_id = data.get('room_id')
    password = data.get('password')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    room_details = json.dumps({'roomId': room_id, 'password': password})
    conn.execute("UPDATE tournaments SET room_details=?, status='ongoing' WHERE id=?", (room_details, tournament_id))
    conn.execute("UPDATE tournament_participants SET status='room_received' WHERE tournament_id=? AND status='selected'", (tournament_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/update_tournament_status', methods=['POST'])
def update_tournament_status():
    data = request.json
    admin_email = data.get('admin_email')
    tournament_id = data.get('tournament_id')
    status = data.get('status')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("UPDATE tournaments SET status=? WHERE id=?", (status, tournament_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/remove_participant', methods=['DELETE'])
def remove_participant():
    data = request.json
    admin_email = data.get('admin_email')
    participant_id = data.get('participant_id')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("DELETE FROM tournament_participants WHERE id=?", (participant_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/remove_user_from_all_tournaments', methods=['POST'])
def remove_user_from_all():
    data = request.json
    admin_email = data.get('admin_email')
    user_id = data.get('user_id')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("DELETE FROM tournament_participants WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ---------- Popup routes ----------
@app.route('/api/popups', methods=['GET'])
def get_popups():
    conn = get_db()
    popups = conn.execute("SELECT * FROM popups ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(p) for p in popups])

@app.route('/api/popups', methods=['POST'])
def create_popup():
    data = request.json
    admin_email = data.get('admin_email')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("INSERT INTO popups (image_url, link, text, created_at) VALUES (?,?,?,?)",
                 (data['image_url'], data.get('link'), data.get('text'), datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/popups/<int:popup_id>', methods=['DELETE'])
def delete_popup(popup_id):
    data = request.json
    admin_email = data.get('admin_email')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("DELETE FROM popups WHERE id=?", (popup_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ---------- About routes ----------
@app.route('/api/about', methods=['GET'])
def get_about():
    conn = get_db()
    about = conn.execute("SELECT * FROM about LIMIT 1").fetchone()
    conn.close()
    if about:
        return jsonify(dict(about))
    else:
        return jsonify({'content': '', 'image_url': ''})

@app.route('/api/about', methods=['POST'])
def update_about():
    data = request.json
    admin_email = data.get('admin_email')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("UPDATE about SET content=?, image_url=? WHERE id=1", (data['content'], data.get('image_url', '')))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ---------- Config routes ----------
@app.route('/api/config/global_notice', methods=['GET'])
def get_global_notice():
    conn = get_db()
    res = conn.execute("SELECT value FROM config WHERE key='global_notice'").fetchone()
    conn.close()
    return jsonify({'text': res['value'] if res else ''})

@app.route('/api/config/global_notice', methods=['POST'])
def set_global_notice():
    data = request.json
    admin_email = data.get('admin_email')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("UPDATE config SET value=? WHERE key='global_notice'", (data['text'],))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/config/support', methods=['GET'])
def get_support():
    conn = get_db()
    res = conn.execute("SELECT value FROM config WHERE key='support'").fetchone()
    conn.close()
    if res:
        return jsonify(json.loads(res['value']))
    else:
        return jsonify({'whatsapp': '', 'telegram': ''})

@app.route('/api/config/support', methods=['POST'])
def set_support():
    data = request.json
    admin_email = data.get('admin_email')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    conn.execute("UPDATE config SET value=? WHERE key='support'", (json.dumps({'whatsapp': data['whatsapp'], 'telegram': data['telegram']}),))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ---------- Backup/Restore ----------
@app.route('/api/backup', methods=['GET'])
def backup():
    admin_email = request.args.get('admin_email')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    tables = ['users', 'tasks', 'tournaments', 'tournament_participants', 'tournament_selections',
              'completed_tasks', 'popups', 'about', 'config']
    backup = {}
    for table in tables:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        backup[table] = [dict(row) for row in rows]
    conn.close()
    return jsonify(backup)

@app.route('/api/restore', methods=['POST'])
def restore():
    admin_email = request.json.get('admin_email')
    if admin_email != ADMIN_EMAIL:
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.json.get('backup')
    conn = get_db()
    conn.execute("PRAGMA foreign_keys = OFF")
    for table, rows in data.items():
        conn.execute(f"DELETE FROM {table}")
        if rows:
            for row in rows:
                cols = ', '.join(row.keys())
                placeholders = ', '.join(['?' for _ in row])
                values = list(row.values())
                conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", values)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Serve frontend
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    init_db()
    # Get port from environment variable for Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
