# Changelog

## 0.1.4

- Retry transient UDP connection failures for mandatory status reads
- Keep write commands single-shot so start, stop, and setting changes are never duplicated
- Document that the MQTT add-on must remain stopped while the native integration is active

## 0.1.3

- Add the combined Home Assistant/Aduro icon and logo from Aduro2mqttAddon
- Enable HACS brand validation for the bundled local assets

## 0.1.2

- Integrate Off, Auto, and Heat into the climate operating modes
- Confirm the requested regulation mode before starting a stopped stove
- Track asynchronous start/stop pulses with repeated status refreshes
- Remove the separate heating switch and clean up replaced pre-1.0 registry entries
- Report an enabled stove with zero current power as idle instead of off

## 0.1.1

- Move 10/50/100% fixed power into the climate entity as Eco/Comfort/Boost presets
- Automatically enter fixed-power heating when a preset is selected
- Remove the separate fixed-power select and exhaust-speed sensor
- Disable shaft temperature and oxygen sensors by default

## 0.1.0

- Native UI config flow with live stove validation and reconfiguration
- Local NBE/UDP polling without MQTT
- Climate, heating switch, fixed-power select, forced-auger number, and sensors
- German and English translations
- Serialized pyduro access and strict response validation
- Immediate post-command refresh and read-back verification
- Partial-data fallback for firmware-dependent sections
