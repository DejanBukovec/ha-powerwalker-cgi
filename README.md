# PowerWalker (BlueWalker) VFI CGI Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
![Maintainer](https://img.shields.io/badge/maintainer-DejanBukovec-blue.svg?style=for-the-badge)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-blue.svg?style=for-the-badge)
![Version](https://img.shields.io/github/v/release/DejanBukovec/ha-powerwalker-cgi?style=for-the-badge)

Monitor and control **PowerWalker (BlueWalker) VFI** UPS units directly from Home Assistant — without NUT or SNMP.

This integration communicates directly with the **10120505 SNMP/Network Manager card** via its native CGI endpoints, providing fast, stable, bidirectional control over HTTP/HTTPS.

---

## Features

### Sensors
| Sensor | Unit | Description |
|--------|------|-------------|
| Status Mode | — | Current UPS mode: Line, Battery, Bypass, etc. |
| Internal Temperature | °C | UPS internal temperature |
| Input Voltage | V | Mains input voltage |
| Input Frequency | Hz | Mains input frequency |
| Output Voltage | V | UPS output voltage |
| Output Frequency | Hz | UPS output frequency |
| Output Current | A | Output current draw |
| Output Active Power | W | Calculated output power (V × I) |
| Load Level | % | Current load as percentage of UPS capacity |
| Battery Voltage | V | Battery pack voltage |
| Battery Capacity | % | Remaining battery charge |
| Remaining Backup Time | min | Estimated runtime on battery |

### Switches
| Switch | Description |
|--------|-------------|
| System Power | Toggle UPS output on/off |
| Alarm Control | Enable or mute the UPS beeper |

### Buttons
| Button | Description |
|--------|-------------|
| 10-Second Test | Initiate a quick 10-second battery self-test |
| Deep Discharge Test | Run a full deep discharge battery test |
| Cancel Test | Abort any active battery test |

---

## Requirements

- Home Assistant 2024.1 or newer
- PowerWalker / BlueWalker VFI UPS with the **10120505 SNMP/Network Manager card**
- The UPS card must be reachable on your network (port 80 HTTP or 443 HTTPS)

---

## Installation

### Method 1: HACS (Recommended)
1. Open **HACS** in Home Assistant.
2. Go to **Integrations**.
3. Click the three dots (⋮) in the top right → **Custom repositories**.
4. Add `https://github.com/DejanBukovec/ha-powerwalker-cgi` as an **Integration**.
5. Find **PowerWalker CGI** and click **Download**.
6. **Restart Home Assistant.**

### Method 2: Manual
1. Download this repository as a ZIP and extract it.
2. Copy the `custom_components/powerwalker_cgi` folder to your HA `config/custom_components/` directory.
3. **Restart Home Assistant.**

---

## Configuration

1. Go to **Settings → Devices & Services → + Add Integration**.
2. Search for **PowerWalker CGI**.
3. Fill in the form:

| Field | Description | Default |
|-------|-------------|---------|
| Host | IP address of the SNMP card | — |
| Use HTTPS | Enable for HTTPS connections | Off |
| Port | Network port | 80 / 443 |
| Password | Web UI password (if set) | — |
| Scan Interval | Polling frequency in seconds | 30 |

> You can change these settings later via **Settings → Devices & Services → PowerWalker CGI → Configure**.

---

## Technical Notes

### Communication
The integration polls two unauthenticated CGI endpoints on every scan interval — a single coordinated fetch shared by all entities:

| Endpoint | Purpose | Auth required |
|----------|---------|---------------|
| `GET /cgi-bin/realInfo.cgi` | All sensor values | No |
| `GET /cgi-bin/getControl.cgi` | Switch states | No |
| `GET /cgi-bin/rtControl.cgi` | Send commands | Yes (password CGI) |

Write commands (switches, buttons) use a two-step session: a password handshake followed immediately by the command, both over the same persistent TCP connection.

### Polling Rate
The minimum recommended scan interval is **10 seconds**. The SNMP card firmware refreshes its data at approximately this rate, so polling faster returns stale values and adds unnecessary load to the legacy hardware.

### Output Active Power
The firmware does not provide a reliable active power reading for the VFI 2000 single-phase model. Power is instead calculated as **Output Voltage × Output Current**, which closely matches the true apparent power at near-unity power factor loads.

### Safety Warning
The **System Power** switch controls the UPS output directly. Turning it off will cut power to all connected equipment immediately.

---

## Tested Hardware

| Device | Firmware | Status |
|--------|----------|--------|
| PowerWalker VFI 2000 LCD | SNMP Web Pro v1.1 (card 10120505) | ✅ Working |

If you have successfully tested this integration with other PowerWalker/BlueWalker models, please open an issue to have your device added to this list.

---

## Credits

Developed by [@DejanBukovec](https://github.com/DejanBukovec) for the PowerWalker VFI 2000 LCD with Legacy SNMP Manager card.