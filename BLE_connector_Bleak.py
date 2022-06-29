import asyncio

import bleak


# async def create_BLE_connector(address):
#    instance = BLE_connector()
#    await instance.async_init(address=address)
#    return instance


class BLE_connector:
    def __init__(self, address):
        self.client = bleak.BleakClient(address)

    async def keep_connections_to_device(self, uuids, callbacks):
        while True:
            try:
                await self.client.connect(timeout=10)
                if self.client.is_connected:
                    print("Connected to Device")
                    # self.client.set_disconnected_callback(self.on_disconnect)
                    for uuid, callback in zip(uuids, callbacks):
                        await self.client.start_notify(uuid, callback)
                    while True:
                        if not self.client.is_connected:
                            print("Lost connection, reconnecting...")
                            break
                        await asyncio.sleep(1)
                else:
                    print(f"Failed to connect to Device, reconnecting...")
                    await asyncio.sleep(0)
            except Exception as e:
                print(e)
                await asyncio.sleep(1)

    async def scan(self):
        try:
            devices_list = []

            devices = await bleak.BleakScanner.discover(5)
            devices.sort(key=lambda x: -x.rssi)  # sort by signal strength
            for device in devices:
                devices_list.append(str(device.address) + "/" + str(device.name) + "/" + str(device.rssi))
#
            return devices_list

            #scanner = bleak.BleakScanner()
            #scanner.register_detection_callback(self.detection_callback)
            #await scanner.start()
            #await asyncio.sleep(5.0)
            #await scanner.stop()


        except Exception as e:
            print(e)

    #def detection_callback(device, advertisement_data):
    #    print(device.address, "RSSI:", device.rssi, advertisement_data)

    async def get_rssi(self):
        return await self.client.get_rssi()

    async def get_battery_voltage(self):
        return "3.7"

    async def disconnect(self):
        print("Disconnecting...")
        if self.client.is_connected:
            await self.client.disconnect()
            print("Disconnected")
