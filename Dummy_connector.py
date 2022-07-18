import asyncio


class Dummy_connector:
    def __init__(self, address):
        pass
        # self.client = bleak.BleakClient(address)

    async def keep_connections_to_device(self, uuids, callbacks):
        while True:
            for uuid, callback in zip(uuids, callbacks):
                if uuid == '340a1b80-cf4b-11e1-ac36-0002a5d5c51b':
                    callback(99, bytearray(b'\x02\x03\x05\x07'))
            await asyncio.sleep(10)

    async def start_scanning(self):
        print("Dummy scanning started")
        dict_of_devices = {}

        async def stop_handle():
            print("Stopping not implemented")

        return stop_handle, dict_of_devices

    async def get_battery_voltage(self):
        return "3.7"

    async def write_char(self):
        return 0

    async def disconnect(self):
        print("Dummy disconnecting...")
