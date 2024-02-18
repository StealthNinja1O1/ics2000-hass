"""Platform for light integration."""
from __future__ import annotations

import logging
import time
import threading
import voluptuous as vol

from typing import Any
from ics2000.Core import Hub
from ics2000.Devices import Sunshade
from enum import Enum

# Import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.components.cover import CoverEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_PASSWORD, CONF_MAC, CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)


def repeat(tries: int, sleep: int, callable_function, **kwargs):
    _LOGGER.info(f'Function repeat called in thread {threading.current_thread().name}')
    qualname = getattr(callable_function, '__qualname__')
    for i in range(0, tries):
        _LOGGER.info(f'Try {i + 1} of {tries} on {qualname}')
        callable_function(**kwargs)
        time.sleep(sleep if i != tries - 1 else 0)


# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MAC): cv.string,
    vol.Required(CONF_EMAIL): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
})


def setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        add_entities: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the ICS2000 Light platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.
    # Setup connection with devices/cloud
    hub = Hub(
        config[CONF_MAC],
        config[CONF_EMAIL],
        config[CONF_PASSWORD]
    )

    # Verify that passed in configuration works
    if not hub.connected:
        _LOGGER.error("Could not connect to ICS2000 hub")
        return

    # Add devices
    add_entities(KlikAanKlikUitDevice(
        device=device
    ) for device in hub.devices if Sunshade == type(device))



class KlikAanKlikUitAction(Enum):
    OPEN = 'open'
    CLOSE = 'close'
    STOP = 'stop'


class KlikAanKlikUitThread(threading.Thread):

    def __init__(self, action: KlikAanKlikUitAction, device_id, target, kwargs):
        super().__init__(
            # Thread name may be 15 characters max
            name=f'kaku{action.value}{device_id}',
            target=target,
            kwargs=kwargs
        )

    @staticmethod
    def has_running_threads(device_id) -> bool:
        running_threads = [thread.name for thread in threading.enumerate() if thread.name in [
            f'kaku{KlikAanKlikUitAction.TURN_ON.value}{device_id}',
            f'kaku{KlikAanKlikUitAction.DIM.value}{device_id}',
            f'kaku{KlikAanKlikUitAction.TURN_OFF.value}{device_id}'
        ]]
        if running_threads:
            _LOGGER.info(f'Running KlikAanKlikUit threads: {",".join(running_threads)}')
            return True
        return False


class KlikAanKlikUitDevice(CoverEntity):
    """Representation of a KlikAanKlikUit device"""
    __attr_is_closed = None
    _attr_is_closed = None

    def __init__(self, device: Sunshade) -> None:
        """Initialize a KlikAanKlikUitDevice"""
        self._name = device.name
        self._id = device.id
        self._hub = device.hub

    @property
    def name(self) -> str:
        """Return the display name of this sunshade."""
        return self._name
    
    def open_cover(self, **kwargs: Any):
        """Open the cover."""
        KlikAanKlikUitThread(
            action=KlikAanKlikUitAction.OPEN,
            device_id=self._id,
            target=repeat,
            kwargs={
                'tries': 1,
                'sleep': 1,
                'callable_function': self._hub.open,
                'entity': self._id
            }
        ).start()


    def close_cover(self, **kwargs: Any):
        """Close the cover."""
        KlikAanKlikUitThread(
            action=KlikAanKlikUitAction.CLOSE,
            device_id=self._id,
            target=repeat,
            kwargs={
                'tries': 1,
                'sleep': 1,
                'callable_function': self._hub.close,
                'entity': self._id
            }
        ).start()

    def stop_cover(self, **kwargs: Any):
        """Stop the cover."""
        KlikAanKlikUitThread(
            action=KlikAanKlikUitAction.STOP,
            device_id=self._id,
            target=repeat,
            kwargs={
                'tries': 1,
                'sleep': 1,
                'callable_function': self._hub.stop,
                'entity': self._id
            }
        ).start()

    def update(self) -> None:
        pass
