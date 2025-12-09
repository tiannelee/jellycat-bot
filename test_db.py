# test_db.py
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()  # read .env

DATABASE_URL = os.environ["DATABASE_URL"]

def main():
    print("DATABASE_URL:", DATABASE_URL)
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    cur.execute("SELECT NOW() AS server_time;")
    row = cur.fetchone()
    print("Connected! Supabase time:", row["server_time"])

    # Optional: check your wishlist_entries table
    cur.execute("SELECT COUNT(*) AS c FROM wishlist_entries;")
    row = cur.fetchone()
    print("wishlist_entries rows:", row["c"])

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
