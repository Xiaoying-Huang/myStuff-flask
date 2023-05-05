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
                message = f"House name '{house_name}' already exists! Please enter another house name."
            # If no duplication of house names under the same user, insert the new house name into database
            else:
                db.execute(
                    "INSERT INTO house(house_name, user_id) VALUES (?, ?)",
                    (house_name, current_user.id),
                )
                db.commit()
                message = f"Successfully added {house_name} as a new house!"
            return render_template(
                "add_house.html",
                message_house=message,
            )
    else:
        return render_template("add_house.html", message_hosue="")


# Adding a room
@app.route("/add_room", methods=["GET", "POST"])
@login_required
def add_room():
    db = get_db_connection()
    houses = db.execute(
        "SELECT house_name FROM house WHERE user_id=?", [current_user.id]
    ).fetchall()
    house_len = len(houses)
    if request.method == "POST":
        # Perform name research of the room. If there is another room within the same house under the same user id, the room cannot be added and an error message should be shown to the user.
        room_name = request.form.get("room_name")
        room_name_search = db.execute(
            "SELECT COUNT(*) FROM room WHERE room_name=? AND house=? AND user_id=?",
            (room_name, request.form.get("house_select"), current_user.id),
        ).fetchall()
        if room_name_search[0]["COUNT(*)"] > 0:
            message = f'Room name "{room_name}" already exists in {request.form.get("house_select")}! Please enter another room name.'
        # If name check passes, the new room can be added.
        else:
            db.execute(
                "INSERT INTO room(room_name, user_id, house) VALUES (?, ?, ?)",
                (room_name, current_user.id, request.form.get("house_select")),
            )
            db.commit()
            message = f'Successfully added "{room_name}" in "{request.form.get("house_select")}"!'
        return render_template(
            "add_room.html",
            house_len=house_len,
            houses=houses,
            message_room=message,
            instruction="Please select a house in which you're going to add a new room.",
        )
    else:
        return render_template(
            "add_room.html",
            house_len=house_len,
            houses=houses,
            message_room="",
            instruction="Please select a house in which you're going to add a new room.",
        )


# Adding a piece of furniture
@app.route("/add_furniture", methods=["GET", "POST"])
@login_required
def add_furniture():
    # First, obtain a list of all the houses and rooms available to display in the chained dropdown list.
    db = get_db_connection()

    house_names = db.execute(
        "SELECT house_name from house WHERE user_id = ?", [current_user.id]
    ).fetchall()

    house_names_list = []
    for i in range(len(house_names)):
        house_names_list.append(house_names[i]["house_name"])

    room_names_list = {}
    for house in house_names_list:
        room_list = []
        room_names = db.execute(
            "SELECT house, room_name FROM room WHERE user_id = ? AND house = ?",
            (current_user.id, house),
        ).fetchall()
        for i in range(len(room_names)):
            room_list.append(room_names[i]["room_name"])
        room_names_list[house] = room_list
    # room_names_list is to be passed to html

    if request.method == "POST":
        # Perform name research of the new furniture. If there is another piece of furniture within the same room of the same house under the same user id, the furniture cannot be added and an error message should be shown to the user.
        furniture_name = request.form.get("furniture")
        furniture_name_search = db.execute(
            "SELECT COUNT(*) FROM furniture WHERE furniture_name=? AND house=? AND room=? AND user_id=?",
            (
                furniture_name,
                request.form.get("house"),
                request.form.get("room"),
                current_user.id,
            ),
        ).fetchall()
        if furniture_name_search[0]["COUNT(*)"] > 0:
            message = f'Furniture name "{furniture_name}" already exists in "{request.form.get("room")}" of "{request.form.get("house")}"! Please enter another furniture name.'
        # if no duplication of names are found, a new entry of furniture will be inserted to the furniture table of myStuff.db.
        else:
            db.execute(
                "INSERT INTO furniture(furniture_name, user_id, house, room) VALUES (?, ?, ?,?)",
                (
                    furniture_name,
                    current_user.id,
                    request.form.get("house"),
                    request.form.get("room"),
                ),
            )
            db.commit()
            message = f'You have successfully added "{furniture_name}" in the "{request.form.get("room")}" of "{request.form.get("house")}"'
        return render_template(
            "add_furniture.html", menu=room_names_list, message=message
        )

    else:
        return render_template("add_furniture.html", menu=room_names_list, message="")


# Adding a container
@app.route("/add_container", methods=["GET", "POST"])
@login_required
def add_container():
    # First, obtain a list of all the houses and rooms available to display in the chained dropdown list.
    db = get_db_connection()

    house_names = db.execute(
        "SELECT house_name from house WHERE user_id = ?", [current_user.id]
    ).fetchall()

    house_names_list = []
    for i in range(len(house_names)):
        house_names_list.append(house_names[i]["house_name"])

    room_names_list = {}
    for house in house_names_list:
        room_list = []
        room_names = db.execute(
            "SELECT house, room_name FROM room WHERE user_id = ? AND house = ?",
            (current_user.id, house),
        ).fetchall()
        for i in range(len(room_names)):
            room_list.append(room_names[i]["room_name"])
        room_names_list[house] = room_list

    furniture_names_list = {}
    for key in room_names_list.keys():
        furniture_names_list[key] = {}
        for i in range(len(room_names_list[key])):
            furniture_names_list[key][room_names_list[key][i]] = {}
            furniture_list = []
            furniture_names = db.execute(
                "SELECT house, room, furniture_name FROM furniture WHERE user_id =? AND house = ? AND room =?",
                (current_user.id, key, room_names_list[key][i]),
            ).fetchall()
            for j in range(len(furniture_names)):
                furniture_list.append(furniture_names[j]["furniture_name"])
            furniture_names_list[key][room_names_list[key][i]] = furniture_list

    if request.method == "POST":
        # Perform name research of the new container. If there is another container within the same furniture, same room of the same house under the same user id, the furniture cannot be added and an error message should be shown to the user.
        container_name = request.form.get("container")
        container_name_search = db.execute(
            "SELECT COUNT(*) FROM container WHERE container_name=? AND furniture=? AND house=? AND room=? AND user_id=?",
            (
                container_name,
                request.form.get("furniture"),
                request.form.get("house"),
                request.form.get("room"),
                current_user.id,
            ),
        ).fetchall()
        if container_name_search[0]["COUNT(*)"] > 0:
            message = f'Container name "{container_name}" already exists in "{request.form.get("furniture")}, in the room "{request.form.get("room")}" of house "{request.form.get("house")}"! Please enter another container name.'
        # if no duplication of names are found, a new entry of furniture will be inserted to the furniture table of myStuff.db.
        else:
            db.execute(
                "INSERT INTO container(container_name, user_id, house, room, furniture) VALUES (?,?,?,?,?)",
                (
                    container_name,
                    current_user.id,
                    request.form.get("house"),
                    request.form.get("room"),
                    request.form.get("furniture"),
                ),
            )
            db.commit()
            message = f'You have successfully added "{container_name}" to the furniture "{request.form.get("furniture")}", in the room "{request.form.get("room")}" of house "{request.form.get("house")}".'
        return render_template(
            "add_container.html", menu=furniture_names_list, message=message
        )

        pass
    else:
        return render_template(
            "add_container.html", menu=furniture_names_list, message=""
        )


# Displaying the storage plan


@app.route("/add_stock", methods=["GET", "POST"])
@login_required
def add_stock():
    db = get_db_connection()
    category = db.execute("SELECT category FROM category").fetchall()
    length = len(category)
    if request.method == "GET":
        return render_template("add_stock.html", category=category, length=length)
