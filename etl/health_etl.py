# ETL script for Health sector.
#
# STATUS: no automated county-level source is wired in yet -- use manual entry
# (Django admin or the /data/upload/ CSV form) with an appropriate DataSource
# until this is revisited. Enter data under CountyScore(sector='Health', ...).
#
# Why not automated yet:
# - WHO GHO API and World Bank Open Data have real, free, no-auth Kenya health
#   indicators, but both are NATIONAL-level only (no county breakdown) -- not
#   usable for a per-county scorecard.
# - Kenya Master Health Facility List (KMHFL) publishes a documented, public,
#   no-auth-looking API with a county field (base URL api.kmhfr.health.go.ke,
#   docs: https://mfl-api-docs.readthedocs.io/en/latest/) and is the most
#   promising real candidate -- but it could not be reached from this dev
#   environment (connection timed out; may be geo-restricted to Kenya, or
#   just down). Verify live connectivity and response shape from a Kenya-based
#   network before wiring it in, following the same pattern as
#   etl/agriculture_etl.py and etl/water_etl.py.
# - KHIS/DHIS2 (hiskenya.org) has real county-disaggregated indicators but
#   requires an authenticated account -- not a public API.
