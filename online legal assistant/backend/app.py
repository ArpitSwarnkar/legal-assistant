
import sqlite3
import re
from datetime import datetime
import os
print("GROQ KEY:", os.getenv("GROQ_API_KEY"))

from flask import session, Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from rapidfuzz import process
from groq import Groq

# 📄 PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# 🔑 GROQ CLIENT
if not os.getenv("GROQ_API_KEY"):
    print("⚠️ GROQ API KEY NOT FOUND")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 🚀 FLASK APP
app = Flask(__name__,
            template_folder="../frontend",
            static_folder="../frontend")

app.secret_key = "super_secret_key"
CORS(app, supports_credentials=True)

# 🔥 FAQ
LEGAL_FAQ = {
    "fir": "You can file FIR under Section 154 CrPC.",
    "cyber crime": "Report at cybercrime.gov.in or call 1930.",
    "lost mobile": "Block IMEI at ceir.gov.in.",
    "domestic violence": "Call 1091 or file complaint.",

}
# 🔥 CLEAN TEXT
def clean_text(text):
    return re.sub(r'[^a-z\s]', '', text.lower())

# 🤖 ANSWER FUNCTION
def get_answer(query):
    q = clean_text(query)

    # Only trigger FAQ if very short query
    if len(q.split()) <= 2:
        best_match = process.extractOne(q, LEGAL_FAQ.keys())
        if best_match:
            key, score, _ = best_match
            if score > 90:
                return LEGAL_FAQ[key]

    # Otherwise use AI
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional Indian legal assistant. Give detailed and helpful legal guidance."
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        print("GROQ ERROR:", e)
        return "Error"
# 🔐 REGISTER
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    conn = sqlite3.connect("legal_assistant.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (data["email"], data["password"])
        )
        conn.commit()
        return jsonify({"message": "Registered"})
    except:
        return jsonify({"error": "Email exists"}), 400
    finally:
        conn.close()

# 🔐 LOGIN
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    conn = sqlite3.connect("legal_assistant.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE email=? AND password=?",
        (data["email"], data["password"])
    )

    user = cursor.fetchone()
    conn.close()

    if user:
        session["user_id"] = user[0]
        return jsonify({"message": "Login success"})
    return jsonify({"error": "Invalid"}), 401

# 💬 ASK
@app.route("/api/ask", methods=["POST"])
def ask():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    question = data["question"]
    user_id = session["user_id"]

    answer = get_answer(question)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("legal_assistant.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO chats VALUES (NULL,?,?,?,?)",
                   (user_id, question, "user", now))

    cursor.execute("INSERT INTO chats VALUES (NULL,?,?,?,?)",
                   (user_id, answer, "bot", now))

    conn.commit()
    conn.close()

    return jsonify({"answer": answer})

# 📜 HISTORY
@app.route("/api/history")
def history():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = sqlite3.connect("legal_assistant.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT message, sender, created_at FROM chats WHERE user_id=?",
        (session["user_id"],)
    )

    chats = cursor.fetchall()
    conn.close()

    return jsonify({"chats": chats})

# 📄 EXPORT PDF
@app.route("/api/export-pdf")
def export_pdf():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]

    conn = sqlite3.connect("legal_assistant.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT message, sender, created_at FROM chats WHERE user_id=?",
        (user_id,)
    )

    chats = cursor.fetchall()
    conn.close()

    file_path = f"chat_{user_id}.pdf"

    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()
    content = []

    for msg, sender, time in chats:
        content.append(Paragraph(f"{sender} ({time}): {msg}", styles["Normal"]))
        content.append(Spacer(1, 10))

    doc.build(content)

    return send_file(file_path, as_attachment=True)

# 🌐 PAGES
@app.route("/")
def login_page():
    return render_template("index.html")

@app.route("/home")
def home():
    return render_template("home.html")

# 🔓 LOGOUT
@app.route("/api/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})

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

# 🚀 RUN
import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))