import csv
import os
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "class_dataset.csv"
if not CSV_PATH.exists():
    CSV_PATH = ROOT / "class_dataset.csv"


def load_env():
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v.strip().strip('"').strip("'"))


def split_semi(value):
    if not value:
        return []
    out, seen = [], set()
    for part in value.split(";"):
        item = " ".join(part.split()).strip()
        if not item or item.lower() == "none yet":
            continue
        key = item.lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


DDL = """
DROP TABLE IF EXISTS response_tool, response_availability, intake_response, student, tool, availability_slot CASCADE;

CREATE TABLE student (
    netid VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    school_year VARCHAR NOT NULL,
    intro_programming VARCHAR NOT NULL
);

CREATE TABLE intake_response (
    id SERIAL PRIMARY KEY,
    netid VARCHAR NOT NULL REFERENCES student(netid),
    skill_programming SMALLINT NOT NULL CHECK (skill_programming BETWEEN 1 AND 5),
    skill_data_stats SMALLINT NOT NULL CHECK (skill_data_stats BETWEEN 1 AND 5),
    skill_frontend_design SMALLINT NOT NULL CHECK (skill_frontend_design BETWEEN 1 AND 5),
    skill_business_pitch SMALLINT NOT NULL CHECK (skill_business_pitch BETWEEN 1 AND 5),
    working_style TEXT NOT NULL,
    interests TEXT NOT NULL,
    semester_goal TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE tool (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE
);

CREATE TABLE response_tool (
    response_id INTEGER NOT NULL REFERENCES intake_response(id),
    tool_id INTEGER NOT NULL REFERENCES tool(id),
    PRIMARY KEY (response_id, tool_id)
);

CREATE TABLE availability_slot (
    id SERIAL PRIMARY KEY,
    label VARCHAR NOT NULL UNIQUE
);

CREATE TABLE response_availability (
    response_id INTEGER NOT NULL REFERENCES intake_response(id),
    slot_id INTEGER NOT NULL REFERENCES availability_slot(id),
    PRIMARY KEY (response_id, slot_id)
);
"""


def upsert_lookup(cur, table, col, value):
    cur.execute(
        f"INSERT INTO {table} ({col}) VALUES (%s) ON CONFLICT ({col}) DO UPDATE SET {col}=EXCLUDED.{col} RETURNING id",
        (value,),
    )
    return cur.fetchone()[0]


def main():
    load_env()
    url = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(url, sslmode="require")
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute(DDL)

    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cur.execute(
                """
                INSERT INTO student (netid, name, school_year, intro_programming)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (netid) DO UPDATE SET
                    name = EXCLUDED.name,
                    school_year = EXCLUDED.school_year,
                    intro_programming = EXCLUDED.intro_programming
                """,
                (row["netid"], row["name"], row["school_year"], row["intro_programming"]),
            )
            cur.execute(
                """
                INSERT INTO intake_response (
                    netid, skill_programming, skill_data_stats,
                    skill_frontend_design, skill_business_pitch,
                    working_style, interests, semester_goal, submitted_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    row["netid"],
                    int(row["skill_programming"]),
                    int(row["skill_data_stats"]),
                    int(row["skill_frontend_design"]),
                    int(row["skill_business_pitch"]),
                    row["working_style"],
                    row["interests"],
                    row["semester_goal"],
                    row["submitted_at"],
                ),
            )
            response_id = cur.fetchone()[0]
            for name in split_semi(row["tools"]):
                tool_id = upsert_lookup(cur, "tool", "name", name)
                cur.execute(
                    "INSERT INTO response_tool (response_id, tool_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (response_id, tool_id),
                )
            for label in split_semi(row["availability"]):
                slot_id = upsert_lookup(cur, "availability_slot", "label", label)
                cur.execute(
                    "INSERT INTO response_availability (response_id, slot_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (response_id, slot_id),
                )

    conn.commit()
    for table in (
        "student",
        "intake_response",
        "tool",
        "response_tool",
        "availability_slot",
        "response_availability",
    ):
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"{table}: {cur.fetchone()[0]}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
