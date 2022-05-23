from bleuio_lib.bleuio_funcs import BleuIo
import asyncio
import hjson
import pprint
from collections import OrderedDict
import datetime


async def create_BLE_connector():
    instance = BLE_connector()
    await instance.async_init()
    return instance


async def my_command(my_dongle, command='AT', wait=1):
    my_dongle.send_command(command)
    await asyncio.sleep(wait)
    print(my_dongle.rx_response)


class BLE_connector:
    # https://stackoverflow.com/questions/33128325/how-to-set-class-attribute-with-await-in-init

    def __init__(self):
        pass


    async def async_init(self):
        self.my_dongle = BleuIo(port="COM4", baud=921600)
        self.my_dongle.start_daemon()
        await asyncio.sleep(1)
        print(self.my_dongle.rx_response)

        await my_command(self.my_dongle, 'ATV1', 1)
        await my_command(self.my_dongle, 'ATA0', 1)
        await my_command(self.my_dongle, 'AT+CENTRAL', 1)
        await my_command(self.my_dongle, 'AT+GAPCONNECT=[1]C3:D8:3C:EB:54:65', 5)
        await my_command(self.my_dongle, 'AT+SETNOTI=0015', 1)

        print()

        await asyncio.sleep(1)

    async def get_more_data(self, interval=0):
        N = 0
        while 1:
            try:
                # print(self.my_dongle.rx_response)
                lines = self.my_dongle.rx_response.pop(0)  # FIFO
                for line in lines.split("\n"):
                    parsed = hjson.loads(line)
                    if isinstance(parsed, OrderedDict):
                        if '777' in parsed.keys():  # '777' means notification
                            digits_only = parsed['0015']['hex'][2:]
                            response = {
                                'Hex': digits_only,
                                'Time': datetime.datetime.utcnow().timestamp(),
                                'N': N
                            }
                            N += 1
                            # print('---')
                            #print('yield')
                            yield response
                        else:
                            # print(parsed)
                            pass
            except Exception as e:
                # print(e)
                pass

            while not self.my_dongle.rx_response:
                #print('_________empty')
                await asyncio.sleep(interval)

    def __del__(self):
        self.my_dongle.stop_daemon()
        print('BLE_connector instance destroyed successfully')


async def main():
    instance = await create_BLE_connector()
    print(instance)
    async for data in instance.get_more_data():
        print(data)


if __name__ == "__main__":
    asyncio.run(main())
