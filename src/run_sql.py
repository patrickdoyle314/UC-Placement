"""Run a SQL file in sql/ with DuckDB from the project root and save the result as CSV in results/.

Usage: python src/run_sql.py [sql/state_ranks.sql]
"""
# ===================================================================================================
# HOW TO READ THIS FILE
# Business purpose: run a .sql file with DuckDB (a fast database that can query files directly)
# and save the answer as a CSV in results/, so SQL results sit next to the pandas ones.
#
# Python ideas: duckdb.connect() for an in-memory database, .df() to get a pandas table back,
# sys.argv for command-line arguments, Path.stem for a file name without its extension.
# ===================================================================================================
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent


# Run one query and return the result as a pandas table. SET file_search_path lets the SQL refer to
# files by paths relative to the project root. The tests call this function too.
def run(sql_file: Path):
    con = duckdb.connect()
    con.execute(f"SET file_search_path = '{ROOT.as_posix()}'")
    return con.sql(sql_file.read_text("utf-8")).df()


def main():
    sql_file = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sql/state_ranks.sql"  # the SQL file named on the command line, or state_ranks.sql by default
    df = run(sql_file if sql_file.is_absolute() else ROOT / sql_file)
    out = ROOT / "results" / (sql_file.stem + ".csv")  # state_ranks.sql -> results/state_ranks.csv
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False)
    print(df.head(12).to_string(index=False))
    print(f"... {len(df)} rows -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
