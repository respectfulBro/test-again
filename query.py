import os
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent


def load_env():
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v.strip().strip('"').strip("'"))


QUERIES = [
    "SELECT count(*) FROM students;",
    "SELECT name, school_year FROM students LIMIT 5;",
    """
    SELECT t.name, COUNT(*) AS n_students
    FROM student_tools st
    JOIN tools t ON st.tool_id = t.id
    GROUP BY t.name
    ORDER BY n_students DESC;
    """,
]


def main():
    load_env()
    conn = psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")
    cur = conn.cursor()
    cur.execute(
        """
        CREATE OR REPLACE VIEW students AS SELECT * FROM student;
        CREATE OR REPLACE VIEW tools AS SELECT * FROM tool;
        CREATE OR REPLACE VIEW student_tools AS
            SELECT ir.netid AS student_id, rt.tool_id
            FROM response_tool rt
            JOIN intake_response ir ON ir.id = rt.response_id;
        """
    )
    conn.commit()

    for sql in QUERIES:
        print(sql.strip())
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        print(cols)
        for row in cur.fetchall():
            print(row)
        print()

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
