import asyncio

import bleak


class BLE_connector:
    def __init__(self, address="", to_connect=True):
        self.address = address
        self.to_connect = to_connect
        try:
            asyncio.get_running_loop().run_until_complete(self.client.disconnect())
        except Exception as e:
            # print(e)
            pass
        try:
            del self.client
        except Exception as e:
            # print(e)
            pass
        if self.to_connect:
            self.client = bleak.BleakClient(address)
            asyncio.get_running_loop().run_until_complete(self.client.pair(2))

    async def keep_connections_to_device(self, uuids, callbacks):
        while True:
            try:
                if self.to_connect:
                    # workaround, without this line it sometimes cannot reconnect or takes a lot of time to reconnect
                    # self.__init__(self.address, self.to_connect)
                    await self.client.connect(timeout=32)  # timeout should be the same as in firmware
                    if self.client.is_connected:
                        print("Connected to Device")

                        def on_disconnect(client):
                            print("Client with address {} got disconnected!".format(client.address))

                        self.client.set_disconnected_callback(on_disconnect)
                        for uuid, callback in zip(uuids, callbacks):
                            await self.client.start_notify(uuid, callback)
                        while True:
                            if not self.client.is_connected:
                                print("Lost connection, reconnecting...")
                                await self.client.disconnect()
                                break
                            # print("Here")
                            # try:
                            #     a = await self.client.get_services()  #
                            #     # print(a)
                            #     for c in a.characteristics.values():
                            #         # print(c.uuid, c.__dict__)
                            #         #
                            #         try:
                            #             # self.client.p
                            #             # await self.client.pair(1)
                            #             print(await self.client.write_gatt_char(c, B"123ABC"))  # TODO
                            #             print(await self.client.read_gatt_char(c))
                            #             # bytearray(b'\x02\x03\x05\x07')
                            #             # print(b)
                            #         #
                            #         except Exception as e:
                            #             print("Test error 2:", e)
                            #             if "Access Denied" not in str(e):
                            #                 print("Have a look!", e)
                            #         await asyncio.sleep(0.1)
                            #     # '330a1b80-cf4b-11e1-ac36-0002a5d5c51b'
                            #     # print(a.characteristics[20])
                            # except Exception as e:
                            #     print("Test error:", e)
                            await asyncio.sleep(1)
                    else:
                        print(f"Not connected to Device, reconnecting...")
            except Exception as e:
                print(e)
                print("Connection error, reconnecting...")
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

            return scanner.stop, dict_of_devices

        except Exception as e:
            print(e)
            return -1

    async def get_battery_voltage(self):
        return "3.7"

    async def write_char(self):
        await self.client.write_gatt_char(self.address, b"Hello World!")
        return

    async def disconnect(self):
        try:
            if self.client.is_connected:
                print("Disconnecting...")
                # del self.client
                await self.client.disconnect()
                print("Disconnected")
        except Exception as e:
            pass
