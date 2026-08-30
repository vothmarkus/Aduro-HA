# Aduro Hybrid für Home Assistant

Native Home-Assistant-Integration für den **Aduro H2 Hybridofen** über das lokale NBE/UDP-Protokoll. Sie übernimmt die Funktionen des [Aduro2MQTT-Add-ons](https://github.com/vothmarkus/Aduro2mqttAddon), benötigt aber weder MQTT noch ein zusätzliches Add-on.

[English documentation](README.en.md)

## Funktionen in v0.1.2

| Home-Assistant-Entität | Funktion |
|---|---|
| Klima | Ein/Aus, Ist- und Solltemperatur, Temperatur- oder Festleistungsbetrieb und drei integrierte Heizstufen |
| Zahl „Förderer erzwingen“ | Förderschnecke für 0 bis 120 Sekunden ansteuern |
| Statussensor | Übersetzter Betriebszustand inklusive Fehler- und Türzuständen |
| Messsensoren | Raum- und Rauchgastemperatur, Leistung, CO und Gesamtbetriebszeit |
| Optionale Sensoren | Schachttemperatur und Sauerstoff; standardmäßig deaktiviert |
| Diagnosesensoren | Rohwerte für Status, Unterstatus und Statusdauer; standardmäßig deaktiviert |

Die Klima-Modi steuern jetzt den vollständigen Ofenbetrieb:

- **Aus**: Ofen stoppen, `misc.stop = 1`
- **Auto**: temperaturgeregelter Betrieb, fest `regulation.operation_mode = 1`
- **Heizen**: Festleistungsbetrieb, `regulation.operation_mode = 0`

Beim Wechsel von **Aus** zu **Auto** oder **Heizen** wird zuerst der gewünschte Regelungsmodus bestätigt und erst danach der Ofen mit `misc.start = 1` gestartet. **Aus** ändert den gespeicherten Regelungsmodus nicht. Ein späteres Einschalten stellt deshalb den zuletzt verwendeten Modus wieder her.

Im Modus **Heizen** stehen direkt in der Klimakarte drei Voreinstellungen zur Verfügung:

- **Eco**: 10 %
- **Komfort**: 50 %
- **Boost**: 100 %

Die Auswahl einer dieser Stufen wechselt bei Bedarf automatisch von **Auto** zu **Heizen**. Im Automatikbetrieb wird die gespeicherte Festleistung nicht verwendet und die Voreinstellung als „Ohne“ angezeigt.

Beim Aktualisieren von v0.1.0 oder v0.1.1 entfernt die Integration die ersetzten Registry-Einträge für den alten Heizbetrieb-Schalter, die separate Festleistungsauswahl und das Abgasgebläse automatisch.

## Warum die native Integration zuverlässiger reagiert

- NBE-Zugriffe werden serialisiert, weil `pyduro` einen festen lokalen UDP-Port verwendet und nicht threadsicher ist.
- Jede Antwort wird auf Seriennummer, Funktion, Sequenznummer und NBE-Status geprüft.
- Home Assistant übernimmt keine optimistischen Schaltzustände.
- Nach jedem Befehl wird der Zustand unmittelbar erneut vom Ofen gelesen.
- Start und Stopp werden als Impulsbefehle behandelt und mit zwei schnellen Statusabfragen verfolgt, ohne bei einer langsamen Ofenreaktion einen falschen Zustand anzuzeigen.
- Solltemperatur, Betriebsmodus und feste Leistung werden durch Rücklesen bestätigt.
- Nicht unterstützte Zusatzwerte legen nicht das gesamte Gerät lahm; nur die betroffenen Entitäten werden vorübergehend als nicht verfügbar markiert.
- Kürzere oder längere Statusantworten werden anhand der tatsächlich vorhandenen Felder verarbeitet, statt die komplette Aktualisierung abzubrechen.

## Installation mit HACS

1. HACS öffnen und **Integrationen** auswählen.
2. Über das Menü **Benutzerdefinierte Repositories** öffnen.
3. `https://github.com/vothmarkus/Aduro-HA` als Typ **Integration** hinzufügen.
4. **Aduro Hybrid** installieren und Home Assistant neu starten.
5. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **Aduro Hybrid** suchen.
6. IP-Adresse, Seriennummer, PIN und Abfrageintervall eingeben.

Die Verbindung wird vor dem Speichern direkt am Ofen geprüft. Empfohlen sind **30 Sekunden** Abfrageintervall; zulässig sind 15 bis 300 Sekunden.

## Manuelle Installation

Den Ordner `custom_components/aduro` in den gleichnamigen Ordner unterhalb des Home-Assistant-Konfigurationsverzeichnisses kopieren:

```text
<config>/custom_components/aduro
```

Anschließend Home Assistant neu starten und die Integration über die Benutzeroberfläche hinzufügen.

## Wechsel vom Add-on

1. Das Aduro2MQTT-Add-on stoppen, aber zunächst installiert lassen.
2. Die native Integration einrichten und ihre Entitäten testen.
3. Automationen und Dashboards auf die neuen Entitäten umstellen.
4. Danach das Add-on entfernen.

Die alten MQTT-Discovery-Nachrichten sind retained und können deshalb im Broker erhalten bleiben. Falls das alte MQTT-Gerät erneut erscheint, die retained Konfigurationen mit einem MQTT-Werkzeug löschen. Sie liegen nach der Standardkonfiguration unter `homeassistant/<Plattform>/aduro_h2_<Objekt>/config`. Vorher prüfen, ob `device_id` oder `discovery_prefix` im Add-on abweichend eingestellt waren.

## Hinweise

- Getestete Zielplattform ist der Aduro H2. Andere NBE-kompatible Aduro-Hybridöfen können funktionieren, sind in v0.1 aber noch nicht bestätigt.
- Einzelne Sensoren können je nach Firmware fehlen und werden dann automatisch als nicht verfügbar angezeigt.
- Der Ofen muss aus dem Home-Assistant-Netz lokal per UDP erreichbar sein. Das NBE-Ziel ist Port `8483`; `pyduro` verwendet lokal Port `1901`.
- Verbindungsdaten lassen sich später über **Neu konfigurieren** ändern und werden erneut geprüft.

## Entwicklung und Tests

```bash
python -m pip install pyduro==3.2.1 pytest ruff
ruff check custom_components tests
pytest -q
```

## Basis und Danksagung

Die Kommunikation basiert auf [clementprevot/pyduro](https://github.com/clementprevot/pyduro). Die bewährten Entitäten und Zustandszuordnungen stammen aus dem eigenen [Aduro2MQTT-Add-on](https://github.com/vothmarkus/Aduro2mqttAddon) und dessen Upstream [Johnny100dk/aduro2mqtt](https://github.com/Johnny100dk/aduro2mqtt).

Lizenz: [MIT](LICENSE)
