#!/usr/bin/env python3
"""
Alaina avy ao amin'ny https://impriad.mg/produits/ ny lisitry ny produit, ary soratana ao `produits.json`.
Fiarovana: raha tsy mifanaraka ny isa (produit/sokajy) na misy vidiny tsy ara-dalàna, dia MIHOATRA ny script
(exit 1) ary tsy misy commit -> tsy simba ny katalaogy ampiasain'ny app.
"""
import json
import pathlib
import re
import sys
import datetime

import requests
from bs4 import BeautifulSoup

URL = "https://impriad.mg/produits/"
OUT = pathlib.Path(__file__).resolve().parent.parent / "produits.json"
PRICE_FULL = re.compile(r"^(\d[\d\s\u00a0\u202f]*)\s*Ar$", re.I)
DIGITS = re.compile(r"^\d[\d\s\u00a0\u202f]*$")
CHIP = re.compile(r"^(.*?)\s*\((\d+)\)$")
SLUG = re.compile(r"/produit/([^/?#]+)/?$")


def fail(msg):
    print("ERREUR:", msg, file=sys.stderr)
    sys.exit(1)


def to_int(txt):
    return int(re.sub(r"[^\d]", "", txt))


def parse(html):
    soup = BeautifulSoup(html, "html.parser")

    # 1) Sokajy: rohy « Label (N) » mankany amin'ny #anchor
    cats = {}  # label -> (id, count) ; ordre = ordre de la navigation
    for a in soup.find_all("a", href=True):
        if "#" not in a["href"]:
            continue
        m = CHIP.match(a.get_text(" ", strip=True))
        if not m:
            continue
        label, count = m.group(1).strip(), int(m.group(2))
        anchor = a["href"].split("#", 1)[1]
        if label and anchor and label not in cats:
            cats[label] = (anchor, count)
    if not cats:
        fail("Tsy hita ny lisitry ny sokajy (niova ny endriky ny pejy?)")

    labels_by_len = sorted(cats, key=len, reverse=True)

    # 2) Produit
    seen = {}
    for a in soup.find_all("a", href=SLUG):
        pid = SLUG.search(a["href"]).group(1)
        if pid in seen:
            continue
        strings = [s for s in a.stripped_strings]
        if not strings:
            continue

        # vidiny: tsipika farany (« 3 300 Ar » na « 3 300 » + « Ar »)
        price = None
        if PRICE_FULL.match(strings[-1]):
            price = to_int(strings[-1])
            strings = strings[:-1]
        elif strings[-1].lower() == "ar" and len(strings) >= 2 and DIGITS.match(strings[-2]):
            price = to_int(strings[-2])
            strings = strings[:-2]
        else:
            joined = " ".join(strings)
            m = re.search(r"((?:\d{1,3}(?:[ \u00a0\u202f]\d{3})+|\d+))\s*Ar$", joined)
            if m:
                price = to_int(m.group(1))
                strings = [joined[: m.start()].strip()]
        if price is None:
            fail(f"Vidiny tsy hita ho an'ny {pid}: {strings}")

        lang = "mg"
        rest = []
        for s in strings:
            if s.upper() == "FR":
                lang = "fr"
            elif s.upper() == "EN":
                lang = "en"
            elif not re.search(r"[A-Za-z0-9]", s):
                continue  # emoji / sary
            else:
                rest.append(s)

        cat_label = None
        name_parts = []
        for s in rest:
            if cat_label is None and s in cats:
                cat_label = s
                continue
            name_parts.append(s)
        if cat_label is None:  # sokajy sy anarana mitambatra amin'ny tsipika iray
            for i, s in enumerate(name_parts):
                for lab in labels_by_len:
                    if s.startswith(lab + " "):
                        cat_label = lab
                        name_parts[i] = s[len(lab) + 1:].strip()
                        break
                if cat_label:
                    break
        if cat_label is None:
            fail(f"Sokajy tsy hita ho an'ny {pid}: {rest}")
        name = " ".join(p for p in name_parts if p).strip()
        if not name:
            fail(f"Anarana foana ho an'ny {pid}")
        seen[pid] = {"id": pid, "name": name, "category": cats[cat_label][0], "language": lang, "price": price}

    products = list(seen.values())

    # 3) Fanamarinana
    expected = sum(c for _, c in cats.values())
    if len(products) != expected:
        fail(f"Isan'ny produit {len(products)} ≠ {expected} (araka ny sokajy)")
    by_cat = {}
    for p in products:
        by_cat[p["category"]] = by_cat.get(p["category"], 0) + 1
    for label, (cid, cnt) in cats.items():
        if by_cat.get(cid, 0) != cnt:
            fail(f"Sokajy {label}: {by_cat.get(cid, 0)} ≠ {cnt}")
    if not all(100 <= p["price"] <= 500000 for p in products):
        fail("Misy vidiny tsy ara-dalàna (<100 na >500000)")

    categories = [{"id": cid, "label": label, "count": cnt} for label, (cid, cnt) in cats.items()]
    return categories, products


def main():
    r = requests.get(
        URL,
        timeout=30,
        headers={"User-Agent": "impriad-catalog-bot/1.0 (+https://github.com/sitraka0417/impriad-data)"},
    )
    r.raise_for_status()
    categories, products = parse(r.text)

    old = {}
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
    if old.get("categories") == categories and old.get("products") == products:
        print("Tsy misy fiovana.")
        return

    # fampitahana (ho an'ny log)
    om = {p["id"]: p for p in old.get("products", [])}
    nm = {p["id"]: p for p in products}
    for pid, p in nm.items():
        if pid not in om:
            print(f"VAOVAO   {p['name']}  {p['price']} Ar")
        elif om[pid]["price"] != p["price"]:
            print(f"VIDINY   {p['name']}  {om[pid]['price']} -> {p['price']}")
        elif om[pid] != p:
            print(f"FIOVANA  {p['name']}")
    for pid, p in om.items():
        if pid not in nm:
            print(f"AVOAKA   {p['name']}")

    data = {
        "version": int(old.get("version", 0)) + 1,
        "updatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": URL,
        "categories": categories,
        "products": products,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Voasoratra: v{data['version']} ({len(products)} produit)")


if __name__ == "__main__":
    main()
