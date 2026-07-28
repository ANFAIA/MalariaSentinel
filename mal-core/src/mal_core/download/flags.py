from typing import TypedDict, Any

class DownloadFlags(TypedDict, total=False):
    aoi: str
    datasets: str
    years: str
    months: str

DOWNLOAD_FLAGS_SCHEMA: dict[str, dict[str, Any]] = {
    "aoi": {"type": str, "default": "ghana", "help": "AOI slug"},
    "datasets": {"type": str, "default": "", "help": "Comma-separated dataset names"},
    "years": {"type": str, "default": "", "help": "Comma-separated years"},
    "months": {"type": str, "default": "", "help": "Comma-separated months"},
}
