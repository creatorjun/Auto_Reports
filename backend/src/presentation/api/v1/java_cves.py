# backend/src/presentation/api/v1/java_cves.py
from src.application.use_cases.java_cves import JavaReleases, JavaResults
from src.presentation.api.v1.vendor_cve_routes import vendor_cve_router


router = vendor_cve_router("java-cves", lambda services: services.java_cves, JavaReleases, JavaResults)
