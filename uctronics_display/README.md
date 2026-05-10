# UCTRONICS RM0004 Display — Home Assistant Add-on

Python-native driver voor de **UCTRONICS RM0004 Pi Rack Pro** op
**Raspberry Pi 5** met **Home Assistant OS**.

Toont roterende stats op het 160×80 ST7735 LCD en ondersteunt de
power-button via gpiod (Pi 5 compatibel).

---

## Vereisten

| Onderdeel | Waarde |
|-----------|--------|
| Hardware | Raspberry Pi 5 |
| Rack | UCTRONICS RM0004 Pi Rack Pro |
| HAOS | 13+ (aarch64) |
| I²C | Ingeschakeld — `/dev/i2c-1` aanwezig |
| GPIO | `/dev/gpiochip4` aanwezig (Pi 5 standaard) |

### I²C inschakelen in HAOS

Voeg toe aan `/mnt/boot/config.txt`:
```
dtparam=i2c_arm=on
dtparam=i2c_arm_baudrate=400000
```

En maak `/mnt/boot/CONFIG/modules/rpi-i2c.conf` aan met inhoud:
```
i2c-dev
```

Reboot. Controleer: `ls /dev/i2c-*` → `/dev/i2c-1` moet zichtbaar zijn.

---

## Installatie

1. Ga in HA naar **Settings → Add-ons → Add-on Store**
2. Klik op de **⋮ menu** (rechtsboven) → **Repositories**
3. Voeg toe: `https://github.com/sammycolson/uctronics-rm0004-haos`
4. Zoek **"UCTRONICS RM0004 Display"** in de store en klik **Install**
5. Wacht tot de Docker image gebouwd is (~2–5 min op Pi 5)
6. Klik **Start**

---

## Display pagina's (rotatie elke 5 seconden)

| Pagina | Inhoud |
|--------|--------|
| 1 | IP-adres van `end0` |
| 2 | CPU gebruik % |
| 3 | RAM gebruik % + GB gebruikt/totaal |
| 4 | Disk gebruik % van `/` + GB |
| 5 | CPU temperatuur in °C |

Kleuren: groen (normaal) → geel (hoog) → rood (kritiek).

---

## Power-button

| Actie | Resultaat |
|-------|-----------|
| Korte druk (< 1.5 s) | Display aan/uit (DISPON/DISPOFF) |
| Lange druk (≥ 3 s) | HA host shutdown via Supervisor API |

GPIO: **BCM 4** = `gpiochip4` offset 4 (Pi 5).

---

## Troubleshooting

**Display blijft op boot-logo**
→ De I²C bridge op 0x18 is bereikbaar maar de init-sequentie wordt niet
verstuurd. Controleer de logs: `i2cdetect -y 1` moet adres `18` tonen.

**`/dev/i2c-1` niet gevonden**
→ I²C niet ingeschakeld in `config.txt`. Zie sectie "I²C inschakelen".

**Button werkt niet**
→ Controleer of `/dev/gpiochip4` bestaat: `ls /dev/gpiochip*`.
Op Pi 4 is dit `gpiochip0` — pas `CHIP` aan in `button.py` indien nodig.

**MADCTL / rotatie verkeerd**
→ Als beeld gespiegeld of gedraaid is, pas `_MADCTL_VAL` aan in `st7735.py`:
`0x70` (standaard), `0x00`, `0xA0`, `0xC0`, of `0x60`.

---

## Logs bekijken

In de add-on UI → **Log** tab, of via SSH:
```bash
ha addons logs local_uctronics_display
```
