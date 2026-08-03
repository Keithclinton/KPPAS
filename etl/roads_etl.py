# ETL script for Roads sector.
#
# STATUS: no automated county-level source available -- use manual entry
# (Django admin or the /data/upload/ CSV form) with an appropriate DataSource.
# Enter data under CountyScore(sector='Roads', ...).
#
# Why not automated:
# - KeNHA, KURA and KeRRA publish road projects as static listing pages, not
#   structured APIs or downloadable datasets.
# - PPRA's procurement data is available as a genuine no-auth bulk download
#   (Open Contracting Data, https://data.open-contracting.org/en/publication/147,
#   sourced from tenders.go.ke/ocds) but tenders aren't reliably attributable
#   to a single county per record -- it would need fragile inference from
#   free-text procuring-entity names, not a clean per-county indicator.
