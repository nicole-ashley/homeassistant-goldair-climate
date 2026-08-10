from datetime import timedelta

DOMAIN = "goldair_climate"

CONF_DEVICE_ID = "device_id"
CONF_LOCAL_KEY = "local_key"
CONF_TYPE = "type"
CONF_TYPE_AUTO = "auto"
CONF_TYPE_GPPH_HEATER = "heater"
CONF_TYPE_DEHUMIDIFIER = "dehumidifier"
CONF_TYPE_FAN = "fan"
CONF_TYPE_GPCV_HEATER = "gpcv_heater"
CONF_TYPE_GECO_HEATER = "geco_heater"
CONF_CLIMATE = "climate"
CONF_DISPLAY_LIGHT = "display_light"
CONF_CHILD_LOCK = "child_lock"

# Tried in order until one works, then pinned (see GoldairTuyaDevice).
# 3.2 is deliberately excluded: tinytuya's set_version(3.2) eagerly calls
# detect_available_dps(), which does live network I/O and blocks until it times
# out, so rotating onto it against an unreachable device stalls the executor.
API_PROTOCOL_VERSIONS = [3.3, 3.4, 3.5, 3.1]
SCAN_INTERVAL = timedelta(seconds=30)
