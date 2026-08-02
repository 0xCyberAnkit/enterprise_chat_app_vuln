import sqlite3
import os

DB_PATH = 'enterprise_chat.db'

def init_db():
    # Remove existing DB if it exists for clean initialization
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            department TEXT DEFAULT 'General',
            title TEXT DEFAULT 'Employee',
            internal_profile TEXT,
            bio TEXT DEFAULT 'Hey there! I am using Nexus Connect.'
        )
    ''')

    # Create messages table
    cursor.execute('''
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT,
            content TEXT NOT NULL,
            channel TEXT DEFAULT 'general',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert dummy users (REALISTIC CORPORATE DATA)
    users = [
        ('a.mercer', 'admin123', 'admin', 'Executive', 'Chief Executive Officer', 'CONFIDENTIAL: Project Titan acquisition finalizing Q3. Max bid 450M. Do not discuss outside executive committee.', 'Visionary CEO of CorpNet.'),
        ('j.doe', 'password123', 'user', 'Engineering', 'Senior Developer', 'Standard employee profile.', 'Code is poetry.'),
        ('s.smith', 'password123', 'user', 'HR', 'HR Director', 'CONFIDENTIAL: Q4 Layoff list finalized. Departments affected: Sales, Marketing.', 'Passionate about people.'),
        ('t.admin', 'password123', 'admin', 'IT Operations', 'SysAdmin', 'CONFIDENTIAL: Production Database Credentials - Host: 10.0.4.55, User: sa_prod_backup, Pass: P@ssw0rd_B@ckup_2026!', 'Keeping the lights on.')
    ]
    cursor.executemany('INSERT INTO users (username, password, role, department, title, internal_profile, bio) VALUES (?, ?, ?, ?, ?, ?, ?)', users)

    # Insert some initial chat messages (General)
    messages = [
        ('a.mercer', 'Welcome everyone to Nexus Connect! This is our new secure communication platform.', 'general', None),
        ('t.admin', 'Please note that the IT diagnostic tools are now available for sysadmins only. <div class="mt-2 flex gap-1"><span class="inline-flex items-center gap-1 bg-[#313338] border border-[#2B2D31] px-2 py-0.5 rounded-md text-xs text-[#DBDEE1] hover:bg-[#3F4147] cursor-pointer transition-colors">👍 <span class="font-bold">4</span></span></div>', 'general', None),
        ('j.doe', 'Has anyone seen the latest deployment logs?', 'general', None),
        ('s.smith', 'Don\'t forget to complete your mandatory security training by Friday. <br><a href="/api/attachments/download?file=policies/Q3_Security_Policy.pdf" target="_blank" class="mt-2 p-3 bg-[#2B2D31] border border-[#1E1F22] rounded-[8px] flex items-center gap-3 w-fit hover:bg-[#313338] transition-colors inline-block"><div class="w-10 h-10 bg-[#F23F43]/20 text-[#F23F43] rounded-lg flex items-center justify-center"><i class="fa-solid fa-file-pdf text-2xl"></i></div><div><p class="text-[13px] font-bold text-white hover:underline decoration-1 underline-offset-2">Q3_Security_Policy.pdf</p><p class="text-[11px] text-[#949BA4]">2.4 MB</p></div></a>', 'general', None)
    ]
    cursor.executemany('INSERT INTO messages (sender, content, channel, receiver) VALUES (?, ?, ?, ?)', messages)

    # Insert some direct messages
    dms = [
        ('a.mercer', 't.admin', 'I need the backup credentials ASAP.', 'dm'),
        ('t.admin', 'a.mercer', 'I will share them securely. <br><a href="/api/attachments/download?file=Encrypted_Payload.vault" target="_blank" class="mt-2 p-3 bg-[#2B2D31] border border-[#1E1F22] rounded-[8px] flex items-center gap-3 w-fit hover:bg-[#313338] transition-colors inline-block"><div class="w-10 h-10 bg-[#23A559]/20 text-[#23A559] rounded-lg flex items-center justify-center"><i class="fa-solid fa-lock text-xl"></i></div><div><p class="text-[13px] font-bold text-white hover:underline decoration-1 underline-offset-2">Encrypted_Payload.vault</p><p class="text-[11px] text-[#949BA4]">45 KB</p></div></a>', 'dm'),
        ('j.doe', 's.smith', 'When is the next all-hands meeting?', 'dm')
    ]
    cursor.executemany('INSERT INTO messages (sender, receiver, content, channel) VALUES (?, ?, ?, ?)', dms)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
