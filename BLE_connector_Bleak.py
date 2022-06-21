import asyncio

import bleak


# async def create_BLE_connector(address):
#    instance = BLE_connector()
#    await instance.async_init(address=address)
#    return instance


class BLE_connector:
    def __init__(self, address):
        self.client = bleak.BleakClient(address)
        # self.connection_enabled = False

    # async def async_init(self, address):

    async def keep_connections_to_device(self, uuids, callbacks):
        while True:
            try:
                await self.client.connect()
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
        devices_dict = {}
        devices_list = []

        devices = await bleak.BleakScanner.discover(10)
        for i, device in enumerate(devices):
            # Print the devices discovered
            print([i], device.address, device.name, device.metadata["uuids"])
            # Put devices information into list
            devices_dict[device.address] = []
            devices_dict[device.address].append(device.name)
            devices_dict[device.address].append(device.rssi)
            devices_list.append([device.address, device.name, device.rssi])
        print(devices_dict)
        return devices_list

    async def close(self):
        print("Closing Bleak...")
        await self.client.disconnect()
