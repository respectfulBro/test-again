import os

import psycopg2
from flask import Flask, render_template

from load_csv import load_env

load_env()
app = Flask(__name__)


@app.route("/")
def index():
    conn = psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")
    cur = conn.cursor()
    cur.execute("SELECT name FROM student ORDER BY name")
    names = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return render_template("index.html", names=names)


if __name__ == "__main__":
    app.run(debug=True)
