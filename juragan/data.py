"""Synthetic, deterministic store dataset for a small Indonesian grocery + digital-services shop.

Everything here is generated from a fixed seed, so evaluation answers are reproducible.
The data is SYNTHETIC: it is modelled on a typical "toko sembako + PPOB" but contains
no real transactions.
"""

from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

SEED = 20261122
END_DATE = date(2026, 11, 22)  # last day with sales in the dataset
DAYS = 90

SCHEMA = """
CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    lead_time_days INTEGER NOT NULL
);
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit TEXT NOT NULL,
    cost_price INTEGER NOT NULL,      -- rupiah
    sell_price INTEGER NOT NULL,      -- rupiah
    supplier_id INTEGER REFERENCES suppliers(id),
    is_service INTEGER NOT NULL DEFAULT 0  -- 1 = PPOB / digital service (no stock)
);
CREATE TABLE stock (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    qty INTEGER NOT NULL,
    reorder_point INTEGER NOT NULL
);
CREATE TABLE sales (
    id INTEGER PRIMARY KEY,
    sold_at TEXT NOT NULL,            -- ISO date YYYY-MM-DD
    product_id INTEGER NOT NULL REFERENCES products(id),
    qty INTEGER NOT NULL,
    unit_price INTEGER NOT NULL,
    payment_method TEXT NOT NULL      -- cash | qris | transfer
);
CREATE TABLE purchases (
    id INTEGER PRIMARY KEY,
    purchased_at TEXT NOT NULL,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    qty INTEGER NOT NULL,
    unit_cost INTEGER NOT NULL
);
CREATE INDEX idx_sales_date ON sales(sold_at);
CREATE INDEX idx_sales_product ON sales(product_id);
"""

SUPPLIERS = [
    (1, "CV Sumber Pangan", "Sidoarjo", 2),
    (2, "UD Maju Jaya", "Surabaya", 3),
    (3, "PT Segar Minuman", "Surabaya", 4),
    (4, "Toko Grosir Berkah", "Sidoarjo", 1),
]

# (sku, name, category, unit, cost, sell, supplier, is_service, base_daily_demand)
PRODUCTS = [
    ("BRS-05", "Beras Premium 5 kg", "Sembako", "karung", 68000, 76000, 1, 0, 3.0),
    ("BRS-01", "Beras Medium 1 kg", "Sembako", "kg", 12500, 14000, 1, 0, 6.0),
    ("MNY-1L", "Minyak Goreng 1 L", "Sembako", "botol", 15500, 17500, 1, 0, 7.0),
    ("MNY-2L", "Minyak Goreng 2 L", "Sembako", "pouch", 30000, 33500, 1, 0, 3.0),
    ("GLA-1K", "Gula Pasir 1 kg", "Sembako", "kg", 16000, 18000, 1, 0, 5.0),
    ("TLR-1K", "Telur Ayam 1 kg", "Sembako", "kg", 26000, 29000, 4, 0, 6.0),
    ("TPG-1K", "Tepung Terigu 1 kg", "Sembako", "kg", 11000, 12500, 4, 0, 2.5),
    ("GRM-250", "Garam Dapur 250 g", "Sembako", "bks", 2500, 3500, 4, 0, 2.0),
    ("KCP-135", "Kecap Manis 135 ml", "Bumbu", "botol", 5500, 7000, 2, 0, 3.0),
    ("SMB-140", "Saus Sambal 140 ml", "Bumbu", "botol", 6000, 7500, 2, 0, 2.0),
    ("BMB-NG", "Bumbu Nasi Goreng", "Bumbu", "sachet", 2000, 3000, 2, 0, 3.5),
    ("MIE-GRG", "Mi Instan Goreng", "Makanan", "bks", 2800, 3500, 2, 0, 18.0),
    ("MIE-KUA", "Mi Instan Kuah Soto", "Makanan", "bks", 2700, 3300, 2, 0, 12.0),
    ("SRD-155", "Sarden Kaleng 155 g", "Makanan", "kaleng", 8500, 10500, 2, 0, 1.5),
    ("BSK-CKL", "Biskuit Cokelat", "Makanan", "bks", 7000, 9000, 2, 0, 3.0),
    ("ROT-TWR", "Roti Tawar", "Makanan", "bks", 13000, 15500, 4, 0, 2.5),
    ("AIR-600", "Air Mineral 600 ml", "Minuman", "botol", 2500, 3500, 3, 0, 20.0),
    ("AIR-GLN", "Air Mineral Galon 19 L", "Minuman", "galon", 17000, 21000, 3, 0, 4.0),
    ("TEH-BTL", "Teh Botol 350 ml", "Minuman", "botol", 3800, 5000, 3, 0, 9.0),
    ("KOP-SCH", "Kopi Sachet 3in1", "Minuman", "sachet", 1300, 2000, 3, 0, 15.0),
    ("SSU-KTL", "Susu Kental Manis", "Minuman", "kaleng", 10500, 12500, 3, 0, 2.0),
    ("ISO-500", "Minuman Isotonik 500 ml", "Minuman", "botol", 5500, 7000, 3, 0, 4.0),
    ("SBN-MND", "Sabun Mandi Batang", "Kebutuhan Rumah", "pcs", 3200, 4500, 2, 0, 3.0),
    ("SMP-SCH", "Sampo Sachet", "Kebutuhan Rumah", "sachet", 800, 1000, 2, 0, 8.0),
    ("DTG-800", "Deterjen Bubuk 800 g", "Kebutuhan Rumah", "bks", 17000, 20000, 2, 0, 1.5),
    ("PST-GGI", "Pasta Gigi 120 g", "Kebutuhan Rumah", "tube", 9500, 12000, 2, 0, 1.2),
    ("TSU-250", "Tisu Wajah 250 lembar", "Kebutuhan Rumah", "bks", 11000, 13500, 2, 0, 1.0),
    ("GAS-3KG", "Gas LPG 3 kg (isi ulang)", "Energi", "tabung", 18000, 22000, 4, 0, 5.0),
    # PPOB / digital services: price = admin fee earned per transaction, no stock
    ("PLS-10K", "Pulsa 10.000", "PPOB", "trx", 10200, 12000, None, 1, 8.0),
    ("PLS-25K", "Pulsa 25.000", "PPOB", "trx", 25100, 27000, None, 1, 4.0),
    ("TKN-50K", "Token Listrik 50.000", "PPOB", "trx", 50500, 53000, None, 1, 4.0),
    ("TRF-BNK", "Transfer Bank (biaya admin)", "PPOB", "trx", 2500, 5000, None, 1, 6.0),
    ("EMN-TOP", "Top Up E-Money (biaya admin)", "PPOB", "trx", 1000, 3000, None, 1, 5.0),
]

PAYMENT_WEIGHTS = [("cash", 0.55), ("qris", 0.35), ("transfer", 0.10)]


def _payment(rng: random.Random) -> str:
    r = rng.random()
    acc = 0.0
    for name, w in PAYMENT_WEIGHTS:
        acc += w
        if r <= acc:
            return name
    return "cash"


def build_database(path: str | Path) -> Path:
    """Create (or overwrite) the synthetic SQLite database at ``path``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    rng = random.Random(SEED)
    con = sqlite3.connect(path)
    try:
        con.executescript(SCHEMA)
        con.executemany("INSERT INTO suppliers VALUES (?,?,?,?)", SUPPLIERS)
        for pid, p in enumerate(PRODUCTS, start=1):
            sku, name, cat, unit, cost, sell, sup, svc, _ = p
            con.execute(
                "INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?)",
                (pid, sku, name, cat, unit, cost, sell, sup, svc),
            )

        start = END_DATE - timedelta(days=DAYS - 1)
        sale_rows = []
        sold_qty = {pid: 0 for pid in range(1, len(PRODUCTS) + 1)}
        last30_qty = {pid: 0 for pid in range(1, len(PRODUCTS) + 1)}
        for d in range(DAYS):
            day = start + timedelta(days=d)
            weekday = day.weekday()
            weekend = 1.25 if weekday >= 5 else 1.0
            payday = 1.3 if day.day in (25, 26, 27, 28, 1, 2) else 1.0
            trend = 0.9 + 0.2 * (d / DAYS)  # gentle growth over the period
            for pid, p in enumerate(PRODUCTS, start=1):
                base = p[8]
                lam = base * weekend * payday * trend
                # split daily demand into a few transactions
                n_trx = max(0, int(rng.gauss(lam / 1.6, lam / 4)))
                for _ in range(n_trx):
                    q = 1 if p[7] else rng.choice((1, 1, 1, 2, 2, 3))
                    sale_rows.append((day.isoformat(), pid, q, p[5], _payment(rng)))
                    sold_qty[pid] += q
                    if d >= DAYS - 30:
                        last30_qty[pid] += q
        con.executemany(
            "INSERT INTO sales (sold_at, product_id, qty, unit_price, payment_method) VALUES (?,?,?,?,?)",
            sale_rows,
        )

        # purchases: weekly restock per goods product
        purchase_rows = []
        for pid, p in enumerate(PRODUCTS, start=1):
            if p[7]:
                continue
            weekly = max(1, round(p[8] * 7 * 1.05))
            for w in range(0, DAYS, 7):
                day = start + timedelta(days=w)
                purchase_rows.append((day.isoformat(), p[6], pid, weekly, p[4]))
        con.executemany(
            "INSERT INTO purchases (purchased_at, supplier_id, product_id, qty, unit_cost) VALUES (?,?,?,?,?)",
            purchase_rows,
        )

        # stock on END_DATE: deterministic days-of-cover, a few items deliberately low
        low_items = {"MNY-1L", "TLR-1K", "AIR-GLN", "GAS-3KG", "MIE-GRG"}
        for pid, p in enumerate(PRODUCTS, start=1):
            if p[7]:
                continue
            daily = last30_qty[pid] / 30
            cover = rng.uniform(0.5, 2.0) if p[0] in low_items else rng.uniform(6, 20)
            qty = max(0, round(daily * cover))
            reorder = max(2, round(daily * 4))
            con.execute("INSERT INTO stock VALUES (?,?,?)", (pid, qty, reorder))
        con.commit()
    finally:
        con.close()
    return path
