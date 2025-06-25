import os
import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

# BLE UUIDs
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"


class TokenCharacteristic(dbus.service.Object):
    def __init__(self, bus, index, service, token: bytes):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.token = token
        self.service = service
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            'org.bluez.GattCharacteristic1': {
                'Service': self.service.get_path(),
                'UUID': CHAR_UUID,
                'Flags': ['read'],
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method('org.bluez.GattCharacteristic1',
                         in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        print("[BLE] Token read over Bluetooth.")
        return dbus.Array(self.token, signature='y')


class TokenService(dbus.service.Object):
    def __init__(self, bus, index, token: bytes):
        self.path = '/org/bluez/example/service' + str(index)
        self.bus = bus
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.characteristics.append(TokenCharacteristic(bus, 0, self, token))

    def get_properties(self):
        return {
            'org.bluez.GattService1': {
                'UUID': SERVICE_UUID,
                'Primary': True,
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_characteristics(self):
        return self.characteristics


class Application(dbus.service.Object):
    def __init__(self, bus, token: bytes):
        self.path = '/'
        self.services = [TokenService(bus, 0, token)]
        dbus.service.Object.__init__(self, bus, self.path)

    @dbus.service.method('org.freedesktop.DBus.ObjectManager',
                         out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        managed_objects = {}
        for service in self.services:
            managed_objects[service.get_path()] = service.get_properties()
            for char in service.get_characteristics():
                managed_objects[char.get_path()] = char.get_properties()
        return managed_objects


def start_ble_token_advertiser():
    token = os.getenv("FEEDER_TOKEN")
    if not token:
        print("[ERROR] FEEDER_TOKEN is not set in the environment.")
        return

    token_bytes = token.encode()

    print("[BLE] Starting BLE advertisement with token:", token)

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    # Find Bluetooth adapter path
    manager = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager')
    objects = manager.GetManagedObjects()
    adapter_path = next(
        (path for path, ifaces in objects.items() if 'org.bluez.Adapter1' in ifaces), None
    )
    if not adapter_path:
        print("[ERROR] No Bluetooth adapter found.")
        return

    service_manager = dbus.Interface(bus.get_object('org.bluez', adapter_path), 'org.bluez.GattManager1')
    app = Application(bus, token_bytes)

    loop = GLib.MainLoop()

    def on_register():
        print("[BLE] GATT service registered and running.")

    def on_error(e):
        print("[BLE] Failed to register application:", e)
        loop.quit()

    service_manager.RegisterApplication(app.get_path(), {}, reply_handler=on_register, error_handler=on_error)

    # Run in background
    from threading import Thread
    Thread(target=loop.run, daemon=True).start()
