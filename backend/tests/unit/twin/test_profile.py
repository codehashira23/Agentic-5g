"""
C040: Unit tests for NFType, NFStatus, Region, and NFProfile.
Pure domain — no database, no HTTP, no frameworks.
"""
import pytest
from app.domain.twin.profile import NFProfile, NFStatus, NFType, Region
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# NFType
# ---------------------------------------------------------------------------
class TestNFType:
    def test_all_13_types_exist(self) -> None:
        expected = {
            "UE", "gNB", "AMF", "SMF", "UPF",
            "NRF", "UDM", "PCF", "NWDAF", "NEF",
            "DCF", "AF", "Edge",
        }
        actual = {t.value for t in NFType}
        assert actual == expected

    def test_type_is_string_comparable(self) -> None:
        assert NFType.AMF == "AMF"
        assert NFType.NWDAF == "NWDAF"

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError):
            NFType("INVALID_NF")


# ---------------------------------------------------------------------------
# NFStatus
# ---------------------------------------------------------------------------
class TestNFStatus:
    def test_all_5_statuses_exist(self) -> None:
        expected = {"ACTIVE", "DEGRADED", "FAILED", "RECOVERING", "STANDBY"}
        assert {s.value for s in NFStatus} == expected

    def test_status_is_string_comparable(self) -> None:
        assert NFStatus.ACTIVE == "ACTIVE"
        assert NFStatus.FAILED == "FAILED"


# ---------------------------------------------------------------------------
# Region
# ---------------------------------------------------------------------------
class TestRegion:
    def test_all_regions_exist(self) -> None:
        expected = {"Delhi", "Mumbai", "Bengaluru", "Core"}
        assert {r.value for r in Region} == expected


# ---------------------------------------------------------------------------
# NFProfile — construction
# ---------------------------------------------------------------------------
class TestNFProfileConstruction:
    def test_minimal_profile(self) -> None:
        p = NFProfile(id="amf_core_1", type=NFType.AMF, region=Region.CORE)
        assert p.id == "amf_core_1"
        assert p.type == NFType.AMF
        assert p.region == Region.CORE

    def test_default_status_is_active(self) -> None:
        p = NFProfile(id="smf_delhi_1", type=NFType.SMF, region=Region.DELHI)
        assert p.status == NFStatus.ACTIVE

    def test_default_services_is_empty(self) -> None:
        p = NFProfile(id="upf_mumbai_1", type=NFType.UPF, region=Region.MUMBAI)
        assert p.services == ()

    def test_profile_with_services(self) -> None:
        p = NFProfile(
            id="nrf_core_1",
            type=NFType.NRF,
            region=Region.CORE,
            services=("nrf.register", "nrf.discover", "nrf.list"),
        )
        assert "nrf.register" in p.services
        assert len(p.services) == 3

    def test_missing_required_fields_raises(self) -> None:
        with pytest.raises(ValidationError):
            NFProfile(id="bad")  # type: ignore[call-arg]  # missing type + region


# ---------------------------------------------------------------------------
# NFProfile — immutability
# ---------------------------------------------------------------------------
class TestNFProfileImmutability:
    def test_profile_is_immutable(self) -> None:
        p = NFProfile(id="nrf_core_1", type=NFType.NRF, region=Region.CORE)
        with pytest.raises(ValidationError):
            p.id = "changed"  # type: ignore[misc]  # must raise — frozen model

    def test_with_status_returns_new_object(self) -> None:
        p = NFProfile(id="nrf_core_1", type=NFType.NRF, region=Region.CORE)
        p2 = p.with_status(NFStatus.FAILED)
        # original unchanged
        assert p.status == NFStatus.ACTIVE
        # new object has new status
        assert p2.status == NFStatus.FAILED
        # different object
        assert p is not p2

    def test_with_status_preserves_other_fields(self) -> None:
        p = NFProfile(
            id="nrf_core_1",
            type=NFType.NRF,
            region=Region.CORE,
            services=("nrf.register",),
        )
        p2 = p.with_status(NFStatus.RECOVERING)
        assert p2.id == p.id
        assert p2.type == p.type
        assert p2.region == p.region
        assert p2.services == p.services


# ---------------------------------------------------------------------------
# NFProfile — is_healthy helper
# ---------------------------------------------------------------------------
class TestNFProfileIsHealthy:
    def test_active_is_healthy(self) -> None:
        p = NFProfile(id="upf_1", type=NFType.UPF, region=Region.DELHI)
        assert p.is_healthy() is True

    def test_standby_is_healthy(self) -> None:
        p = NFProfile(
            id="nrf_standby_1",
            type=NFType.NRF,
            region=Region.CORE,
            status=NFStatus.STANDBY,
        )
        assert p.is_healthy() is True

    def test_failed_is_not_healthy(self) -> None:
        p = NFProfile(
            id="upf_1",
            type=NFType.UPF,
            region=Region.DELHI,
            status=NFStatus.FAILED,
        )
        assert p.is_healthy() is False

    def test_degraded_is_not_healthy(self) -> None:
        p = NFProfile(
            id="upf_1",
            type=NFType.UPF,
            region=Region.DELHI,
            status=NFStatus.DEGRADED,
        )
        assert p.is_healthy() is False

    def test_recovering_is_not_healthy(self) -> None:
        p = NFProfile(
            id="upf_1",
            type=NFType.UPF,
            region=Region.DELHI,
            status=NFStatus.RECOVERING,
        )
        assert p.is_healthy() is False
