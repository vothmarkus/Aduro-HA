# Aduro Hybrid for Home Assistant

Native Home Assistant integration for the **Aduro H2 hybrid stove** over the local NBE/UDP protocol. It provides the controls from the [Aduro2MQTT add-on](https://github.com/vothmarkus/Aduro2mqttAddon) without requiring MQTT or a separate add-on.

## Features in v0.1.0

- Climate entity for current/target temperature and temperature/fixed-power mode
- Heating switch for start and stop
- Fixed power selection: 10%, 50%, or 100%
- Forced auger run from 0 to 120 seconds
- Translated stove state
- Room, smoke, and shaft temperature, oxygen, power, exhaust, CO, and total-hours sensors
- Disabled-by-default raw state diagnostic sensors

Climate **Auto** is the Aduro H2 temperature mode and always writes `regulation.operation_mode = 1`. **Heat** selects fixed-power mode (`0`). Start and stop remain on the separate heating switch, matching the proven add-on behavior.

Commands are not optimistic. The integration validates the direct NBE reply, immediately refreshes the stove, and read-verifies persistent settings. It also validates response serial, function, sequence, and status fields.

## HACS installation

1. Open HACS and select **Integrations**.
2. Add `https://github.com/vothmarkus/Aduro-HA` as a custom **Integration** repository.
3. Install **Aduro Hybrid** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration** and select **Aduro Hybrid**.
5. Enter the stove's local IP/hostname, serial number, PIN, and polling interval.

The setup flow tests the credentials directly with the stove before saving. The recommended polling interval is 30 seconds.

## Migrating from the add-on

Stop the Aduro2MQTT add-on before testing this integration, keep it installed for rollback, and migrate automations after confirming the native entities. Retained MQTT Discovery topics can keep the old MQTT device visible; clear the matching `homeassistant/<platform>/aduro_h2_<object>/config` topics if needed.

## Compatibility

Version 0.1 targets the Aduro H2. Other NBE-compatible Aduro hybrid stoves may work but are not yet verified. Sensor availability depends on the controller firmware.

Communication uses [clementprevot/pyduro](https://github.com/clementprevot/pyduro). Entity behavior is based on [Aduro2mqttAddon](https://github.com/vothmarkus/Aduro2mqttAddon) and [Johnny100dk/aduro2mqtt](https://github.com/Johnny100dk/aduro2mqtt).

License: [MIT](LICENSE)
