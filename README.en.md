# Aduro Hybrid for Home Assistant

Native Home Assistant integration for the **Aduro H2 hybrid stove** over the local NBE/UDP protocol. It provides the controls from the [Aduro2MQTT add-on](https://github.com/vothmarkus/Aduro2mqttAddon) without requiring MQTT or a separate add-on.

## Features in v0.1.3

- Climate entity for power, current/target temperature, operating mode, and three heat levels
- Forced auger run from 0 to 120 seconds
- Translated stove state
- Room and smoke temperature, power, CO, and total-hours sensors
- Shaft temperature and oxygen sensors, disabled by default
- Disabled-by-default raw state diagnostic sensors

The climate modes now control the complete stove operation: **Off** sends `misc.stop = 1`, **Auto** uses temperature mode (`regulation.operation_mode = 1`), and **Heat** uses fixed-power mode (`0`). When starting from Off, the integration confirms the selected regulation mode before sending `misc.start = 1`. Stopping preserves the stored regulation mode.

In **Heat** mode, the climate card provides **Eco** (10%), **Comfort** (50%), and **Boost** (100%) presets. Selecting a preset automatically switches from Auto to Heat when needed. In Auto, the stored fixed-power value is inactive and the preset is shown as “None”.

When upgrading from v0.1.0 or v0.1.1, the integration automatically removes the replaced registry entries for the old heating switch, fixed-power select, and exhaust-speed sensor.

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
