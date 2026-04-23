import sqlite3
import re
import os
from datetime import datetime

from flask import session, Flask, request, jsonify, render_template
from flask_cors import CORS
from rapidfuzz import process
from groq import Groq

# 🚀 FLASK APP
app = Flask(__name__)

app.config['SESSION_COOKIE_SAMESITE'] = "None"
app.config['SESSION_COOKIE_SECURE'] = True
app.secret_key = "super_secret_key"

CORS(app, supports_credentials=True, origins=[
    "https://legal-assistant-nmki.onrender.com"
])

# 🔥 FAQ
LEGAL_FAQ = {
    "fir": "You can file FIR under Section 154 CrPC.",
    "cyber crime": "Report at cybercrime.gov.in or call 1930.",
    "lost mobile": "Block IMEI at ceir.gov.in.",
    "domestic violence": "Call 1091 or file complaint.",
}

# 🧹 CLEAN TEXT
def clean_text(text):
    return re.sub(r'[^a-z\s]', '', text.lower())

# 🗄️ DB INIT
def init_db():
    conn = sqlite3.connect("legal_assistant.db")
    cursor = conn.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT)""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        sender TEXT,
        created_at TEXT)""")

    conn.commit()
    conn.close()

init_db()

# 🤖 AI FUNCTION (FIXED)
def get_answer(query):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("❌ API KEY MISSING ON RENDER")
        return "❌ AI service not configured. Add GROQ_API_KEY in Render."

    client = Groq(api_key=api_key)

    q = clean_text(query)

    # FAQ shortcut
    if len(q.split()) <= 2:
        best_match = process.extractOne(q, LEGAL_FAQ.keys())
        if best_match:
            key, score, _ = best_match
            if score > 90:
                return LEGAL_FAQ[key]

    try:
        # 🥇 Primary model
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional Indian legal assistant."},
                {"role": "user", "content": query}
            ]
        )
        return response.choices[0].message.content

    except Exception as e:
        print("Primary model failed:", e)

        try:
            # 🥈 Fallback model
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a professional Indian legal assistant."},
                    {"role": "user", "content": query}
                ]
            )
            return response.choices[0].message.content

        except Exception as e2:
            print("Fallback failed:", e2)
            return f"❌ GROQ ERROR: {str(e2)}"

# 🔐 REGISTER
@app.route("/api/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        conn = sqlite3.connect("legal_assistant.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email, password)
        )
        conn.commit()
        conn.close()

        return jsonify({"message": "Registered"})

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 🔐 LOGIN
@app.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        conn = sqlite3.connect("legal_assistant.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE email=? AND password=?",
            (email, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return jsonify({"message": "Login success"})
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 💬 ASK
@app.route("/api/ask", methods=["POST"])
def ask():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    question = data.get("question")

    answer = get_answer(question)
    return jsonify({"answer": answer})

# 🌐 PAGES
@app.route("/")
def login_page():
    return render_template("index.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/home")
def home():
    return render_template("home.html")

# 🚀 RUN
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

