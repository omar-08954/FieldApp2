"""Central, non-secret application settings.

Secrets remain in Streamlit's secret store.  Keeping operational constants
here prevents security and performance behaviour drifting between pages.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    session_timeout_seconds: int = 30 * 60
    max_login_attempts: int = 5
    account_lock_minutes: int = 15
    online_user_window_minutes: int = 15
    max_upload_bytes: int = 5 * 1024 * 1024
    database_pool_min_connections: int = 1
    database_pool_max_connections: int = 10
    search_page_size: int = 200
    search_fuzzy_candidate_limit: int = 2_000
    cache_ttl_reference_seconds: int = 60
    cache_ttl_search_seconds: int = 15
    cache_ttl_operational_seconds: int = 10
    cache_ttl_diagnostics_seconds: int = 30
    storage_delete_attempts: int = 3


SETTINGS = Settings()
