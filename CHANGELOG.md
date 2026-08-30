# Changelog

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
