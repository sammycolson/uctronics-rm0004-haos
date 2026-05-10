# uctronics-rm0004-haos

Home Assistant add-on repository voor de **UCTRONICS RM0004 Pi Rack Pro**
op **Raspberry Pi 5** met HAOS.

## Add-ons in deze repository

| Add-on | Versie | Omschrijving |
|--------|--------|--------------|
| UCTRONICS RM0004 Display | 1.0.3 | LCD stats + power-button driver |

## Installeren in Home Assistant

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Voeg de volgende URL toe en klik **Add**:
   ```
   https://github.com/sammycolson/uctronics-rm0004-haos
   ```
3. Zoek **"UCTRONICS RM0004 Display"** in de store

Zie de [add-on README](uctronics_display/README.md) voor
installatie-vereisten en troubleshooting.

## Waarom een nieuwe repo?

De bestaande fork (`sammycolson/UCTRONICS_RM0004_HA`) is gebaseerd op de
C-implementatie van UCTRONICS. Die stuurt geen display-init-sequentie
op Pi 5, waardoor het scherm vastloopt op het boot-logo
([upstream issue #46](https://github.com/UCTRONICS/SKU_RM0004/issues/46)).

Deze repo gebruikt een volledige Python-implementatie die:
- De volledige ST7735S init-sequentie verstuurt via de I²C bridge
- BusyBox-compatible is (geen GNU-only flags)
- Pi 5 GPIO ondersteunt via gpiod v2 (gpiochip4)
- Geen `/dev/sda` of `eth0` aanneemt
