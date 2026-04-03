# PowerWalker (BlueWalker) VFI CGI Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
![Maintainer](https://img.shields.io/badge/maintainer-User-blue.svg?style=for-the-badge)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-blue.svg?style=for-the-badge)

This custom integration allows you to monitor and control **PowerWalker (BlueWalker) VFI** UPS units (specifically those using the **10120505 SNMP/Network Manager card**) directly through Home Assistant. 

By bypassing the often unreliable NUT or SNMP protocols, this integration uses the card's native internal CGI endpoints for high-speed, stable, bidirectional communication.

---

## 🚀 Features

### 📊 Real-time Monitoring (Sensors)
The integration automatically creates sensors for all data points exposed by the card:
- **UPS Status:** Current mode (Line, Battery, Bypass, etc.).
- **Electrical Metrics:** Input/Output Voltage, Input/Output Frequency, and Output Current.
- **Battery Health:** Voltage, Capacity (%), and Internal Temperature.
- **Load Statistics:** Load Level (%) and Active Output Power (W).
- **Diagnostics:** Remaining Backup Time, Warning Status, and Fault Types.

### ⚙️ Controls (Switches & Buttons)
Take action directly from your Home Assistant Dashboard:
- **System Power Switch:** Software-controlled UPS Output Toggle (On/Off).
- **Alarm Control Switch:** Enable or Disable (Mute) the UPS beeper.
- **Maintenance Buttons:** - 10-Second Self Test
    - Deep Discharge Test
    - Cancel Active Test

---

## 🛠 Installation

### Method 1: HACS (Recommended)
1. Open **HACS** in Home Assistant.
2. Go to **Integrations**.
3. Click the three dots (top right) -> **Custom repositories**.
4. Paste your GitHub Repository URL.
5. Select `Integration` as the category and click **Add**.
6. Find "PowerWalker CGI" in the list and click **Download**.
7. **Restart Home Assistant.**

### Method 2: Manual
1. Download this repository as a ZIP.
2. Extract and copy the `custom_components/powerwalker_cgi` folder into your HA `config/custom_components/` directory.
3. **Restart Home Assistant.**

---

## ⚙️ Configuration

1. Navigate to **Settings** -> **Devices & Services**.
2. Click **+ Add Integration**.
3. Search for **PowerWalker CGI**.
4. Fill in the configuration form:
   - **Host:** The IP address of your SNMP Card.
   - **Username:** Typically `admin`.
   - **Password:** Your web UI password (if set).
   - **Scan Interval:** Polling frequency in seconds (30s recommended).

---

## 📝 Technical Overview

This integration maps internal CGI responses into Home Assistant entities using the following logic:

| Data Point | CGI Endpoint | Mapping Index |
|------------|--------------|---------------|
| Status     | `realInfo.cgi` | 0             |
| Voltages   | `realInfo.cgi` | 13, 16        |
| Commands   | `rtControl.cgi`| name/params   |
| Config     | `config.cgi`   | name/params   |

---

## ⚠️ Important Notes
- **Network Access:** Ensure the UPS card is reachable via port 80 (HTTP).
- **Polling Rate:** Polling faster than 10 seconds is possible but may strain the legacy hardware on the SNMP card.
- **Safety:** Be cautious with the "System Power" switch, as it can shut down your connected equipment.

---

## Credits
Custom integration developed for PowerWalker VFI 2000 LCD UPS with Legacy SNMP Manager.
