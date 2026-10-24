"""Run a SQL file in sql/ with DuckDB from the project root and save the result as CSV in results/.

Usage: python src/run_sql.py [sql/state_ranks.sql]
"""
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent


def run(sql_file: Path):
    con = duckdb.connect()
    con.execute(f"SET file_search_path = '{ROOT.as_posix()}'")
    return con.sql(sql_file.read_text("utf-8")).df()


def main():
    sql_file = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sql/state_ranks.sql"
    df = run(sql_file if sql_file.is_absolute() else ROOT / sql_file)
    out = ROOT / "results" / (sql_file.stem + ".csv")
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False)
    print(df.head(12).to_string(index=False))
    print(f"... {len(df)} rows -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
