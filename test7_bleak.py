# FIND DEVICE

import asyncio
import bleak
# from bleak import BleakScanner
# from bleak import BleakClient
import nest_asyncio

nest_asyncio.apply()


async def run():
    devices = await bleak.BleakScanner.discover()
    for d in devices:
        print(d)

def callback(sender, data):
    print(f"{sender}: {data}")


async def main(address):
    print("Connecting to device...")
    async with bleak.BleakClient(address) as client:
        print("Connected")

        ch = await client.read_gatt_char(16)
        #ch = await client.read_gatt_char(client.services.services[16].uuid)
        await client.start_notify(16, callback)
        #client.services.services[16].uuid
        while 1:
            await asyncio.sleep(1)

        #model_number = client.read_gatt_char()
        #print("Model Number: {0}".format("".join(map(chr, model_number))))
        # t = await client.get_services()
        # print(t.services)


loop = asyncio.get_event_loop()

asyncio.run(run())

address = "C3:D8:3C:EB:54:65"
asyncio.run(main(address))
