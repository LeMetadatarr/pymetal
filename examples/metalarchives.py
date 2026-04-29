"""End-to-end tour of the pymetal API.

Run: python examples/metalarchives.py
"""
from pymetal import CreditSection, MetalArchives, ReleaseType


m = MetalArchives()

# -- Random band --------------------------------------------------------------
band = m.random_band()
print(band.name, "-", band.country, "-", ", ".join(band.genres))

# -- Random band filtered by genre -------------------------------------------
# `genre` is one of MA's 23 coarse buckets (see pymetal.locators.GENRES).
# Re-rolls automatically until a match is found, sleeping between attempts
# so we don't hammer MA.
black = m.random_band(genre="black")
print(f"black metal pick: {black.name} ({black.country})")

# -- Band detail by id (Carcass = 14) ----------------------------------------
carcass = m.get_band(14)
print(f"\n{carcass.name} ({carcass.country}) — formed {carcass.formed_in}")
print(f"  status: {carcass.status.value if carcass.status else None}")
print(f"  genres: {carcass.genres}")
print(f"  current label: {carcass.current_label_name}")
if carcass.audit:
    print(f"  audited: added {carcass.audit.added_on}, last edit {carcass.audit.last_modified_on}")

# -- Band lineup over time ---------------------------------------------------
print("\nlineup:")
for member in m.get_lineup(14)[:6]:
    span = f"{member.date_from or '?'}–{member.date_to or 'present'}"
    print(f"  [{member.status.value:>14}] {member.artist_name:<20} {span}  {member.role}")

# -- Discography -------------------------------------------------------------
disco = m.get_discography(14)
print(f"\ndiscography: {len(disco)} releases")
for r in disco[:3]:
    print(f"  {r.release_date}  {r.type.value:<12} {r.title}")

# -- Release with tracks ------------------------------------------------------
release, songs, apps = m.get_release(451600)  # Carcass — Heartwork
print(f"\n{release.title} ({release.release_date}) — {release.type.value}")
print(f"  label: {release.label_name}, format: {release.format.value if release.format else release.format_raw}")
print(f"  total length: {release.total_length}, reviews: {release.reviews_count}@{release.reviews_avg_percent}%")
for song, app in list(zip(songs, apps))[:3]:
    print(f"  {app.track_no:>2}. {song.title:<25} {song.length}")

# -- Per-release credits (band / guest / staff) ------------------------------
print("\nstaff credits on Heartwork:")
for credit in m.get_release_lineup(451600):
    if credit.section is CreditSection.STAFF:
        print(f"  {credit.artist_name:<25} {credit.role}")

# -- Other versions / re-issues ----------------------------------------------
versions = m.get_other_versions(451600)
print(f"\nHeartwork has {len(versions)} known versions; first three:")
for v in versions[:3]:
    print(f"  {v.release_date}  {v.format.value if v.format else '?':<10} {v.label_name} / {v.catalog_no}")

# -- Split release: per-track band attribution -------------------------------
split, _, split_apps = m.get_release(485040)  # Napalm Death / S.O.B.
print(f"\nsplit '{split.title}' attributes tracks to band ids: {sorted(set(a.band_id for a in split_apps))}")

# -- Artist detail ------------------------------------------------------------
steer = m.get_artist(490)
print(f"\nartist: {steer.alias} — {steer.real_name}, born {steer.born}")

# -- Search bands with full filter set ---------------------------------------
print("\nPortuguese heavy metal bands formed in the 80s:")
for hit in m.search_bands(country="PT", genre="Heavy", year_from=1980, year_to=1989):
    print(f"  {hit.ma_id:<7} {hit.name}")

# -- Search albums by release type -------------------------------------------
# Two notes:
#   1. Pass `exact_band_match=True` — MA's default is fuzzy band matching, so
#      "Carcass" otherwise pulls in "Carcass Grinder", "Living Carcass" etc.
#   2. MA's albums-search response omits the year column when `band_name` is
#      set, so `hit.release_date` is None in this query. Use `get_discography`
#      (or `get_release` per id) when you need release dates.
print("\nCarcass full-lengths and EPs:")
for hit in m.search_albums(
    band_name="Carcass",
    exact_band_match=True,
    release_type=[ReleaseType.FULL_LENGTH, ReleaseType.EP],
):
    print(f"  {hit.type.value if hit.type else '?':<11} {hit.title}")

# -- Search songs (returns rich SongSearchHit with band_id/release_id/lyrics_id)
print("\nsongs titled 'Heartwork' across MA:")
for hit in m.search_songs(song_title="Heartwork", band_name="Carcass"):
    print(f"  {hit.lyrics_id:<8} {hit.band_name} — {hit.title}  ({hit.release_type.value if hit.release_type else '?'})")

# -- Lyrics by song id --------------------------------------------------------
text = m.get_lyrics_by_song_id(172090)
if text:
    print("\nfirst lines of Heartwork lyrics:")
    for line in text.splitlines()[:6]:
        print(" ", line)

# -- High-level lyrics generator ---------------------------------------------
print("\nfirst hit from full-text lyrics search 'ace of spades':")
for lyrics in m.get_lyrics(song_title="Ace of Spades", band_name="Motörhead"):
    print(lyrics.splitlines()[0])
    break
