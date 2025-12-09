from dotenv import load_dotenv
import os
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print("DATABASE_URL =", DATABASE_URL)

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()
cur.execute("SELECT current_database() AS db, current_schema() AS schema;")
row = cur.fetchone()
print("Connected! db:", row["db"], "schema:", row["schema"])

cur.close()
conn.close()