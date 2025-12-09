# db.py
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load .env when this module is imported
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Make sure you have a .env file with DATABASE_URL=... in your project root."
    )

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# 1) Add user to wishlist for a SKU
def add_to_wishlist(user_id: str, display_name: str, sku: str, item_name: str) -> int:
    """
    Returns the user's position in the queue for that SKU (1-based).
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO wishlist_entries (sku, item_name, user_id, display_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (sku, user_id)
                DO NOTHING;
                """,
                (sku, item_name, user_id, display_name),
            )

            # Get the created_at timestamp for this user+sku
            cur.execute(
                """
                SELECT created_at FROM wishlist_entries
                WHERE sku = %s AND user_id = %s
                """,
                (sku, user_id),
            )
            row = cur.fetchone()
            if not row:
                # They were already in the list; fetch existing timestamp
                cur.execute(
                    """
                    SELECT created_at FROM wishlist_entries
                    WHERE sku = %s AND user_id = %s
                    """,
                    (sku, user_id),
                )
                row = cur.fetchone()

            created_at = row["created_at"]

            # Position = how many entries for this SKU with created_at <= this user's
            cur.execute(
                """
                SELECT COUNT(*) AS position
                FROM wishlist_entries
                WHERE sku = %s AND created_at <= %s
                """,
                (sku, created_at),
            )
            pos = cur.fetchone()["position"]
            return pos

# 2) Remove user from a SKU
def remove_from_wishlist(user_id: str, sku: str) -> str | None:
    """
    Remove a user from a wishlist for a given SKU.
    Returns the item_name if something was removed, otherwise None.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1) Look up the item_name first
            cur.execute(
                """
                SELECT item_name
                FROM wishlist_entries
                WHERE sku = %s AND user_id = %s
                """,
                (sku, user_id),
            )
            row = cur.fetchone()
            if not row:
                return None  # user wasn't on that SKU

            item_name = row["item_name"]

            # 2) Delete the entry
            cur.execute(
                "DELETE FROM wishlist_entries WHERE sku = %s AND user_id = %s",
                (sku, user_id),
            )

            # conn.commit() happens automatically because of the context manager
            return item_name


# 3) View all entries for a user (with positions)
def get_user_entries(user_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sku, item_name, created_at
                FROM wishlist_entries
                WHERE user_id = %s
                ORDER BY created_at
                """,
                (user_id,),
            )
            entries = cur.fetchall()

            result = []
            for e in entries:
                sku = e["sku"]
                created_at = e["created_at"]

                # Position
                cur.execute(
                    """
                    SELECT COUNT(*) AS position
                    FROM wishlist_entries
                    WHERE sku = %s AND created_at <= %s
                    """,
                    (sku, created_at),
                )
                pos = cur.fetchone()["position"]

                # Total for that SKU
                cur.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM wishlist_entries
                    WHERE sku = %s
                    """,
                    (sku,),
                )
                total = cur.fetchone()["total"]

                result.append({
                    "sku": sku,
                    "item_name": e["item_name"],
                    "position": pos,
                    "total": total,
                })
            return result

# 4) Count list size for a SKU
def count_for_sku(sku: str) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS c FROM wishlist_entries WHERE sku = %s",
                (sku,),
            )
            return cur.fetchone()["c"]

def admin_remove_by_name(name: str, sku: str) -> str | None:
    """
    Admin-only helper: remove one wishlist entry matching (display_name, sku).

    Returns:
        item_name (str) if an entry was found and deleted,
        None if no matching entry was found.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Find the earliest entry for this name + SKU
            cur.execute(
                """
                SELECT id, item_name
                FROM wishlist_entries
                WHERE sku = %s AND display_name = %s
                ORDER BY created_at
                LIMIT 1
                """,
                (sku, name),
            )
            row = cur.fetchone()
            if not row:
                return None

            entry_id = row["id"]
            item_name = row["item_name"]

            # Delete that specific entry
            cur.execute(
                "DELETE FROM wishlist_entries WHERE id = %s",
                (entry_id,),
            )

            return item_name
