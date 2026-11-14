
import sqlite3

REVIEW_ID = "98542685-f9b5-48d4-8b08-917e034c87d1"

REGISTRY_DB = "data/review_registry.sqlite"
CHECKPOINT_DB = "data/review_checkpoints.sqlite"


def delete_review():

    if REVIEW_ID == "PASTE_FAILED_REVIEW_ID_HERE":
        print("Please provide the review ID.")
        return

    # Remove review metadata
    with sqlite3.connect(REGISTRY_DB) as conn:
        cursor = conn.execute(
            "DELETE FROM reviews WHERE review_id = ?",
            (REVIEW_ID,)
        )
        print(f"Registry entries deleted: {cursor.rowcount}")

    # Remove all LangGraph checkpoint records for this review
    with sqlite3.connect(CHECKPOINT_DB) as conn:

        tables = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
        """).fetchall()

        total_deleted = 0

        for (table,) in tables:

            columns = conn.execute(
                f'PRAGMA table_info("{table}")'
            ).fetchall()

            column_names = [column[1] for column in columns]

            if "thread_id" in column_names:
                cursor = conn.execute(
                    f'DELETE FROM "{table}" WHERE thread_id = ?',
                    (REVIEW_ID,)
                )

                if cursor.rowcount:
                    print(f"{table}: {cursor.rowcount} records deleted")

                total_deleted += cursor.rowcount

    print(f"\nTotal checkpoint records deleted: {total_deleted}")
    print("Review deletion completed.")


if __name__ == "__main__":
    delete_review()
