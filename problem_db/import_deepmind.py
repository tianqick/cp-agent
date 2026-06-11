"""
Import Codeforces problems from deepmind/code_contests (HuggingFace parquet).
Downloads parquet files directly and extracts CF problems.
"""
import io
import sqlite3
import sys
import urllib.request
from pathlib import Path

PARQUET_FILES = [
    f"data/train-{i:05d}-of-00039-{h}.parquet"
    for i, h in enumerate([
        "e991a271dbfa9925", "e092fe56fda18715", "9cea23812e920e41",
        "e3822fccad6e083a", "cefe355b4667b27e", "b7580d2d846c2136",
        "65184bb9f7d61fde", "05785de21e8b8429", "7246e6b7423b404f",
        "b8c920f6629b57b2", "6de28ba20654f69b", "5de236be5188959d",
        "da9476a39a1bdbb7", "30b8c3829ee3b962", "dc3ebb07a3cba8e4",
        "19ccd7331d695677", "bf38b0908b322307", "ae5533a2f822e6ef",
        "8c793837880f5507", "d688fad5ee604390", "5d59387098675b73",
        "b257bf03d6876780", "1cfd39fa43c1917c", "d078bcb55e45cbf0",
        "f4e3da0e5661e6d1", "3f6ebfbaba5f4c70", "7d4898300894cbbe",
        "f8196766547533a2", "79a302af3c924863", "2b6615897d038115",
        "4135cc54050afc22", "40309dd907c042b7", "7b7d2068a3d9c359",
        "53b0f749aacff9c1", "a36ff0bff7d2a76f", "d28f9be60314601f",
        "146e1a11c054aeab", "995207c374a4e6f2", "96a59dd6a98cd075",
    ])
]


def import_deepmind_cf(db_path: Path, max_files: int = 0):
    """Import CF problems from HuggingFace parquet files."""
    import pyarrow.parquet as pq

    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            difficulty TEXT,
            tags TEXT,
            url TEXT,
            UNIQUE(source, source_id)
        )
    """)

    files_to_download = PARQUET_FILES[:max_files] if max_files > 0 else PARQUET_FILES
    total_imported = 0
    total_skipped = 0

    for file_idx, file_path in enumerate(files_to_download):
        url = f"https://huggingface.co/datasets/deepmind/code_contests/resolve/main/{file_path}"
        print(f"\n📦 [{file_idx+1}/{len(files_to_download)}] Downloading {file_path.split('/')[-1]}...")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            print(f"   Downloaded: {len(data)/1024/1024:.1f} MB")

            # Parse parquet
            table = pq.read_table(io.BytesIO(data))
            df = table.to_pandas()

            # Filter CF problems
            cf_mask = df["cf_contest_id"] > 0
            cf_df = df[cf_mask]
            print(f"   CF problems: {len(cf_df)}")

            file_imported = 0
            file_skipped = 0

            for _, row in cf_df.iterrows():
                contest_id = int(row["cf_contest_id"])
                index = row["cf_index"]
                source_id = f"{contest_id}{index}"
                title = row["name"]
                description = row["description"]

                if not description or len(description) < 50:
                    file_skipped += 1
                    continue

                content = f"Problem {source_id}: {title}\n\n{description}"
                rating = int(row.get("cf_rating", 0)) if row.get("cf_rating") else ""
                tags = row.get("cf_tags", [])
                tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
                url_str = f"https://codeforces.com/problemset/problem/{contest_id}/{index}"

                try:
                    # Try UPDATE first (for existing problems without description)
                    cursor = conn.execute(
                        "UPDATE problems SET content = ? WHERE source = 'codeforces' AND source_id = ? AND LENGTH(content) < 300",
                        (content[:5000], source_id)
                    )
                    if cursor.rowcount > 0:
                        file_imported += 1
                    else:
                        # Insert new if not exists
                        conn.execute(
                            "INSERT OR IGNORE INTO problems (source, source_id, title, content, difficulty, tags, url) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)",
                            ("codeforces", source_id, title, content[:5000], str(rating), tags_str, url_str)
                        )
                        if cursor.rowcount > 0:
                            file_imported += 1
                        else:
                            file_skipped += 1
                except sqlite3.Error:
                    file_skipped += 1

            conn.commit()
            total_imported += file_imported
            total_skipped += file_skipped
            print(f"   Imported: {file_imported} | Skipped: {file_skipped}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    conn.close()
    print(f"\n✅ Total: {total_imported} imported, {total_skipped} skipped")


if __name__ == "__main__":
    db_path = Path("problem_data/problems.db")
    max_files = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    db_path.parent.mkdir(parents=True, exist_ok=True)
    import_deepmind_cf(db_path, max_files)
