"""Command line: ``juragan seed | ask | mcp | eval``."""

from __future__ import annotations

import argparse
import json
import sys

import anyio


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import logging

    logging.getLogger("httpx").setLevel(logging.WARNING)
    ap = argparse.ArgumentParser(prog="juragan", description="JURAGAN - AI agent asisten data toko berbasis MCP")
    ap.add_argument("--db", default="data/toko.db")
    ap.add_argument("--reports", default="reports")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("seed", help="buat ulang database toko sintetis")

    a = sub.add_parser("ask", help="tanya agen")
    a.add_argument("question")
    a.add_argument("--provider", default="local", choices=["local", "claude", "ollama"])
    a.add_argument("--transport", default="inprocess", choices=["inprocess", "stdio"])
    a.add_argument("--json", action="store_true", help="cetak hasil lengkap + jejak tool sebagai JSON")

    sub.add_parser("mcp", help="jalankan MCP server (stdio)")

    e = sub.add_parser("eval", help="jalankan evaluasi")
    e.add_argument("--provider", default="local", choices=["local", "claude", "ollama"])
    e.add_argument("--strict", action="store_true", help="exit 1 jika ada tugas gagal")
    e.add_argument("--out", default="eval/results")

    args = ap.parse_args(argv)

    if args.cmd == "seed":
        from .data import build_database

        print(f"Database dibuat: {build_database(args.db)}")
    elif args.cmd == "mcp":
        from .mcp_server import main as serve

        serve(["--db", args.db, "--reports", args.reports])
    elif args.cmd == "ask":
        from .agent import ask

        res = anyio.run(lambda: ask(args.question, args.provider, db=args.db, reports=args.reports,
                                    transport=args.transport))
        if args.json:
            print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(res.answer)
            tools = ", ".join(tc.name for tc in res.tool_calls) or "-"
            print(f"\n[{res.provider} | tools: {tools} | {res.latency_ms:.0f} ms]")
    elif args.cmd == "eval":
        from .evaluate import run_eval

        summary = anyio.run(lambda: run_eval(args.provider, db=args.db, out_dir=args.out))
        if args.strict and summary["failed"]:
            sys.exit(1)


if __name__ == "__main__":
    main()
