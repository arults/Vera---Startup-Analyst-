from __future__ import annotations

from dataclasses import dataclass
from .sources import PLATFORM_HOSTS, PAGE_TYPES, SourceCapture, validate_capture

@dataclass(frozen=True)
class AdapterSpec:
    platform: str
    allowed_hosts: tuple[str,...]
    supported_page_types: tuple[str,...]
    public_only: bool = True

class BasePlatformAdapter:
    platform=""
    supported_page_types=("campaign","hosted_document","issuer_update","platform_portfolio","funded_listing","secondary_page")

    @classmethod
    def spec(cls) -> AdapterSpec:
        return AdapterSpec(cls.platform,tuple(sorted(PLATFORM_HOSTS[cls.platform])),tuple(cls.supported_page_types),True)

    @classmethod
    def validate_capture(cls,capture: SourceCapture) -> list[str]:
        errors=validate_capture(capture)
        if capture.platform!=cls.platform:
            errors.append("adapter_platform_mismatch")
        if capture.page_type not in cls.supported_page_types:
            errors.append("adapter_page_type_unsupported")
        return errors

class WefunderAdapter(BasePlatformAdapter):
    platform="wefunder"

class StartEngineAdapter(BasePlatformAdapter):
    platform="startengine"

class CrowdcubeAdapter(BasePlatformAdapter):
    platform="crowdcube"

class RepublicUSAdapter(BasePlatformAdapter):
    platform="republic_us"

class RepublicEuropeAdapter(BasePlatformAdapter):
    platform="republic_europe"

ADAPTERS={
    "wefunder":WefunderAdapter,
    "startengine":StartEngineAdapter,
    "crowdcube":CrowdcubeAdapter,
    "republic_us":RepublicUSAdapter,
    "republic_europe":RepublicEuropeAdapter,
}

def get_adapter(platform: str) -> type[BasePlatformAdapter]:
    try:
        return ADAPTERS[platform]
    except KeyError:
        raise ValueError("unsupported_platform")

def validate_adapter_registry() -> bool:
    return set(ADAPTERS)==set(PLATFORM_HOSTS) and all(set(cls.supported_page_types)<=PAGE_TYPES for cls in ADAPTERS.values())
