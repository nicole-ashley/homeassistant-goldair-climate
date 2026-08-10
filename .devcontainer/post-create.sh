#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

pip install --upgrade pip
pip install -r requirements-dev.txt

# A config dir so `hass -c ./config` can run the integration for manual testing.
mkdir -p config/custom_components
ln -sfn ../../custom_components/goldair_climate config/custom_components/goldair_climate
if [ ! -f config/configuration.yaml ]; then
  cat > config/configuration.yaml <<'YAML'
logger:
  default: warning
  logs:
    custom_components.goldair_climate: debug

# Add a device here to test without the UI, or uncomment default_config for the UI.
# goldair_climate:
#   - name: Test heater
#     host: 1.2.3.4
#     device_id: <device id>
#     local_key: <local key>
YAML
fi

echo
echo "Ready. pytest / black . / isort . ; hass -c ./config to run HA on :8123"
