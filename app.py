from flask import Flask, request, jsonify, g, render_template, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import time

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

DB_NAME = "students.db"



# DATABASE QUERIES


CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
"""

CREATE_STUDENTS_TABLE = """
CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    marks INTEGER NOT NULL
)
"""



# DB CONNECTION
def db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    curr = conn.cursor()

    curr.execute(CREATE_USERS_TABLE)
    curr.execute(CREATE_STUDENTS_TABLE)

    conn.commit()
    conn.close()

# TIMER
@app.before_request
def before():
    g.start = time.time()

@app.after_request
def after(resp):
    total = round((time.time() - g.start) * 1000, 2)

    resp.headers["X-Response-Time"] = f"{total} ms"
    resp.headers["X-Powered-By"] = "Flask + SQLite"
    resp.headers["Access-Control-Allow-Origin"] = "*"

    print(f"{request.method} {request.path} -> {total} ms")

    return resp

# AUTH HELPERS
def is_logged_in():
    return "user_id" in session

# HOME
@app.route("/")
def home():
    if not is_logged_in():
        return redirect("/login")

    return render_template(
        "index.html",
        username=session["username"]
    )

# SIGNUP
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    data = request.form

    username = data["username"]
    email = data["email"]
    password = generate_password_hash(data["password"])

    conn = db()
    curr = conn.cursor()

    try:
        curr.execute(
            "INSERT INTO users(username,email,password) VALUES(?,?,?)",
            (username, email, password)
        )

        conn.commit()
        conn.close()

        return redirect("/login")

    except sqlite3.IntegrityError:
        conn.close()
        return "User already exists"

# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    data = request.form

    email = data["email"]
    password = data["password"]

    conn = db()
    curr = conn.cursor()

    curr.execute(
        "SELECT * FROM users WHERE email=?",
        (email,)
    )

    user = curr.fetchone()
    conn.close()

    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return redirect("/")

    return "Invalid credentials"

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# GET ALL STUDENTS
@app.route("/students", methods=["GET"])
def get_students():
    if not is_logged_in():
        return jsonify({"error": "Login required"}), 401

    conn = db()
    curr = conn.cursor()

    curr.execute(
        "SELECT * FROM students WHERE user_id=?",
        (session["user_id"],)
    )

    rows = curr.fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])

# GET SINGLE STUDENT
@app.route("/students/<int:id>", methods=["GET"])
def get_student(id):
    if not is_logged_in():
        return jsonify({"error": "Login required"}), 401

    conn = db()
    curr = conn.cursor()

    curr.execute(
        "SELECT * FROM students WHERE id=? AND user_id=?",
        (id, session["user_id"])
    )

    row = curr.fetchone()
    conn.close()

    if row:
        return jsonify(dict(row))

    return jsonify({"error": "Student not found"}), 404

# CREATE STUDENT
@app.route("/students", methods=["POST"])
def create_student():
    if not is_logged_in():
        return jsonify({"error": "Login required"}), 401

    data = request.get_json()

    conn = db()
    curr = conn.cursor()

    curr.execute(
        "INSERT INTO students(user_id,name,marks) VALUES(?,?,?)",
        (
            session["user_id"],
            data["name"],
            data["marks"]
        )
    )

    conn.commit()
    student_id = curr.lastrowid
    conn.close()

    return jsonify({
        "message": "Student created",
        "id": student_id
    }), 201

# FULL UPDATE
@app.route("/students/<int:id>", methods=["PUT"])
def update_student(id):
    if not is_logged_in():
        return jsonify({"error": "Login required"}), 401

    data = request.get_json()

    conn = db()
    curr = conn.cursor()

    curr.execute(
        """
        UPDATE students
        SET name=?, marks=?
        WHERE id=? AND user_id=?
        """,
        (
            data["name"],
            data["marks"],
            id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Student updated"})

# PATCH UPDATE
@app.route("/students/<int:id>", methods=["PATCH"])
def patch_student(id):
    if not is_logged_in():
        return jsonify({"error": "Login required"}), 401

    data = request.get_json()

    conn = db()
    curr = conn.cursor()

    curr.execute(
        "SELECT * FROM students WHERE id=? AND user_id=?",
        (id, session["user_id"])
    )

    row = curr.fetchone()

    if not row:
        conn.close()
        return jsonify({"error": "Student not found"}), 404

    updated_name = data.get("name", row["name"])
    updated_marks = data.get("marks", row["marks"])

    curr.execute(
        """
        UPDATE students
        SET name=?, marks=?
        WHERE id=? AND user_id=?
        """,
        (
            updated_name,
            updated_marks,
            id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Student patched"})


# DELETE SINGLE
@app.route("/students/<int:id>", methods=["DELETE"])
def delete_student(id):
    if not is_logged_in():
        return jsonify({"error": "Login required"}), 401

    conn = db()
    curr = conn.cursor()

    curr.execute(
        "DELETE FROM students WHERE id=? AND user_id=?",
        (id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Student deleted"})

# DELETE ALL MY STUDENTS
@app.route("/students", methods=["DELETE"])
def clear_students():
    if not is_logged_in():
        return jsonify({"error": "Login required"}), 401

    conn = db()
    curr = conn.cursor()

    curr.execute(
        "DELETE FROM students WHERE user_id=?",
        (session["user_id"],)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "All your students cleared"})

@app.route("/drop-students-table", methods=["POST"])
def drop_students_table():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    conn = db()
    curr = conn.cursor()

    curr.execute("DROP TABLE IF EXISTS students")
    curr.execute(CREATE_STUDENTS_TABLE)

    conn.commit()
    conn.close()

    return jsonify({
        "message": "students table dropped and recreated"
    })


# START APP
if __name__ == "__main__":
    init_db()
    app.run(debug=True)