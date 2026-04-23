from flask import Flask, request, jsonify, g, render_template
import sqlite3
import time

app = Flask(__name__)
DB_NAME = 'students.db'

"""
DATABASE

defining
    connections
    constant sql queries
"""

CREATE_TABLE="create table if not exists students(id integer primary key, name text not null, marks integer not null)"

SELECT_QUERY="select * from students"

SELECT_QUERY_BY_ID="select * from students where id=?"

CREATE_STUDENT = "insert into students (id,name,marks) values(?,?,?)"

UPDATE_STUDENT = "update students set name=?, marks=? where id=?"

DELETE_STUDENT = "delete from students where id=?"


# establishing the connection
def db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn
# initializing DB
def init_db():
    conn = db()
    curr = conn.cursor()
    
    curr.execute(CREATE_TABLE)
    conn.commit()
    conn.close()

def row_to_dict(row):
    return {
        "id": row[0],
        "name": row[1],
        "marks": row[2]
    }

# request tiemr
@app.before_request
def before():
    g.start = time.time()

@app.after_request
def after(resp):
    total = round((time.time() - g.start) * 1000, 2)
    
    resp.headers["X-Response-Time"] = f"{total} ms"
    resp.headers["X-Powered-By"] = "Flask+Sqlite3"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    
    print(f"{request.method} {request.path}-> {total} ms")
    
    return resp

# Home
@app.route("/")
def home():
    # return jsonify({
    #     "message": "Python API playground running",
    #     "routes": [
    #         "GET /students",
    #         "GET /students/<id>",
    #         "POST /students",
    #         "PUT /students/<id>",
    #         "PATCH /students/<id>",
    #         "DELETE /students/<id>",
    #         "GET /inspect"
    #     ]
    # })
    return render_template("index.html")

# inspect the request like POSTMAN
@app.route("/inspect", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def inspect():
    return jsonify({
        "method": request.method,
        "url": request.url,
        "headers": dict(request.headers),
        "query_params": request.args.to_dict(),
        "json_body": request.get_json(silent=True)
    })


# get all students
@app.route("/students", methods=["GET"])
def get_students():
    conn = db()
    curr = conn.cursor()
    
    curr.execute(SELECT_QUERY)
    
    rows = curr.fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in rows])

# get single student
@app.route("/students/<int:id>", methods=["GET"])
def get_student(id):
    conn = db()
    curr = conn.cursor()
    
    curr.execute(SELECT_QUERY_BY_ID, (id,))
    
    row = curr.fetchone()
    conn.close()
    
    if row:
        return jsonify(dict(row))
    
    return jsonify({"error": "student not found}"}), 404

# create a student
@app.route("/students", methods=["POST"])
def create_student():
    data = request.get_json()
    try:
        conn = db()
        curr = conn.cursor()
    
        curr.execute(CREATE_STUDENT, (
            data['id'],
            data['name'],
            data['marks']
        ))
        
        conn.commit()
        student_id = curr.lastrowid
        conn.close()
        
        return jsonify({
            "message": "Student Created",
            "id": student_id
        }), 201
        
    except sqlite3.IntegrityError:
        return jsonify({
            "error": "name already exists"
        }), 400

# full update
@app.route("/students/<int:id>", methods=["PUT"])
def update_student(id):
    data = request.get_json()
    
    conn = db()
    curr = conn.cursor()
    
    curr.execute(UPDATE_STUDENT, (
        data['name'],
        data['marks'],
        id
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Student updated"}), 200

# partial update
@app.route("/students/<int:id>", methods=["PATCH"])
def patch_student(id):
    data = request.get_json()
    
    conn = db()
    curr = conn.cursor()
    
    curr.execute(SELECT_QUERY_BY_ID, (id,))
    row = curr.fetchone()
    
    if not row:
        conn.close()
        return jsonify({"error": "Student not found"}), 404
    
    updated_name = data.get("name", row["name"])
    updated_age = data.get("marks", row["marks"])
    
    curr.execute(UPDATE_STUDENT, (updated_name, updated_age, id))
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Student's been patched"})

# delete a student
@app.route("/students/<int:id>", methods=["DELETE"])
def delete_student(id):
    conn = db()
    curr = conn.cursor()
    
    curr.execute(DELETE_STUDENT, (id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "student's been deleted"}), 200

@app.route("/students", methods=["DELETE"])
def clear_students():
    conn = db()
    curr = conn.cursor()
    
    curr.execute('delete from students')
    conn.commit()
    conn.close()
    
    return jsonify({
        "message": "all student data cleared"
    })

# start app
if __name__ == "__main__":
    init_db()
    app.run(debug=True)