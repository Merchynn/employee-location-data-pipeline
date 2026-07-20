from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

from .config import SourceSettings

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


def read_local_excel(path: Path, worksheet: str) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Excel file not found: {path}")
    return pd.read_excel(path, sheet_name=worksheet, dtype=object)


class SharePointExcelClient:
    def __init__(self, settings: SourceSettings, timeout_seconds: int = 120):
        self.settings = settings.sharepoint
        self.worksheet = settings.worksheet
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _required_env(name: str) -> str:
        value = os.getenv(name, "").strip()
        if not value:
            raise RuntimeError(f"Missing environment variable: {name}")
        return value

    def _token(self) -> str:
        try:
            import msal
        except ImportError as exc:
            raise RuntimeError("Install the project dependencies to use SharePoint extraction.") from exc
        tenant = self._required_env(self.settings.tenant_id_env)
        client_id = self._required_env(self.settings.client_id_env)
        secret = self._required_env(self.settings.client_secret_env)
        app = msal.ConfidentialClientApplication(
            client_id=client_id,
            authority=f"https://login.microsoftonline.com/{tenant}",
            client_credential=secret,
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        token = result.get("access_token")
        if not token:
            detail = result.get("error_description", "unknown error")
            raise RuntimeError(f"Unable to acquire Microsoft Graph token: {detail}")
        return str(token)

    def _resolve_site_id(self, token: str) -> str:
        fixed = os.getenv(self.settings.site_id_env, "").strip()
        if fixed:
            return fixed
        if not self.settings.site_hostname or not self.settings.site_path:
            raise RuntimeError("Configure site_hostname/site_path or SHAREPOINT_SITE_ID.")
        url = f"{GRAPH_BASE_URL}/sites/{self.settings.site_hostname}:/{self.settings.site_path}?$select=id"
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return str(response.json()["id"])

    def _download_url(self, site_id: str | None = None) -> str:
        if self.settings.share_url:
            encoded = base64.urlsafe_b64encode(self.settings.share_url.encode()).decode().rstrip("=")
            return f"{GRAPH_BASE_URL}/shares/u!{encoded}/driveItem/content"
        if not site_id or not self.settings.file_path:
            raise RuntimeError("Configure share_url or a SharePoint site and file_path.")
        path = quote(self.settings.file_path.strip("/"), safe="/")
        drive_id = os.getenv(self.settings.drive_id_env, "").strip()
        if drive_id:
            return f"{GRAPH_BASE_URL}/sites/{site_id}/drives/{drive_id}/root:/{path}:/content"
        return f"{GRAPH_BASE_URL}/sites/{site_id}/drive/root:/{path}:/content"

    def read(self) -> pd.DataFrame:
        token = self._token()
        site_id = None if self.settings.share_url else self._resolve_site_id(token)
        response = requests.get(
            self._download_url(site_id),
            headers={"Authorization": f"Bearer {token}"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return pd.read_excel(
            io.BytesIO(response.content),
            sheet_name=self.worksheet,
            dtype=object,
        )


def extract_dataframe(settings: SourceSettings) -> pd.DataFrame:
    if settings.mode == "local":
        return read_local_excel(settings.local_file, settings.worksheet)
    return SharePointExcelClient(settings).read()
