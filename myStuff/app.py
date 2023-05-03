import sqlite3
from flask import Flask, render_template, request, session, redirect
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
    db = get_db_connection()
    # Forget any user_id
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
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
    db = get_db_connection()
    if request.method == "POST":
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


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/storage_plan", methods=["GET", "POST"])
@login_required
def storage_plan():
    db = get_db_connection()
    if request.method == "POST":
        pass
    else:
        return render_template("storage_plan.html")


@app.route("/add_house", methods=["GET", "POST"])
@login_required
def add_house():
    db = get_db_connection()
    if request.method == "POST":
        if request.form.get("add_house") == "Add house":
            house_name = request.form.get("house_name")
            # Perform a house name search to ensure the input value is unique
            house_name_search = db.execute(
                "SELECT COUNT(*) FROM house WHERE house_name = ? AND user_id = ?",
                (house_name, current_user.id),
            ).fetchall()
            if house_name_search[0]["COUNT(*)"] > 0:
                message = f"House name {house_name} already exists! Please enter another house name."
            # If no duplication of house names under the same user, insert the new house name into database
            else:
                db.execute(
                    "INSERT INTO house(house_name, user_id) VALUES (?, ?)",
                    (house_name, current_user.id),
                )
                db.commit()
                message = "Successfully added a house!"
            return render_template(
                "add_house.html",
                message_house=message,
            )
    else:
        return render_template("add_house.html", message_hosue="")


# Adding a room
# Adding a piece of furniture
# Adding a container
# Displaying the storage plan


@app.route("/add_stock", methods=["GET", "POST"])
@login_required
def add_stock():
    db = get_db_connection()
    category = db.execute("SELECT category FROM category").fetchall()
    length = len(category)
    if request.method == "GET":
        return render_template("add_stock.html", category=category, length=length)
