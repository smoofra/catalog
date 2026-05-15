#!/usr/bin/env python3
"""Fill in missing title/author fields in catalog.csv using Open Library, Crossref, and DataCite."""

import csv
import json
import sys
import time
import urllib.parse
import urllib.request

CSV_FILE = "catalog.csv"
FIELDNAMES = ["isbn", "doi", "url", "epc", "title", "author"]


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "cardex/1.0 (larry@elder-gods.org)"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  error fetching {url}: {e}", file=sys.stderr)
        return None


def doi_ra(prefix):
    data = fetch(f"https://doi.org/ra/{prefix}")
    if isinstance(data, list) and data:
        return data[0].get("RA")
    return None


def lookup_isbn(isbn):
    data = fetch(f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data")
    if not data:
        return None, None
    entry = data.get(f"ISBN:{isbn}")
    if not entry:
        return None, None
    title = entry.get("title")
    by_statement = entry.get("by_statement", "").strip().rstrip(".")
    authors = entry.get("authors", [])
    author = by_statement or "; ".join(a["name"] for a in authors if "name" in a) or None
    return title, author


def lookup_crossref(doi):
    encoded = urllib.parse.quote(doi, safe="/")
    data = fetch(f"https://api.crossref.org/works/{encoded}")
    if not data:
        return None, None
    msg = data.get("message", {})
    title = (msg.get("title") or [None])[0]
    author_parts = []
    for a in msg.get("author", []):
        name = " ".join(filter(None, [a.get("given"), a.get("family")]))
        if name:
            author_parts.append(name)
    return title, "; ".join(author_parts) or None


def lookup_datacite(doi):
    encoded = urllib.parse.quote(doi, safe="/")
    data = fetch(f"https://api.datacite.org/dois/{encoded}")
    if not data:
        return None, None
    attrs = data.get("data", {}).get("attributes", {})
    titles = attrs.get("titles", [])
    title = titles[0].get("title") if titles else None
    creator_parts = []
    for c in attrs.get("creators", []):
        name = c.get("name") or " ".join(filter(None, [c.get("givenName"), c.get("familyName")]))
        if name:
            creator_parts.append(name)
    return title, "; ".join(creator_parts) or None


def lookup_doi(doi):
    prefix = doi.split("/")[0]
    ra = doi_ra(prefix)
    time.sleep(0.3)
    if ra == "Crossref":
        return lookup_crossref(doi)
    elif ra == "DataCite":
        return lookup_datacite(doi)
    print(f"  unknown RA '{ra}' for prefix {prefix}", file=sys.stderr)
    return None, None


def main():
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    changed = 0

    for i, row in enumerate(rows):
        isbn = row.get("isbn", "").strip()
        doi = row.get("doi", "").strip()
        title = row.get("title", "").strip()
        author = row.get("author", "").strip()

        need_title = not title
        need_author = not author

        if not (need_title or need_author):
            continue
        if not isbn and not doi:
            continue

        label = isbn or doi
        print(f"[{i+1}/{total}] {label}")

        new_title, new_author = None, None

        if isbn:
            new_title, new_author = lookup_isbn(isbn)
            time.sleep(0.5)

        if doi and (not new_title or not new_author):
            dt, da = lookup_doi(doi)
            time.sleep(0.5)
            if not new_title:
                new_title = dt
            if not new_author:
                new_author = da

        if need_title and new_title:
            print(f"  title:  {new_title}")
            row["title"] = new_title
            changed += 1
        if need_author and new_author:
            print(f"  author: {new_author}")
            row["author"] = new_author
            changed += 1

    if changed:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nUpdated {changed} field(s) in {CSV_FILE}.")
    else:
        print("\nNothing to update.")


if __name__ == "__main__":
    main()
