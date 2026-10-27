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
    cur.execute(
        """
        SELECT ROUND(AVG(skill_programming)::numeric, 2),
               ROUND(AVG(skill_data_stats)::numeric, 2),
               ROUND(AVG(skill_frontend_design)::numeric, 2),
               ROUND(AVG(skill_business_pitch)::numeric, 2)
        FROM intake_response
        """
    )
    skill_avgs = list(
        zip(
            ("Programming", "Data/Stats", "Frontend/Design", "Business/Pitch"),
            cur.fetchone(),
        )
    )
    cur.close()
    conn.close()
    return render_template("index.html", names=names, skill_avgs=skill_avgs)


if __name__ == "__main__":
    app.run(debug=True)
