import asyncio
import datetime
import tkinter as tk

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)

matplotlib.use('TkAgg')  # Makes sure that all windows are rendered using tkinter

import BLE_connector_Bleak
# import BLE_connector_BleuIO

# hotfix to run nested asyncio to correctly close Bleak without having to wait for timeout to reconnect to device again
import nest_asyncio

nest_asyncio.apply()

address = 'C3:D8:3C:EB:54:65'
uuid = '340a1b80-cf4b-11e1-ac36-0002a5d5c51b'


class App(tk.Tk):
    """Main window of app based on tkinter framework.
    Runs asynchronously, dynamically scheduling which loop to run next depending on intervals."""

    def __init__(self, loop):
        super().__init__()
        self.loop = loop

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.wm_title("Release1")

        self.frameGraph = tk.Frame(master=self)  # div
        self.frameControls = tk.Frame(master=self)  # div

        self.plots_init()

        # slider_update = tk.Scale(master=self.frameControls,
        #                         from_=1,
        #                         to=5,
        #                         orient=tk.HORIZONTAL,
        #                         command=self.update_data,
        #                         label="Frequency [Hz]"
        #                         )
        self.button_autoresize_var = tk.IntVar()
        self.button_autoresize = tk.Checkbutton(master=self.frameControls,
                                                text="Autoresize graph",
                                                variable=self.button_autoresize_var,
                                                # command=self.autoresize
                                                )
        self.button_autoresize.select()

        self.button_save = tk.Button(master=self.frameControls,
                                     text="Save to out.csv",
                                     command=self.save_csv
                                     )

        self.button_quit = tk.Button(master=self.frameControls,
                                     text="Quit",
                                     command=self.close
                                     )

        # Packing order is important. Widgets are processed sequentially and if there
        # is no space left, because the window is too small, they are not displayed.
        # The canvas is rather flexible in its size, so we pack it last which makes
        # sure the UI controls are displayed as long as possible.
        self.frameControls.pack(side=tk.BOTTOM, fill=tk.BOTH)
        self.frameGraph.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)

        self.button_autoresize.pack(side=tk.RIGHT, fill=tk.X)
        self.button_save.pack(side=tk.RIGHT, fill=tk.X)
        self.button_quit.pack(side=tk.BOTTOM, fill=tk.X)
        # slider_update.pack(side=tk.BOTTOM, fill=tk.X)
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)

        self.df = pd.DataFrame(columns=["X", "Y", "Z", "Time", "Jitter", "Time Calculated", "Sender", "N"])
        self.df = self.df.set_index("N")

        self.tasks = []

        # Use either Bleak or BleuIO
        # self.tasks.append(
        #    loop.create_task(self.get_data_loop_bleuio(interval=0))
        # )
        self.tasks.append(
            loop.create_task(self.register_data_callback_bleak())
        )
        self.tasks.append(
            loop.create_task(self.update_plot_loop(interval=1 / 5))
        )  # TODO accelerate matplotlib
        self.tasks.append(
            loop.create_task(self.update_ui_loop(interval=1 / 5))
        )

    def plots_init(self):
        """Initializes plots"""
        fig = plt.figure(figsize=(5, 4), dpi=100)

        self.subplot1 = fig.add_subplot(2, 2, 1)
        self.subplot2 = fig.add_subplot(2, 2, 2)
        self.subplot3 = fig.add_subplot(2, 2, 3, projection='3d')
        # self.subplot4 = fig.add_subplot(2, 2, 4)

        self.line0 = self.subplot1.plot([], [])[0]
        self.line1 = self.subplot1.plot([], [])[0]
        self.line2 = self.subplot1.plot([], [])[0]
        self.line3 = self.subplot2.plot([], [])[0]
        self.line4 = self.subplot3.scatter3D([], [], [], cmap='Greens')

        self.subplot1.set_xlabel("N, samples")
        self.subplot1.set_ylabel("f(N)")

        self.canvas = FigureCanvasTkAgg(fig,
                                        master=self.frameGraph
                                        )  # A tk.DrawingArea.

        self.canvas.mpl_connect("key_press_event",
                                lambda event: print(f"you pressed {event.key}")
                                )

        self.canvas.mpl_connect("key_press_event",
                                key_press_handler
                                )

        # pack_toolbar=False will make it easier to use a layout manager later on.
        self.toolbar = NavigationToolbar2Tk(canvas=self.canvas,
                                            window=self.frameGraph,
                                            pack_toolbar=False
                                            )
        fig.tight_layout()

    # async def get_data_loop_bleuio(self, interval):
    #    """Adds new data into Dataframe"""
    #    self.instance = await BLE_connector_BleuIO.create_BLE_connector()
    #    print(self.instance)
    #    async for data in self.instance.get_more_data(interval=interval):
    #        try:
    #            # print(data)
    #            self.df.loc[data['N']] = [twos_comp(int(data['Hex'][0:4], 16), 16),
    #                                      twos_comp(int(data['Hex'][4:8], 16), 16),
    #                                      twos_comp(int(data['Hex'][8:12], 16), 16),
    #                                      data['Time'],
    #                                      ]  # use either time or N as index
    #        except Exception as e:
    #            print(e)

    async def register_data_callback_bleak(self):
        """Sets up notifications using Bleak, and attaches callbacks"""
        self.BLE_connector_instance = BLE_connector_Bleak.BLE_connector(address=address)
        self.N = 0
        self.is_time_at_start_recorded = False
        await self.BLE_connector_instance.keep_connection_to_device(uuid=uuid, callback=self.data_callback)

    async def data_callback(self, sender, data):
        """Called whenever Bluetooth API receives a notification or indication"""
        if not self.is_time_at_start_recorded:
            self.time_at_start = datetime.datetime.utcnow().timestamp()
            self.is_time_at_start_recorded = True
        data.reverse()
        datahex = data.hex()

        time_delivered = datetime.datetime.utcnow().timestamp()
        jitter = time_delivered - self.time_at_start - (self.N * 0.2)
        # time_calculated = time_delivered - jitter
        time_calculated = self.time_at_start + (self.N * 0.2)
        self.df.loc[self.N] = [twos_comp(int(datahex[0:4], 16), 16) * 0.001,  # TODO May be not stable? Need to check.
                               twos_comp(int(datahex[4:8], 16), 16) * 0.001,
                               twos_comp(int(datahex[8:12], 16), 16) * 0.001,
                               time_delivered,
                               jitter,  # jitter
                               time_calculated,
                               sender
                               ]  # use either time or N as index
        self.N += 1

    async def update_plot_loop(self, interval):
        """Updates plots inside UI, at regular intervals"""
        while True:
            try:
                await asyncio.sleep(interval)

                self.line0.set_data(self.df.index, self.df['X'])
                self.line1.set_data(self.df.index, self.df['Y'])
                self.line2.set_data(self.df.index, self.df['Z'])
                self.line3.set_data(self.df.index, self.df['Jitter'])
                # self.line4._off set_data(self.df['X'], self.df['Y'])
                self.line4._offsets3d = (self.df['Z'], self.df['Y'], self.df['X'])

                if self.button_autoresize_var.get():
                    self.subplot1.set_xlim(min(self.df.index),
                                           max(self.df.index)
                                           )
                    self.subplot1.set_ylim(min(min(self.df['X']),
                                               min(self.df['Y']),
                                               min(self.df['Z']),
                                               # min(self.df['Jitter'])
                                               ),
                                           max(max(self.df['X']),
                                               max(self.df['Y']),
                                               max(self.df['Z']),
                                               # max(self.df['Jitter'])
                                               )
                                           )

                    self.subplot2.set_xlim(min(self.df.index),
                                           max(self.df.index)
                                           )
                    self.subplot2.set_ylim(min(self.df['Jitter']),
                                           max(self.df['Jitter'])
                                           )

                    self.subplot3.set_xlim(min(self.df['Z']),
                                           max(self.df['Z'])
                                           )
                    self.subplot3.set_ylim(min(self.df['Y']),
                                           max(self.df['Y'])
                                           )

                    self.subplot3.set_zlim(min(self.df['X']),
                                           max(self.df['X'])
                                           )

                self.canvas.draw()
            except Exception as e:
                pass
                print(e)
                print('here')

    async def update_ui_loop(self, interval):
        try:
            print('start')

            waiter1 = wait_stable_interval(interval)
            while True:
                await waiter1.wait_async()
                self.update()
        except Exception as e:
            print(e)

    def close(self):
        print('Exiting...')
        self.loop.run_until_complete(self.BLE_connector_instance.close())
        for task in self.tasks:
            task.cancel()
        self.loop.stop()
        self.destroy()

    def save_csv(self):
        print('Saving to .csv ...')
        self.df.to_csv(path_or_buf='output/out.csv')
        print('Saving finished!')


def twos_comp(val, bits):
    """Computes the 2's complement of int value val
    https://stackoverflow.com/questions/1604464/twos-complement-in-python"""

    if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)  # compute negative value
    return val  # return positive value as is


class wait_stable_interval():
    def __init__(self, interval):
        self.interval = interval
        self.t1 = datetime.datetime.now()

    async def wait_async(self):
        """Waits at same intervals independently of CPU speed (if CPU is faster than certain threshold)"""
        self.t2 = datetime.datetime.now()
        previous_frame_time = ((self.t2 - self.t1).total_seconds())
        self.t1 = self.t2

        await asyncio.sleep(min((self.interval * 2) - previous_frame_time, self.interval))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app = App(loop)
    loop.run_forever()
    loop.close()
