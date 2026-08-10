from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_SWING_MODE,
    SWING_HORIZONTAL,
    SWING_OFF,
)
from homeassistant.const import ATTR_TEMPERATURE

ATTR_TARGET_TEMPERATURE = "target_temperature"
ATTR_POWER_MODE = "power_mode"
ATTR_TIMER = "timer"

# dps 4 selects whether the heat level (dps 5) is chosen by the user or by the
# appliance. The panel and remote reach the latter by cycling past High.
ATTR_POWER_MODE_USER = "normal"
ATTR_POWER_MODE_AUTO = "auto"

PRESET_AUTO = "Auto"
PRESET_FAN = "Fan"
PRESET_LOW = "Low"
PRESET_HIGH = "High"

PROPERTY_TO_DPS_ID = {
    ATTR_HVAC_MODE: "1",
    ATTR_TARGET_TEMPERATURE: "2",
    ATTR_TEMPERATURE: "3",
    ATTR_POWER_MODE: "4",
    ATTR_PRESET_MODE: "5",
    ATTR_SWING_MODE: "8",
    ATTR_TIMER: "19",
}

HVAC_MODE_TO_DPS_MODE = {HVACMode.OFF: False, HVACMode.HEAT: True}

# Auto is deliberately absent: it lives on dps 4, not dps 5, and the entity
# layer folds both into a single preset.
PRESET_MODE_TO_DPS_LEVEL = {
    PRESET_FAN: "level_0",
    PRESET_LOW: "level_1",
    PRESET_HIGH: "level_2",
}

SWING_MODE_TO_DPS_MODE = {SWING_OFF: False, SWING_HORIZONTAL: True}
