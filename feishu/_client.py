"""HTTP client plumbing for the Feishu service.

Owns the ``requests.Session``, retry policy, request wrapper, and
helper functions that derive Feishu API URLs from config.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ClientMixin:
    """HTTP session + URL/headers helpers."""

    def __init__(self, config_path='config/feishu.yaml'):
        """Initialize with config file."""
        # Imported lazily so the package can be imported without a
        # configuration file being available (CI smoke test, etc.).
        from config_loader import load_feishu_config

        self.config = load_feishu_config(config_path)
        if self.config is None:
            self.config = {}
        self.access_token = None
        self.token_expires = 0

        # Field aliases can be overridden in config
        aliases = self.config.get('field_aliases', {})
        # FieldMixin may not be in the MRO yet at __init__ time when
        # ClientMixin alone is used; default to {} otherwise.
        default_aliases = getattr(self, 'DEFAULT_FIELD_ALIASES', {})
        self.field_aliases = {**default_aliases, **aliases}

        # Setup session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------

    def _request(self, method, url, **kwargs):
        """Wrapper for requests with error handling."""
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            return response
        except Exception as e:
            print(f"⚠️ Request failed: {e}")
            raise
