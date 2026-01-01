from flask import Flask, render_template, request, redirect, session, flash
import sqlite3, os, uuid
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "hostel_secret"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DB ----------------
def get_db():
    db = sqlite3.connect("database.db")
    db.row_factory = sqlite3.Row
    return db

def init_db():
    if not os.path.exists("database.db"):
        db = get_db()
        with open("database.sql") as f:
            db.executescript(f.read())

        db.execute("""
            INSERT INTO users(username,password,role,approved)
            VALUES (?,?,?,1)
        """, ("admin", generate_password_hash("admin123"), "admin"))

        db.commit()
        db.close()
        print("Database initialized")

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        db.close()

        if user and check_password_hash(user["password"], p):
            if user["approved"] == 0:
                flash("Account waiting for approval")
                return redirect("/")

            session["uid"] = user["id"]
            session["role"] = user["role"]
            session["college"] = user["college"]
            session["username"] = user["username"]
            return redirect(f"/{user['role']}")

        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- REGISTER ----------------
@app.route("/register/<role>", methods=["GET","POST"])
def register(role):
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        college = request.form.get("college")

        id_card = None
        if role == "student":
            file = request.files["id_card"]
            id_card = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            file.save(os.path.join(UPLOAD_FOLDER, id_card))

        db = get_db()
        db.execute("""
            INSERT INTO users(username,password,role,college,id_card)
            VALUES (?,?,?,?,?)
        """, (username, password, role, college, id_card))
        db.commit()
        db.close()

        flash("Registered successfully. Wait for approval.")
        return redirect("/")

    return render_template(f"{role}_register.html")

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/")

    db = get_db()
    principals = db.execute("""
        SELECT * FROM users WHERE role='principal' AND approved=0
    """).fetchall()
    db.close()
    return render_template("admin_dashboard.html", principals=principals)

@app.route("/admin/approve/<int:uid>")
def admin_approve(uid):
    if session.get("role") != "admin":
        return redirect("/")

    db = get_db()
    db.execute("UPDATE users SET approved=1 WHERE id=?", (uid,))
    db.commit()
    db.close()
    return redirect("/admin")

# ---------------- PRINCIPAL ----------------
@app.route("/principal")
def principal():
    if session.get("role") != "principal":
        return redirect("/")

    db = get_db()

    # pending students & wardens of SAME college
    pending_users = db.execute("""
        SELECT * FROM users
        WHERE role IN ('student','warden')
        AND approved=0
        AND college=?
    """, (session["college"],)).fetchall()

    # pending hostel applications
    applications = db.execute("""
        SELECT a.id, u.username, h.name, h.id AS hostel_id, u.id AS student_id
        FROM applications a
        JOIN users u ON a.student_id=u.id
        JOIN hostels h ON a.hostel_id=h.id
        WHERE a.status='pending'
        AND u.college=?
    """, (session["college"],)).fetchall()

    db.close()

    return render_template(
        "principal_dashboard.html",
        students=pending_users,
        apps=applications
    )


@app.route("/principal/approve_user/<int:uid>")
def principal_approve_user(uid):
    if session.get("role") != "principal":
        return redirect("/")

    db = get_db()
    db.execute("UPDATE users SET approved=1 WHERE id=?", (uid,))
    db.commit()
    db.close()

    return redirect("/principal")


@app.route("/principal/reject_user/<int:uid>")
def principal_reject_user(uid):
    if session.get("role") != "principal":
        return redirect("/")

    db = get_db()
    db.execute("DELETE FROM users WHERE id=?", (uid,))
    db.commit()
    db.close()

    return redirect("/principal")


@app.route("/principal/approve_hostel/<int:aid>")
def principal_approve_hostel(aid):
    if session.get("role") != "principal":
        return redirect("/")

    db = get_db()

    app_data = db.execute("""
        SELECT student_id, hostel_id
        FROM applications
        WHERE id=?
    """, (aid,)).fetchone()

    if not app_data:
        db.close()
        return redirect("/principal")

    # get one free room
    room = db.execute("""
        SELECT id FROM rooms
        WHERE hostel_id=? AND is_allocated=0
        LIMIT 1
    """, (app_data["hostel_id"],)).fetchone()

    if room:
        # allocate room
        db.execute("""
            UPDATE rooms
            SET is_allocated=1, student_id=?
            WHERE id=?
        """, (app_data["student_id"], room["id"]))

        # update hostel availability
        db.execute("""
            UPDATE hostels
            SET available_rooms = available_rooms - 1
            WHERE id=?
        """, (app_data["hostel_id"],))

        # mark application approved
        db.execute("""
            UPDATE applications
            SET status='approved'
            WHERE id=?
        """, (aid,))

    db.commit()
    db.close()

    return redirect("/principal")

# ---------------- STUDENT ----------------
@app.route("/student")
def student():
    if session.get("role") != "student":
        return redirect("/")

    db = get_db()
    hostels = db.execute("""
        SELECT * FROM hostels
        WHERE college=? AND available_rooms>0
    """, (session["college"],)).fetchall()

    photos = db.execute("""
        SELECT rp.filename FROM room_photos rp
        JOIN hostels h ON rp.hostel_id=h.id
        WHERE h.college=?
    """, (session["college"],)).fetchall()

    db.close()
    return render_template("student_dashboard.html",
                           hostels=hostels,
                           photos=photos)

@app.route("/student/apply/<int:hid>")
def apply_hostel(hid):
    if session.get("role") != "student":
        return redirect("/")

    db = get_db()
    db.execute("""
        INSERT INTO applications(student_id,hostel_id)
        VALUES (?,?)
    """, (session["uid"], hid))
    db.commit()
    db.close()
    return redirect("/student")

# ---------------- WARDEN ----------------

@app.route("/warden")
def warden():
    if session.get("role") != "warden":
        return redirect("/")

    db = get_db()

    # approved students of same college
    students = db.execute("""
        SELECT id, username FROM users
        WHERE role='student' AND approved=1 AND college=?
    """, (session["college"],)).fetchall()

    # attendance taken by this warden
    attendance = db.execute("""
        SELECT u.username, a.date, a.status
        FROM attendance a
        JOIN users u ON a.student_id = u.id
        WHERE a.warden_id=?
        ORDER BY a.date DESC
    """, (session["uid"],)).fetchall()

    # hostels handled by this warden
    hostels = db.execute("""
        SELECT * FROM hostels
        WHERE warden_id=?
    """, (session["uid"],)).fetchall()

    # rooms of those hostels
    rooms = db.execute("""
        SELECT r.room_number, h.name AS hostel_name
        FROM rooms r
        JOIN hostels h ON r.hostel_id=h.id
        WHERE h.warden_id=?
    """, (session["uid"],)).fetchall()

    # uploaded photos
    photos = db.execute("""
        SELECT * FROM room_photos
        WHERE warden_id=?
    """, (session["uid"],)).fetchall()

    db.close()

    return render_template(
        "warden_dashboard.html",
        students=students,
        attendance=attendance,
        hostels=hostels,
        rooms=rooms,
        photos=photos
    )


@app.route("/warden/add_hostel", methods=["POST"])
def warden_add_hostel():
    if session.get("role") != "warden":
        return redirect("/")

    name = request.form["hostel_name"]
    total_rooms = int(request.form["total_rooms"])

    db = get_db()

    cur = db.execute("""
        INSERT INTO hostels (name, college, warden_id, total_rooms, available_rooms)
        VALUES (?,?,?,?,?)
    """, (
        name,
        session["college"],
        session["uid"],
        total_rooms,
        total_rooms
    ))

    hostel_id = cur.lastrowid

    # create room numbers
    for i in range(1, total_rooms + 1):
        db.execute("""
            INSERT INTO rooms (hostel_id, room_number)
            VALUES (?,?)
        """, (hostel_id, f"R{i}"))

    db.commit()
    db.close()

    return redirect("/warden")


@app.route("/warden/attendance", methods=["POST"])
def warden_attendance():
    if session.get("role") != "warden":
        return redirect("/")

    student_id = request.form["student_id"]
    date = request.form["date"]
    status = request.form["status"]

    db = get_db()
    db.execute("""
        INSERT INTO attendance (student_id, warden_id, date, status)
        VALUES (?,?,?,?)
    """, (student_id, session["uid"], date, status))

    db.commit()
    db.close()

    return redirect("/warden")


@app.route("/warden/photo", methods=["POST"])
def warden_photo():
    if session.get("role") != "warden":
        return redirect("/")

    file = request.files["photo"]
    hostel_id = request.form["hostel_id"]

    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    file.save(os.path.join(UPLOAD_FOLDER, filename))

    db = get_db()
    db.execute("""
        INSERT INTO room_photos (hostel_id, warden_id, filename)
        VALUES (?,?,?)
    """, (hostel_id, session["uid"], filename))

    db.commit()
    db.close()

    return redirect("/warden")

# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)