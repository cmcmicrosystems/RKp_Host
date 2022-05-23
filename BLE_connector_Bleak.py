import asyncio

import datetime

import bleak


#async def create_BLE_connector(address):
#    instance = BLE_connector()
#    await instance.async_init(address=address)
#    return instance


class BLE_connector:
    def __init__(self, address):
        self.client = bleak.BleakClient(address)
        self.connection_enabled = False

    #async def async_init(self, address):


    async def keep_connection_to_device(self, uuid, callback):
        while True:
            try:
                await self.client.connect()
                if self.client.is_connected:
                    print("Connected to Device")
                    # self.client.set_disconnected_callback(self.on_disconnect)
                    await self.client.start_notify(uuid, callback)
                    while True:
                        if not self.client.is_connected:
                            print("Lost connection, reconnecting...")
                            break
                        await asyncio.sleep(1)
                else:
                    print(f"Failed to connect to Device, reconnecting...")
            except Exception as e:
                    print(e)

    async def close(self):
        print("Closing Bleak...")
        await self.client.disconnect()
