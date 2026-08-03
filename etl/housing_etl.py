# ETL script for Housing sector.
#
# STATUS: no automated county-level source available -- use manual entry
# (Django admin or the /data/upload/ CSV form) with an appropriate DataSource.
# Enter data under CountyScore(sector='Housing', ...).
#
# Why not automated:
# - Kenya's national Open Data portal (opendata.go.ke) has been offline for
#   years pending a legal/institutional revival.
# - KNBS's 2023/24 Kenya Housing Survey covers all 47 counties but is only
#   published as static PDF/Excel reports and gated microdata (NADA catalog,
#   https://statistics.knbs.or.ke/nada/index.php/catalog/184), not a live,
#   queryable dataset -- there's nothing here to poll on a schedule.
