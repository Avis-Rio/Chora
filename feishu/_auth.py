"""Tenant access token management for the Feishu service."""

from datetime import datetime


class AuthMixin:
    """Get / cache the tenant access token used by every Feishu call."""

    def get_access_token(self):
        """Get tenant access token from Feishu API."""
        if self.access_token and datetime.now().timestamp() < self.token_expires:
            return self.access_token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}

        feishu_cfg = self.config.get('feishu', self.config)
        data = {
            "app_id": feishu_cfg.get('app_id'),
            "app_secret": feishu_cfg.get('app_secret'),
        }

        try:
            response = self._request("POST", url, headers=headers, json=data)
            result = response.json()

            if result.get('code') == 0:
                self.access_token = result.get('tenant_access_token')
                self.token_expires = datetime.now().timestamp() + result.get('expire', 7200) - 60
                return self.access_token
            else:
                print(f"❌ Failed to get access token: {result}")
                return None
        except Exception as exc:
            print(f"❌ Exception getting access token: {exc}")
            return None

    # ------------------------------------------------------------------
    # Headers + URL builders used by every other mixin
    # ------------------------------------------------------------------

    def _headers(self):
        """Get request headers with auth token."""
        token = self.get_access_token()
        if not token:
            raise Exception("Failed to get access token")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _auth_header(self):
        """Get auth header only (for multipart requests)."""
        token = self.get_access_token()
        if not token:
            raise Exception("Failed to get access token")
        return {"Authorization": f"Bearer {token}"}

    def _base_url(self):
        """Get base URL for bitable API."""
        feishu_cfg = self.config.get('feishu', self.config)
        base_id = feishu_cfg.get('base_id')
        table_id = feishu_cfg.get('table_id')
        return f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_id}/tables/{table_id}"
