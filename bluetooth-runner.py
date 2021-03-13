#!/usr/bin/env python

import sys
import signal
import logging
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GObject
import subprocess
import time

LOG_LEVEL = logging.INFO
#LOG_LEVEL = logging.DEBUG
LOG_FILE = "/dev/stdout"
#LOG_FILE = "/var/log/syslog"
LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"

PATH = "/org/bluez/hci0/dev_"
SPEAKERS = f"{PATH}00_00_00_00_03_C2"
HEADSET = f"{PATH}E8_AB_FA_37_DE_E9"


def device_property_changed_cb(property_name, *args, path, **kwargs):
    dicts = [x for x in args if type(x) == dbus.Dictionary]
    if not dicts:
        return

    if "bluez" not in property_name:
        return

    dic = dicts[0]
    connected = dic.get("Connected")
    logging.info(f"prop change: {property_name}, dict {dic}, connected {connected}")
    if connected is not None:
        logging.info(f"path: {path}")
        action = "connected" if connected else "disconnected"
        print(f"bluetooth {action}")
        if path == HEADSET:
            bus = dbus.SystemBus()
            speakers = bus.get_object("org.bluez", "/org/bluez/hci0/dev_00_00_00_00_03_C2")
            prop_iface = dbus.Interface(speakers, "org.freedesktop.DBus.Properties")

            if action == "connected":
                if prop_iface.Get("org.bluez.Device1", "Connected"):
                    dev_if = dbus.Interface(speakers, "org.bluez.Device1")
                    dev_if.Disconnect()
                    logging.info("Speakers disconnected")

            if action == "disconnected":
                if not prop_iface.Get("org.bluez.Device1", "Connected"):
                    dev_if = dbus.Interface(speakers, "org.bluez.Device1")
                    dev_if.Connect()
                    logging.info("Speakers re-connected")
        else:
            print(path, HEADSET)

def shutdown(signum, frame):
    mainloop.quit()

if __name__ == "__main__":
    # shut down on a TERM signal
    signal.signal(signal.SIGTERM, shutdown)

    # start logging
    logging.basicConfig(filename=LOG_FILE, format=LOG_FORMAT, level=LOG_LEVEL)
    logging.info("Starting to monitor Bluetooth connections")

    # get the system bus
    try:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
    except Exception as ex:
        logging.error("Unable to get the system dbus: '{0}'. Exiting."
                      " Is dbus running?".format(ex.message))
        sys.exit(1)

    # listen for signals on the Bluez bus
    bus.add_signal_receiver(device_property_changed_cb, bus_name="org.bluez",
                            signal_name=None,
                            dbus_interface=None,
                            path_keyword="path", interface_keyword="interface")
    try:
        mainloop = GObject.MainLoop()
        mainloop.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error("Unable to run the gobject main loop")
        logging.error(e)

    logging.info("Shutting down bluetooth-runner")
    sys.exit(0)
