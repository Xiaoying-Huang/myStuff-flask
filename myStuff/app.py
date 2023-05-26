import sqlite3

import urllib.parse

from flask import Flask, render_template, request, session, redirect, url_for
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


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=current_user.username)


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
        return redirect(url_for("dashboard"))

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
            # Insert new user
            db.execute(
                "INSERT INTO user(username, password) VALUES (?, ?) ",
                (username, hashed),
            )
            db.commit()
            # Insert the 'Unassigned' container
            user_id = db.execute(
                "SELECT id FROM user WHERE username = ?", [username]
            ).fetchall()[0]["id"]
            db.execute(
                "INSERT INTO house (house_name, user_id) VALUES (?, ?)",
                ("Unassigned", user_id),
            )
            db.commit()
            house_id = db.execute(
                "SELECT house_id FROM house WHERE house_name = 'Unassigned' AND user_id=?",
                [user_id],
            ).fetchall()[0]["house_id"]
            db.execute(
                "INSERT INTO room (room_name, house_id) VALUES (?, ?)",
                ("Unassigned", house_id),
            )
            db.commit()
            room_id = db.execute(
                "SELECT room_id FROM room WHERE room_name = 'Unassigned' AND house_id =?",
                [house_id],
            ).fetchall()[0]["room_id"]
            db.execute(
                "INSERT INTO furniture (furniture_name, room_id) VALUES (?, ?)",
                ("Unassigned", room_id),
            )
            db.commit()
            furniture_id = db.execute(
                "SELECT furniture_id FROM furniture WHERE furniture_name = 'Unassigned' AND room_id = ?",
                [room_id],
            ).fetchall()[0]["furniture_id"]
            db.execute(
                "INSERT INTO container (container_name, furniture_id, is_unassigned) VALUES (?, ?, 1)",
                ("Unassigned", furniture_id),
            )
            db.commit()
            return redirect(url_for("login"))

    else:
        return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/storage_plan")
@login_required
def storage_plan():
    # First, obtain a list of all the houses, rooms, furniture and containers.
    db = get_db_connection()
    rows = db.execute(
        "SELECT house.house_id, house.house_name, room.room_id, room.room_name, furniture.furniture_id, furniture.furniture_name, container.container_id, container.container_name FROM house LEFT JOIN room ON house.house_id = room.house_id LEFT JOIN furniture ON room.room_id = furniture.room_id LEFT JOIN container ON furniture.furniture_id = container.furniture_id WHERE container.is_unassigned != 1 AND house.user_id=?",
        [current_user.id],
    ).fetchall()

    containers_dict = {}
    for row in rows:
        (
            house_id,
            house_name,
            room_id,
            room_name,
            furniture_id,
            furniture_name,
            container_id,
            container_name,
        ) = row

        # create container dictionary
        if house_name not in containers_dict:
            containers_dict[house_name] = {"house_id": house_id, "rooms": {}}

        if room_name == None:
            continue
        elif room_name not in containers_dict[house_name]["rooms"]:
            containers_dict[house_name]["rooms"][room_name] = {
                "room_id": room_id,
                "furniture": {},
            }

        if furniture_name == None:
            continue
        elif (
            furniture_name
            not in containers_dict[house_name]["rooms"][room_name]["furniture"]
        ):
            containers_dict[house_name]["rooms"][room_name]["furniture"][
                furniture_name
            ] = {"furniture_id": furniture_id, "containers": {}}

        if container_name == None:
            continue
        elif (
            container_name
            not in containers_dict[house_name]["rooms"][room_name]["furniture"][
                furniture_name
            ]["containers"]
        ):
            containers_dict[house_name]["rooms"][room_name]["furniture"][
                furniture_name
            ]["containers"][container_name] = container_id
    # print(containers_dict)

    return render_template("storage_plan.html", menu=containers_dict)


@app.route("/add_house", methods=["GET", "POST"])
@login_required
def add_house():
    db = get_db_connection()
    if request.method == "POST":
        if request.form.get("add_house") == "Add house":
            house_name = request.form.get("house_name")

            # Ensure house name was submitted
            if not request.form.get("house_name"):
                return render_template(
                    "add_house.html", message_house="House name should not be empty!"
                )

            # Ensure house name is not 'Unassigned'
            if request.form.get("house_name").lower() == "unassigned":
                return render_template(
                    "add_house.html",
                    message_house="Please do not use 'unassigned' as the house name.",
                )

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
        "SELECT house_name, house_id FROM house WHERE user_id=? AND house_name != 'Unassigned'",
        [current_user.id],
    ).fetchall()
    house_len = len(houses)
    if request.method == "POST":
        room_name = request.form.get("room_name")
        selected_house = db.execute(
            "SELECT house_name FROM house WHERE house_id = ?",
            [request.form.get("house_select")],
        ).fetchall()[0]["house_name"]
        # Ensure room name was submitted
        if not request.form.get("room_name"):
            return render_template(
                "add_room.html",
                message_room="Room name should not be empty!",
                house_len=house_len,
                houses=houses,
            )

        # Ensure room name is not 'Unassigned'
        if request.form.get("room_name").lower() == "unassigned":
            return render_template(
                "add_house.html",
                message_house="Please do not use 'unassigned' as the house name.",
            )

        # Perform name research of the room. If there is another room within the same house under the same user id, the room cannot be added and an error message should be shown to the user.
        room_name_search = db.execute(
            "SELECT COUNT(*) FROM room WHERE room_name=? AND house_id=?",
            (room_name, request.form.get("house_select")),
        ).fetchall()
        if room_name_search[0]["COUNT(*)"] > 0:
            message = f'Room name "{room_name}" already exists in {selected_house}! Please enter another room name.'

        # If name check passes, the new room can be added.
        else:
            db.execute(
                "INSERT INTO room(room_name, house_id) VALUES (?, ?)",
                (room_name, request.form.get("house_select")),
            )
            db.commit()
            message = f'Successfully added "{room_name}" in "{selected_house}"!'
        return render_template(
            "add_room.html",
            house_len=house_len,
            houses=houses,
            message_room=message,
        )
    else:
        return render_template(
            "add_room.html",
            house_len=house_len,
            houses=houses,
            message_room="",
        )


# Adding a piece of furniture
@app.route("/add_furniture", methods=["GET", "POST"])
@login_required
def add_furniture():
    # First, obtain a list of all the houses and rooms available to display in the chained dropdown list.
    db = get_db_connection()

    rooms_dict = {}
    rows = db.execute(
        "SELECT house.house_id, house.house_name, room.room_id, room.room_name FROM house JOIN room ON house.house_id = room.house_id WHERE house.house_name != 'Unassigned' AND room.room_name != 'Unassigned' AND house.user_id=?",
        [current_user.id],
    ).fetchall()

    for row in rows:
        house_id, house_name, room_id, room_name = row

        # Create rooms dictionary
        if house_name not in rooms_dict:
            rooms_dict[house_name] = {"house_id": house_id, "rooms": {}}
        if room_id not in rooms_dict[house_name]["rooms"]:
            rooms_dict[house_name]["rooms"][room_id] = room_name

    # rooms_dict is to be passed to html

    if request.method == "POST":
        # Ensure furniture name was submitted:
        if not request.form.get("furniture"):
            return render_template(
                "add_furniture.html",
                message="Furniture name should not be empty!",
                menu=rooms_dict,
            )

        # Ensure furniture name is not 'unassigned'
        if request.form.get("furniture").lower() == "unassigned":
            return render_template(
                "add_furniture.html",
                message="Please do not use 'unassigned' as the furniture name.",
                menu=rooms_dict,
            )

        # Perform name research of the new furniture. If there is another piece of furniture within the same room of the same house under the same user id, the furniture cannot be added and an error message should be shown to the user.
        furniture_name = request.form.get("furniture")
        furniture_name_search = db.execute(
            "SELECT COUNT(*) FROM furniture WHERE furniture_name=? AND room_id=?",
            (furniture_name, request.form.get("room")),
        ).fetchall()

        selected_house = request.form.get("house")
        selected_room = rooms_dict[request.form.get("house")]["rooms"][
            int(request.form.get("room"))
        ]

        if furniture_name_search[0]["COUNT(*)"] > 0:
            message = f'Furniture name "{furniture_name}" already exists in "{selected_room}" of "{selected_house}"! Please enter another furniture name.'
        # if no duplication of names are found, a new entry of furniture will be inserted to the furniture table of myStuff.db.
        else:
            db.execute(
                "INSERT INTO furniture(furniture_name, room_id) VALUES (?, ?)",
                (
                    furniture_name,
                    request.form.get("room"),
                ),
            )
            db.commit()
            message = f'You have successfully added "{furniture_name}" in the "{selected_room}" of "{selected_house}"'
        return render_template("add_furniture.html", menu=rooms_dict, message=message)

    else:
        return render_template("add_furniture.html", menu=rooms_dict, message="")


# Adding a container
@app.route("/add_container", methods=["GET", "POST"])
@login_required
def add_container():
    # First, obtain a list of all the houses and rooms available to display in the chained dropdown list.
    db = get_db_connection()

    furniture_dict = {}

    rows = db.execute(
        "SELECT house.house_id, house.house_name, room.room_id, room.room_name, furniture.furniture_id, furniture.furniture_name FROM house JOIN room ON house.house_id = room.house_id JOIN furniture ON room.room_id = furniture.room_id WHERE house.house_name != 'Unassigned' AND room.room_name!='Unassigned' AND furniture.furniture_name !='Unassigned' AND house.user_id=?",
        [current_user.id],
    ).fetchall()

    for row in rows:
        house_id, house_name, room_id, room_name, furniture_id, furniture_name = row

        # Create furniture dictionary
        if house_name not in furniture_dict:
            furniture_dict[house_name] = {"house_id": house_id, "rooms": {}}
        if room_name not in furniture_dict[house_name]["rooms"]:
            furniture_dict[house_name]["rooms"][room_name] = {
                "room_id": room_id,
                "furniture": {},
            }
        if (
            furniture_id
            not in furniture_dict[house_name]["rooms"][room_name]["furniture"]
        ):
            furniture_dict[house_name]["rooms"][room_name]["furniture"][
                furniture_id
            ] = furniture_name

    # furniture_dict to be passed to html

    if request.method == "POST":
        # Ensure container name was submitted:
        if not request.form.get("container"):
            return render_template(
                "add_container.html",
                message="Container name should not be empty!",
                menu=furniture_dict,
            )

        # Ensure container name is not 'unassigned':
        if request.form.get("container").lower() == "unassigned":
            return render_template(
                "add_container.html",
                message="Container should not be named as 'unassigned'. Please choose another name.",
                menu=furniture_dict,
            )

        # Perform name research of the new container. If there is another container within the same furniture, same room of the same house under the same user id, the furniture cannot be added and an error message should be shown to the user.
        container_name = request.form.get("container")
        container_name_search = db.execute(
            "SELECT COUNT(*) FROM container WHERE container_name=? AND furniture_id=?",
            (container_name, request.form.get("furniture")),
        ).fetchall()

        selected_furniture = furniture_dict[request.form.get("house")]["rooms"][
            request.form.get("room")
        ]["furniture"][int(request.form.get("furniture"))]

        if container_name_search[0]["COUNT(*)"] > 0:
            message = f'Container name "{container_name}" already exists in "{selected_furniture}, in the room "{request.form.get("room")}" of house "{request.form.get("house")}"! Please enter another container name.'
        # if no duplication of names are found, a new entry of furniture will be inserted to the furniture table of myStuff.db.
        else:
            db.execute(
                "INSERT INTO container(container_name, furniture_id) VALUES (?,?)",
                (container_name, request.form.get("furniture")),
            )
            db.commit()
            message = f'You have successfully added "{container_name}" to the furniture "{selected_furniture}", in the room "{request.form.get("room")}" of house "{request.form.get("house")}".'
        return render_template(
            "add_container.html", menu=furniture_dict, message=message
        )

    else:
        return render_template("add_container.html", menu=furniture_dict, message="")


@app.route("/add_stock/new", methods=["GET", "POST"])
@login_required
def add_stock():
    db = get_db_connection()
    categories = db.execute(
        "SELECT category, category_id FROM category WHERE user_id =?", [current_user.id]
    ).fetchall()

    categories_dict = {}
    for row in categories:
        category, category_id = row
        if category_id not in categories_dict:
            categories_dict[category_id] = category

    containers_dict = {}
    rows = db.execute(
        "SELECT container_id, container_name, furniture_name, room_name, house_name FROM container JOIN furniture ON container.furniture_id=furniture.furniture_id JOIN room ON furniture.room_id=room.room_id JOIN house ON room.house_id=house.house_id WHERE house.user_id=? ORDER BY house.house_id, room.room_id, furniture.furniture_id, container.container_id",
        [current_user.id],
    ).fetchall()

    for row in rows:
        container_id, container_name, furniture_name, room_name, house_name = row
        # create containers_dict
        if house_name not in containers_dict:
            containers_dict[house_name] = {}
        if room_name not in containers_dict[house_name]:
            containers_dict[house_name][room_name] = {}
        if furniture_name not in containers_dict[house_name][room_name]:
            containers_dict[house_name][room_name][furniture_name] = {}
        if container_id not in containers_dict[house_name][room_name][furniture_name]:
            containers_dict[house_name][room_name][furniture_name][
                container_id
            ] = container_name

    if request.method == "POST":
        # add category
        if "cat_submit" in request.form:
            # name check
            cat_name_search = db.execute(
                "SELECT COUNT(*) FROM category WHERE category = ? AND user_id=?",
                (request.form.get("category_name"), current_user.id),
            ).fetchall()
            if cat_name_search[0]["COUNT(*)"] > 0:
                return render_template(
                    "add_stock.html",
                    category=category,
                    message=f'Category "{request.form.get("category_name")}" already exists. Please enter another category.',
                    menu=containers_dict,
                )

            else:
                db.execute(
                    "INSERT INTO category (category, description, user_id) VALUES (?, ?, ?)",
                    (
                        request.form.get("category_name"),
                        request.form.get("description"),
                        current_user.id,
                    ),
                )
                db.commit()
                new_categoryid = db.execute(
                    "SELECT category_id FROM category WHERE user_id =? AND category = ?",
                    (current_user.id, request.form.get("category_name")),
                ).fetchall()[0]["category_id"]

                categories_dict[new_categoryid] = request.form.get("category_name")

                return render_template(
                    "add_stock.html",
                    categories_dict=categories_dict,
                    message=f'Successfully added a new stock category "{request.form.get("category_name")}"',
                    menu=containers_dict,
                )

        # add new stock items
        if "stock_submit" in request.form:
            # Duplicate name check
            stock_name_search = db.execute(
                "SELECT COUNT(*) FROM stock WHERE stock_name = ? and user_id=?",
                (request.form.get("stock_name"), current_user.id),
            ).fetchall()

            if stock_name_search[0]["COUNT(*)"] > 0:
                return render_template(
                    "add_stock.html",
                    categories_dict=categories_dict,
                    message=f'Stock item named "{request.form.get("stock_name")}" already exists. Please choose another name or simply update the quantity of existing item.',
                    menu=containers_dict,
                )
            else:
                db.execute(
                    "INSERT INTO stock(stock_name, category_id, note, user_id) VALUES(?,?,?,?)",
                    (
                        request.form.get("stock_name"),
                        request.form.get("category"),
                        request.form.get("note"),
                        current_user.id,
                    ),
                )
                db.commit()
                stock_id = db.execute(
                    "SELECT stock_id from stock WHERE stock_name = ? AND user_id =?",
                    (request.form.get("stock_name"), current_user.id),
                ).fetchall()[0]["stock_id"]
                print(stock_id)
                db.execute(
                    "INSERT INTO stock_container(stock_id, container_id, quantity) VALUES(?, ?, ?)",
                    (
                        stock_id,
                        request.form.get("container"),
                        request.form.get("quantity"),
                    ),
                )
                db.commit()

            return render_template(
                "add_stock.html",
                categories_dict=categories_dict,
                message=f'Successfully added a new stock item "{request.form.get("stock_name")}"',
                menu=containers_dict,
            )

    else:
        return render_template(
            "add_stock.html",
            categories_dict=categories_dict,
            message="",
            menu=containers_dict,
        )


@app.route("/assign_stock", methods=["GET", "POST"])
@login_required
def assign_stock():
    db = get_db_connection()

    containers_dict = {}
    rows = db.execute(
        "SELECT container_id, container_name, furniture_name, room_name, house_name FROM container JOIN furniture ON container.furniture_id=furniture.furniture_id JOIN room ON furniture.room_id=room.room_id JOIN house ON room.house_id=house.house_id ORDER BY house.house_id, room.room_id, furniture.furniture_id, container.container_id"
    ).fetchall()

    for row in rows:
        container_id, container_name, furniture_name, room_name, house_name = row
        # create containers_dict
        if house_name not in containers_dict:
            containers_dict[house_name] = {}
        if room_name not in containers_dict[house_name]:
            containers_dict[house_name][room_name] = {}
        if furniture_name not in containers_dict[house_name][room_name]:
            containers_dict[house_name][room_name][furniture_name] = {}
        if container_id not in containers_dict[house_name][room_name][furniture_name]:
            containers_dict[house_name][room_name][furniture_name][
                container_id
            ] = container_name

    # print(containers_dict)

    # stock items
    stocks = db.execute(
        "SELECT stock_id, stock_name, category, note FROM stock JOIN category ON stock.category_id=category.category_id AND stock.user_id = ?",
        [current_user.id],
    ).fetchall()

    # create stocks_dict
    stocks_dict = {}
    for stock in stocks:
        stock_id, stock_name, category, note = stock

        if stock_id not in stocks_dict:
            stocks_dict[stock_id] = {
                "stock_name": stock_name,
                "category": category,
                "note": note,
            }
    # print(stocks_dict)

    if request.method == "POST":
        if request.form.get("stock_assign") == "multi_stock_items":
            selected_container = request.form.get("container")
            print("selected_container", selected_container)
            selected_stocks = request.form.getlist("stock_item")
            print("selected stocks", selected_stocks)
            message = ""
            for selected_stock in selected_stocks:
                db.execute(
                    "INSERT INTO stock_container(stock_id, container_id, quantity) VALUES (?, ?,?)",
                    (
                        selected_stock,
                        selected_container,
                        request.form.get(f"quantity_{selected_stock}"),
                    ),
                )
                selected_stock = int(selected_stock)
                db.commit()
                print("quantity", request.form.get(f"quantity_{selected_stock}"))
                message += f"""Successfully assigned "{stocks_dict[selected_stock]["stock_name"]}" to {containers_dict[request.form.get("house")][request.form.get("room")][request.form.get("furniture")][int(selected_container)]} in the quantity of {request.form.get(f"quantity_{selected_stock}")}! """

            return render_template(
                "assign_stock.html",
                containers_dict=containers_dict,
                stocks_dict=stocks_dict,
                message=message,
            )
    else:
        return render_template(
            "assign_stock.html",
            containers_dict=containers_dict,
            stocks_dict=stocks_dict,
            message="",
        )


@app.route("/view_stock", methods=["GET", "POST"])
@login_required
def view_stock():
    db = get_db_connection()
    stocks = db.execute(
        "SELECT stock_container.stock_container_id, stock.stock_id,stock.stock_name,container.container_id, container.container_name, stock_container.quantity, furniture.furniture_name, room.room_name, house.house_name FROM stock_container LEFT JOIN stock ON stock.stock_id=stock_container.stock_id LEFT JOIN container ON container.container_id=stock_container.container_id LEFT JOIN furniture on furniture.furniture_id=container.furniture_id LEFT JOIN room on room.room_id=furniture.room_id LEFT JOIN house on house.house_id=room.house_id WHERE stock.user_id=?",
        [current_user.id],
    )
    stocks_dict = {}
    for stock in stocks:
        (
            stock_container_id,
            stock_id,
            stock_name,
            container_id,
            container_name,
            quantity,
            furniture_name,
            room_name,
            house_name,
        ) = stock
        if stock_container_id not in stocks_dict:
            stocks_dict[stock_container_id] = {
                "stock_id": stock_id,
                "stock_name": stock_name,
                "container_id": container_id,
                "container_name": container_name,
                "quantity": quantity,
                "furniture_name": furniture_name,
                "room_name": room_name,
                "house_name": house_name,
            }
    # print(stocks_dict)

    if request.method == "POST":
        pass
    else:
        return render_template("view_stock.html", stocks=stocks_dict)


@app.route("/stock_info/<int:stock_id>")
@login_required
def stock_info(stock_id):
    db = get_db_connection()
    """ stock_info=db.execute("SELECT") """


@app.route("/test", methods=["GET", "POST"])
@login_required
def test():
    db = get_db_connection()
    # stock items
    stocks = db.execute(
        "SELECT stock_id, stock_name, category, note FROM stock JOIN category ON stock.category_id=category.category_id AND stock.user_id = ?",
        [current_user.id],
    ).fetchall()

    # create stocks_dict
    stocks_dict = {}
    for stock in stocks:
        stock_id, stock_name, category, note = stock

        if stock_id not in stocks_dict:
            stocks_dict[stock_id] = {
                "stock_name": stock_name,
                "category": category,
                "note": note,
            }
    # print(stocks_dict)

    containers_dict = {}
    rows = db.execute(
        "SELECT container_id, container_name, furniture_name, room_name, house_name FROM container JOIN furniture ON container.furniture_id=furniture.furniture_id JOIN room ON furniture.room_id=room.room_id JOIN house ON room.house_id=house.house_id WHERE house.user_id=?",
        [current_user.id],
    ).fetchall()

    for row in rows:
        container_id, container_name, furniture_name, room_name, house_name = row
        # create containers_dict
        if house_name not in containers_dict:
            containers_dict[house_name] = {}
        if room_name not in containers_dict[house_name]:
            containers_dict[house_name][room_name] = {}
        if furniture_name not in containers_dict[house_name][room_name]:
            containers_dict[house_name][room_name][furniture_name] = {}
        if container_id not in containers_dict[house_name][room_name][furniture_name]:
            containers_dict[house_name][room_name][furniture_name][
                container_id
            ] = container_name
    if request.method == "POST":
        pass
    else:
        return render_template(
            "test.html", stocks=stocks_dict, containers=containers_dict
        )
