from flask import Flask, render_template, request, g, redirect, url_for, make_response, render_template_string, send_file
import sqlite3
import os
import uuid

app = Flask(__name__)
app.secret_key = 'corpnet_enterprise_identity_key'
DATABASE = 'enterprise_chat.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# In-memory session store (vulnerable by design for fixation, but acts normal)
if not hasattr(app, 'sessions'):
    app.sessions = {}

def get_current_user():
    session_id = request.cookies.get('session_id')
    if not session_id:
        return None
    return getattr(app, 'sessions', {}).get(session_id)

@app.route('/', methods=['GET'])
def landing():
    return render_template('landing.html')

@app.route('/about', methods=['GET'])
def about():
    return render_template('about.html')

@app.route('/pricing', methods=['GET'])
def pricing():
    return render_template('pricing.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if exists
        cursor.execute("SELECT id FROM users WHERE username=?", (username,))
        if cursor.fetchone():
            return render_template('register.html', error="Email/Username already taken.")
            
        # Create new user
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        db.commit()
        
        # Auto-login after registration
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        
        session_id = str(uuid.uuid4())
        app.sessions[session_id] = {
            'id': user['id'], 
            'username': user['username'], 
            'role': user['role'],
            'title': user['title'],
            'department': user['department'],
            'bio': user['bio']
        }
        
        resp = make_response(redirect(url_for('app_chat')))
        resp.set_cookie('session_id', session_id)
        return resp
        
    return render_template('register.html')

@app.route('/app', methods=['GET', 'POST'])
@app.route('/app/<target_user>', methods=['GET', 'POST'])
def app_chat(target_user=None):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        content = request.form.get('content', '')
        if content:
            # Vulnerability 2: Stored XSS (hidden behind rich text processing logic)
            if target_user:
                cursor.execute("INSERT INTO messages (sender, receiver, content, channel) VALUES (?, ?, ?, ?)", (user['username'], target_user, content, 'dm'))
            else:
                cursor.execute("INSERT INTO messages (sender, content, channel) VALUES (?, ?, ?)", (user['username'], content, 'general'))
            db.commit()
        return redirect(url_for('app_chat', target_user=target_user) if target_user else url_for('app_chat'))

    if target_user:
        cursor.execute("""
            SELECT * FROM messages 
            WHERE channel='dm' 
            AND ((sender=? AND receiver=?) OR (sender=? AND receiver=?)) 
            ORDER BY timestamp ASC
        """, (user['username'], target_user, target_user, user['username']))
    else:
        cursor.execute("SELECT * FROM messages WHERE channel='general' ORDER BY timestamp ASC")
        
    messages = cursor.fetchall()
    
    cursor.execute("SELECT id, username, role, title FROM users")
    users = cursor.fetchall()

    return render_template('index.html', messages=messages, current_user=user, users=users, active_channel=target_user or 'general')

@app.route('/app/settings', methods=['GET', 'POST'])
def settings():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    message = None

    if request.method == 'POST':
        department = request.form.get('department', '')
        title = request.form.get('title', '')
        bio = request.form.get('bio', '')
        
        cursor.execute("UPDATE users SET department=?, title=?, bio=? WHERE id=?", (department, title, bio, user['id']))
        db.commit()
        
        # Update session
        user['department'] = department
        user['title'] = title
        user['bio'] = bio
        message = "Profile settings updated successfully."

    # Refresh user data
    cursor.execute("SELECT * FROM users WHERE id=?", (user['id'],))
    db_user = cursor.fetchone()
    
    return render_template('settings.html', current_user=db_user, message=message)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Vulnerability 5: Session Fixation (hidden as 'legacy SSO fallback')
    sso_token = request.args.get('sso_token')
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        db = get_db()
        cursor = db.cursor()

        # Vulnerability 1: SQL Injection (hidden as poorly written legacy auth wrapper)
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        
        try:
            cursor.execute(query)
            user = cursor.fetchone()
        except Exception as e:
            user = None

        if user:
            # Uses the sso_token if provided, otherwise generates a new one
            session_id = request.cookies.get('session_id')
            if not session_id:
                session_id = str(uuid.uuid4())
            
            app.sessions[session_id] = {
                'id': user['id'], 
                'username': user['username'], 
                'role': user['role'],
                'title': user['title'],
                'department': user['department']
            }
            
            resp = make_response(redirect(url_for('app_chat')))
            resp.set_cookie('session_id', session_id)
            return resp
        else:
            return render_template('login.html', error="Invalid Active Directory credentials", sso_token=sso_token)

    resp = make_response(render_template('login.html', sso_token=sso_token))
    if sso_token:
         resp.set_cookie('session_id', sso_token)
    return resp

@app.route('/logout')
def logout():
    session_id = request.cookies.get('session_id')
    if session_id in app.sessions:
        del app.sessions[session_id]
    resp = make_response(redirect(url_for('login')))
    resp.delete_cookie('session_id')
    return resp

@app.route('/api/directory/profile/<user_id>')
def view_profile(user_id):
    # Vulnerability 3: IDOR (hidden as an API endpoint intended only for internal HR apps)
    current_user = get_current_user()
    if not current_user:
        return {"error": "Unauthorized Access (401)"}, 401
        
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT username, role, department, title, internal_profile, bio FROM users WHERE id=?", (user_id,))
    target_user = cursor.fetchone()
    
    if target_user:
        return {
            "username": target_user['username'],
            "role": target_user['role'],
            "department": target_user['department'],
            "title": target_user['title'],
            "internal_profile": target_user['internal_profile'],
            "bio": target_user['bio']
        }
    return {"error": "User not found in Active Directory"}, 404

@app.route('/api/attachments/download')
def download_attachment():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
        
    filename = request.args.get('file')
    if not filename:
        return "No file specified", 400
        
    # Vulnerability 6a: Local File Inclusion (Download)
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'attachments')
    file_path = os.path.join(base_dir, filename)
    
    try:
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return f"Error downloading file: {str(e)}", 404

@app.route('/api/attachments/view')
def view_attachment():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
        
    filename = request.args.get('file')
    if not filename:
        return "No file specified", 400
        
    # Vulnerability 6b: Local File Inclusion (View Inline)
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'attachments')
    file_path = os.path.join(base_dir, filename)
    
    try:
        return send_file(file_path, mimetype='text/plain')
    except Exception as e:
        return f"Error viewing file: {str(e)}", 404

@app.route('/it/noc/diagnostics', methods=['GET', 'POST'])
def diagnostics():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
        
    if user.get('role') != 'admin':
        return render_template_string("""
            <div style="font-family: monospace; padding: 50px; text-align: center;">
                <h1 style="color: #ef4444;">403 Forbidden</h1>
                <p>Access Denied: This utility requires 'admin' privileges.</p>
                <a href="/app" style="color: #3b82f6;">Return to Workspace</a>
            </div>
        """), 403

    result = None
    if request.method == 'POST':
        target_host = request.form.get('target', '127.0.0.1')
        
        # Vulnerability 4: Command Injection (hidden in an internal ping tool)
        try:
            command = f"ping -n 1 {target_host}" if os.name == 'nt' else f"ping -c 1 {target_host}"
            result = os.popen(command).read()
        except Exception as e:
            result = "Error executing network diagnostic test."
            
    return render_template('diagnostics.html', result=result)

if __name__ == '__main__':
    app.run(debug=True, port=5011)
