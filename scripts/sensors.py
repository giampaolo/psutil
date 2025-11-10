#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A clone of 'sensors' utility on Linux printing hardware temperatures,
fans speed and battery info.

$ python3 scripts/sensors.py
asus
    Temperatures:
        asus                 57.0°C (high=None°C, critical=None°C)
    Fans:
        cpu_fan              3500 RPM
acpitz
    Temperatures:
        acpitz               57.0°C (high=108.0°C, critical=108.0°C)
coretemp
    Temperatures:
        Physical id 0        61.0°C (high=87.0°C, critical=105.0°C)
        Core 0               61.0°C (high=87.0°C, critical=105.0°C)
        Core 1               59.0°C (high=87.0°C, critical=105.0°C)
Battery:
    charge:     84.95%
    status:     charging
    plugged in: yes
"""

import psutil


def secs2hours(secs):
    mm, ss = divmod(secs, 60)
    hh, mm = divmod(mm, 60)
    return f"{int(hh)}:{int(mm):02}:{int(ss):02}"


def main():
    if hasattr(psutil, "sensors_temperatures"):
        temps = psutil.sensors_temperatures()
    else:
        temps = {}
    fans = psutil.sensors_fans() if hasattr(psutil, "sensors_fans") else {}
    if hasattr(psutil, "sensors_battery"):
        battery = psutil.sensors_battery()
    else:
        battery = None

    if not any((temps, fans, battery)):
        print("can't read any temperature, fans or battery info")
        return

    names = set(list(temps.keys()) + list(fans.keys()))
    for name in names:
        print(name)
        # Temperatures.
        if name in temps:
            print("    Temperatures:")
            for entry in temps[name]:
                s = "        {:<20} {}°C (high={}°C, critical={}°C)".format(
                    entry.label or name,
                    entry.current,
                    entry.high,
                    entry.critical,
                )
                print(s)
        # Fans.
        if name in fans:
            print("    Fans:")
            for entry in fans[name]:
                print(
                    "        {:<20} {} RPM".format(
                        entry.label or name, entry.current
                    )
                )

    # Battery.
    if battery:
        print("Battery:")
        print(f"    charge:     {round(battery.percent, 2)}%")
        if battery.power_plugged:
            print(
                "    status:     {}".format(
                    "charging" if battery.percent < 100 else "fully charged"
                )
            )
            print("    plugged in: yes")
        else:
            print(f"    left:       {secs2hours(battery.secsleft)}")
            print("    status:     discharging")
            print("    plugged in: no")


if __name__ == '__main__':
    main()
