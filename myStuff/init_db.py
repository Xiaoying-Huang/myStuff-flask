import sqlite3

connection = sqlite3.connect("myStuff.db")


with open("schema.sql") as f:
    connection.executescript(f.read())

cur = connection.cursor()

cur.execute(
    "INSERT INTO user (id, username, password) VALUES (?, ?, ?)",
    ("10000", "best", "haha123"),
)

connection.commit()
connection.close()
