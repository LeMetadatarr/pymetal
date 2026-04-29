"""Browse metal-archives by country, genre, and letter.

Demonstrates the dedicated `browse/ajax-*` endpoints that walk the full
catalog (vs. `search_bands` which hits the search index). Also shows
`get_upcoming_releases`, `get_rip_artists`, `get_label`, and
`random_band`.

Run: python examples/browse.py
"""
from itertools import islice

from pymetal import MetalArchives


ma = MetalArchives()


# -- 1. Random band ----------------------------------------------------------
# /band/random redirects to a band page; we follow it and parse.
b = ma.random_band()
print(f"random band: {b.name} ({b.country}) — {', '.join(b.genres)}")

# Filter by genre — keeps re-rolling until a match is found (or 50 tries).
heavy = ma.random_band(genre="heavy")
print(f"random heavy band: {heavy.name} ({heavy.country})")


# -- 2. Browse every band from a country -------------------------------------
# Returns more rows than `search_bands(country=...)` because it walks the
# dedicated browse endpoint.
print("\nfirst 5 Portuguese bands MA lists:")
for hit in islice(ma.browse_bands_by_country("PT"), 5):
    print(f"  {hit.ma_id:<10} {hit.name:<30} {hit.genre}")

# Count every band in a country (paginate=True walks all pages).
total_pt = sum(1 for _ in ma.browse_bands_by_country("PT"))
print(f"  total Portuguese bands on MA: {total_pt}")


# -- 3. Browse by genre slug -------------------------------------------------
# Slugs are MA's coarse 23-bucket taxonomy (lowercase, single word):
#   black, death, doom, stoner, sludge, electronic, industrial,
#   experimental, avant-garde, folk, viking, pagan, gothic, grindcore,
#   groove, heavy, metalcore, deathcore, power, progressive, speed,
#   symphonic, thrash
print("\nfirst 5 black-metal bands (alphabetical):")
for hit in islice(ma.browse_bands_by_genre("black"), 5):
    print(f"  {hit.name:<30} {hit.country:<25} {hit.genre}")


# -- 4. Browse by letter -----------------------------------------------------
# 'A'..'Z' for Latin starts; 'NBR' for digits; '~' for symbols/non-Latin.
print("\nfirst 5 bands starting with 'A':")
for hit in islice(ma.browse_bands_by_letter("A"), 5):
    print(f"  {hit.ma_id:<10} {hit.name:<30} {hit.country}")


# -- 5. Compose: every active French black-metal band ------------------------
# Browse-by-genre + filter by country in Python is faster than re-paging the
# search endpoint when both filters are coarse.
print("\nfirst 5 French black-metal bands:")
fr_black = (h for h in ma.browse_bands_by_genre("black") if h.country == "France")
for hit in islice(fr_black, 5):
    print(f"  {hit.name:<35} {hit.genre}")


# -- 6. Upcoming releases ----------------------------------------------------
print("\nnext 5 upcoming releases:")
for u in islice(ma.get_upcoming_releases(), 5):
    print(f"  {u.release_date:<25} {u.band_name:<25} {u.release_title} ({u.type.value if u.type else '?'})")


# -- 7. Deceased artists -----------------------------------------------------
# /artist/rip — ~10k rows. Useful for memorial projects, statistics.
print("\nfirst 5 deceased artists in MA's RIP list:")
for r in islice(ma.get_rip_artists(), 5):
    print(f"  {r.artist_name:<25} {r.country:<25} died {r.died_on}")


# -- 8. Label detail ---------------------------------------------------------
nb = ma.get_label(2)  # Nuclear Blast Records
print(f"\nlabel: {nb.name}")
print(f"  founded: {nb.founding_date} in {nb.country}")
print(f"  status: {nb.status}")
print(f"  styles: {nb.styles}")
print(f"  {len(nb.sub_labels)} sub-labels; first three: {nb.sub_labels[:3]}")


# -- 9. End-to-end: every Portuguese black-metal band's releases pre-2000 ---
# Combine browse + per-band discography; demonstrates the catalog walk.
print("\nPortuguese black-metal demos before 2000 (first 10):")
shown = 0
for band in ma.browse_bands_by_country("PT"):
    if "Black" not in (band.genre or ""):
        continue
    for rel in ma.get_discography(band.ma_id):
        year = (rel.release_date or "").split()[-1] if rel.release_date else ""
        if year.isdigit() and int(year) < 2000 and rel.type.value == "Demo":
            print(f"  {year}  {band.name:<25} {rel.title}")
            shown += 1
            if shown >= 10:
                break
    if shown >= 10:
        break
