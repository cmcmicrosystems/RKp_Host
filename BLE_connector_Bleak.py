import asyncio

import bleak


class BLE_connector:
    def __init__(self, address):
        try:
            del self.client
        except Exception as e:
            pass
        self.client = bleak.BleakClient(address)

    async def keep_connections_to_device(self, uuids, callbacks):
        while True:
            try:
                await self.client.connect(timeout=32)
                if self.client.is_connected:
                    print("Connected to Device")

                    def on_disconnect(client):
                        print("callback")
                        print("Client with address {} got disconnected!".format(client.address))

                    self.client.set_disconnected_callback(on_disconnect)
                    for uuid, callback in zip(uuids, callbacks):
                        await self.client.start_notify(uuid, callback)
                    while True:
                        if not self.client.is_connected:
                            print("Lost connection, reconnecting...")
                            break
                        await asyncio.sleep(1)
                else:
                    print(f"Not connected to Device, reconnecting...")
                    await asyncio.sleep(0)
            except Exception as e:
                print(e)
                print("Connection error, reconnecting...")
                # del self.client
                await self.client.disconnect()  # accelerates reconnection
                await asyncio.sleep(1)

    # async def scan(self):
    #    try:
    #        devices_list = []
    #
    #        devices = await bleak.BleakScanner.discover(5)
    #        devices.sort(key=lambda x: -x.rssi)  # sort by signal strength
    #        for device in devices:
    #            devices_list.append(str(device.address) + "/" + str(device.name) + "/" + str(device.rssi))
    #        #
    #        return devices_list
    #
    #        # scanner = bleak.BleakScanner()
    #        # scanner.register_detection_callback(self.detection_callback)
    #        # await scanner.start()
    #        # await asyncio.sleep(5.0)
    #        # await scanner.stop()
    #
    #
    #    except Exception as e:
    #        print(e)

    # def detection_callback(device, advertisement_data):
    #    print(device.address, "RSSI:", device.rssi, advertisement_data)

    async def start_scanning(self):
        try:
            dict_of_devices = {}

            def detection_callback(device, advertisement_data):
                # print(device.address, "RSSI:", device.rssi, advertisement_data)

                dict_of_devices[device.address] = device  # overwrites device object

            scanner = bleak.BleakScanner(scanning_mode="passive")
            scanner.register_detection_callback(detection_callback)
            await scanner.start()

            async def stop_handle():
                print('stopping handle')
                await scanner.stop()

            return stop_handle, dict_of_devices

        except Exception as e:
            print(e)
            return -1

    async def get_battery_voltage(self):
        return "3.7"

    async def write_char(self):
        return 0

    async def disconnect(self):
        if self.client.is_connected:
            print("Disconnecting...")
            # del self.client
            await self.client.disconnect()
            print("Disconnected")
