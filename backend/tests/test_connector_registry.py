import pytest
from app.schemas.connector import PlatformType
from app.services.connectors.ashby import AshbyConnector
from app.services.connectors.generic_browser import GenericBrowserConnector
from app.services.connectors.greenhouse import GreenhouseConnector
from app.services.connectors.lever import LeverConnector
from app.services.connectors.registry import ConnectorRegistry, get_connector_registry


def test_connector_registry_registration_and_retrieval():
    registry = ConnectorRegistry()
    gh = GreenhouseConnector()
    lev = LeverConnector()
    ashby = AshbyConnector()
    browser = GenericBrowserConnector()

    registry.register(gh)
    registry.register(lev)
    registry.register(ashby)
    registry.register(browser)

    assert registry.get_connector(PlatformType.GREENHOUSE) is gh
    assert registry.get_connector(PlatformType.LEVER) is lev
    assert registry.get_connector(PlatformType.ASHBY) is ashby
    assert registry.get_connector(PlatformType.BROWSER) is browser
    # Unregistered platform falls back to browser
    assert registry.get_connector(PlatformType.LINKEDIN) is browser
    assert registry.get_connector(PlatformType.UNKNOWN) is browser


def test_connector_registry_duplicate_registration_error():
    registry = ConnectorRegistry()
    gh1 = GreenhouseConnector()
    gh2 = GreenhouseConnector()

    registry.register(gh1)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(gh2)


def test_connector_registry_invalid_type_rejection():
    registry = ConnectorRegistry()
    with pytest.raises(TypeError, match="Expected PlatformConnector"):
        registry.register("not_a_connector")  # type: ignore


def test_connector_registry_unregister_and_list():
    registry = ConnectorRegistry()
    gh = GreenhouseConnector()
    registry.register(gh)

    assert len(registry.list_connectors()) == 1
    infos = registry.list_connector_infos()
    assert len(infos) == 1
    assert infos[0].name == "Greenhouse ATS Connector"

    unregistered = registry.unregister(PlatformType.GREENHOUSE)
    assert unregistered is gh
    assert len(registry.list_connectors()) == 0


def test_default_singleton_registry():
    registry = get_connector_registry()
    assert len(registry.list_connectors()) >= 4
    assert registry.get_connector(PlatformType.GREENHOUSE) is not None
    assert registry.get_connector(PlatformType.LEVER) is not None
