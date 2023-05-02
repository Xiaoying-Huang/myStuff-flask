import sqlite3
from flask import Flask, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)

app = Flask(__name__)
app.secret_key = "BEST ORGANIZATION"


# Define the User class
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect("myStuff.db")
    c = conn.cursor()
    c.execute("SELECT * FROM user WHERE id=?", [user_id])
    user = c.fetchone()
    if user:
        return User(user[0], user[1])
    else:
        return None


def get_db_connection():
    conn = sqlite3.connect("myStuff.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        db = get_db_connection()
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", message=f"must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("error.html", message=f"must provide password")

        # Query database for username
        rows = db.execute(
            "SELECT * FROM user WHERE username = ?", [request.form.get("username")]
        ).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["password"], request.form.get("password")
        ):
            return render_template(
                "error.html", message=f"invalid username and/or password"
            )

        # Remember which user has logged in
        user_obj = User(rows[0]["id"], rows[0]["username"])
        login_user(user_obj)
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return render_template("dashboard.html", username=current_user.username)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        db = get_db_connection()
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        username_search = db.execute(
            "SELECT COUNT(*) FROM user WHERE username = ?", [username]
        ).fetchall()

        if username_search[0]["COUNT(*)"] > 0:
            return render_template(
                "error.html", message=f"Username {username} already exists"
            )
        elif not password:
            return render_template("error.html", message=f"Missing password")
        elif not confirm_password or password != confirm_password:
            return render_template("error.html", message=f"Passwords do not match")
        else:
            hashed = generate_password_hash(password)
            db.execute(
                "INSERT INTO user(username, password) VALUES (?, ?) ",
                (username, hashed),
            )
            db.commit()
            return render_template(
                "login.html",
                message=f"Successfully registered. Please log in with your username and password.",
            )

    else:
        return render_template("register.html")
