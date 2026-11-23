"""Static read-only guard for SQL that an LLM (or a user) wants to run.

Defence in depth: this check runs first, and the connection itself is also opened
read-only (``mode=ro``) with an authorizer that denies writes, so a bypass of this
regex layer still cannot modify data.
"""

from __future__ import annotations

import re

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|pragma|vacuum|reindex|grant|revoke|load_extension)\b",
    re.IGNORECASE,
)


class UnsafeSQLError(ValueError):
    """Raised when a statement is not a single read-only query."""


def _strip_comments_and_strings(sql: str) -> str:
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    # blank out string literals so keywords inside text values do not trip the guard
    sql = re.sub(r"'(?:''|[^'])*'", "''", sql)
    sql = re.sub(r'"(?:""|[^"])*"', '""', sql)
    return sql


def check_sql(sql: str) -> str:
    """Return the cleaned statement if it is a single SELECT/WITH query, else raise."""
    if not sql or not sql.strip():
        raise UnsafeSQLError("Query kosong / empty query.")
    body = _strip_comments_and_strings(sql).strip().rstrip(";").strip()
    if ";" in body:
        raise UnsafeSQLError("Hanya satu statement yang diizinkan / only one statement is allowed.")
    first = body.split(None, 1)[0].lower() if body else ""
    if first not in ("select", "with"):
        raise UnsafeSQLError("Hanya query SELECT yang diizinkan / only SELECT queries are allowed.")
    m = FORBIDDEN.search(body)
    if m:
        raise UnsafeSQLError(f"Kata kunci terlarang / forbidden keyword: {m.group(1).upper()}")
    return sql.strip().rstrip(";")
