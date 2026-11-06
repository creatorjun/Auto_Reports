# backend/src/presentation/api/v1/database_cves.py
from src.application.use_cases.database_cves import DatabaseReleases, DatabaseResults
from src.presentation.api.v1.vendor_cve_routes import vendor_cve_router


router = vendor_cve_router("db-cves", lambda services: services.db_cves, DatabaseReleases, DatabaseResults)
