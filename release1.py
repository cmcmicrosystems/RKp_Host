import asyncio
import datetime
import tkinter as tk
import math

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
uuids = ['340a1b80-cf4b-11e1-ac36-0002a5d5c51b', ]
sample_delay = 0.2


class App(tk.Tk):
    """Main window of app based on tkinter framework.
    Runs asynchronously, dynamically scheduling which loop to run next depending on intervals."""

    def __init__(self, loop: asyncio.AbstractEventLoop):
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

        self.button_autoresize_X_var = tk.IntVar(value=1)
        self.button_autoresize_X = tk.Checkbutton(master=self.frameControls,
                                                  text="Maximize X",
                                                  variable=self.button_autoresize_X_var
                                                  )

        self.button_autoresize_Y_var = tk.IntVar(value=1)
        self.button_autoresize_Y = tk.Checkbutton(master=self.frameControls,
                                                  text="Maximize Y",
                                                  variable=self.button_autoresize_Y_var
                                                  )

        self.button_autoresize_axis_var = tk.IntVar(value=0)
        self.button_autoresize_axis = tk.Checkbutton(master=self.frameControls,
                                                     text="Autoresize Axis",
                                                     variable=self.button_autoresize_axis_var
                                                     )

        self.button_pause_plotting_var = tk.IntVar(value=0)
        self.button_pause_plotting = tk.Checkbutton(master=self.frameControls,
                                                    text="Pause plotting",
                                                    variable=self.button_pause_plotting_var
                                                    )

        # OPTIONS = [
        #    "X",
        #    "All resize",
        #    "Recent only resize"
        #    "Manual resize"
        # ]
        # resize_variable = tk.StringVar(master=self.frameControls)
        # resize_variable.set(OPTIONS[0])  # default value
        # self.option_autoresize = tk.OptionMenu(master=self.frameControls,
        #                                       variable=variable,
        #                                       *OPTIONS
        #                                       )

        self.button_save = tk.Button(master=self.frameControls,
                                     text="Save to out.json",
                                     command=self.save_json
                                     )

        self.button_load = tk.Button(master=self.frameControls,
                                     text="Load from out.json",
                                     command=self.load_json
                                     )

        self.button_quit = tk.Button(master=self.frameControls,
                                     text="Quit",
                                     command=self.close
                                     )

        # Packing order is important. Widgets are processed sequentially and if there
        # is no space left, because the window is too small, they are not displayed.
        # The canvas is rather flexible in its size, so we pack it last which makes
        # sure the UI controls are displayed as long as possible.
        self.frameControls.pack(side=tk.LEFT, fill=tk.BOTH)
        self.frameGraph.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)

        self.button_autoresize_X.pack(side=tk.TOP, fill=tk.X)
        self.button_autoresize_Y.pack(side=tk.TOP, fill=tk.X)
        self.button_autoresize_axis.pack(side=tk.TOP, fill=tk.X)
        self.button_pause_plotting.pack(side=tk.TOP, fill=tk.X)

        self.button_save.pack(side=tk.TOP, fill=tk.X)
        self.button_load.pack(side=tk.TOP, fill=tk.X)
        self.button_quit.pack(side=tk.TOP, fill=tk.X)

        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)
        #

        # self.electrodes = {}

        # self.electrodes["electrode_1"] = self.df

        self.init_dataframe()

        # TODO https://www.delftstack.com/howto/python-pandas/pandas-dataframe-to-json/

        self.tasks = []  # list of tasks to be continuously executed at the same time (asynchronously, not in parallel)

        # Use either Bleak or BleuIO
        # self.tasks.append(
        #    loop.create_task(self.get_data_loop_bleuio(interval=0))
        # )
        self.tasks.append(
            loop.create_task(self.register_data_callback_bleak())
        )
        self.tasks.append(
            loop.create_task(self.update_plot_loop(interval=1.0))
        )  # matplotlib is slow with large amounts of data, so update every second
        self.tasks.append(
            loop.create_task(self.update_ui_loop(interval=1 / 60))
        )

    def plots_init(self):
        """Initializes plots"""
        plt.rcParams['axes.grid'] = True  # enables all grid lines globally

        self.fig = plt.figure(figsize=(5, 4), dpi=100)

        self.subplot1 = self.fig.add_subplot(2, 2, 1)
        self.subplot2 = self.fig.add_subplot(2, 2, 2)
        self.subplot3 = self.fig.add_subplot(2, 2, 3, projection='3d')
        # self.subplot4 = fig.add_subplot(2, 2, 4)

        self.subplot1.set_xlabel("N, samples")
        self.subplot1.set_ylabel("f(N)")
        self.subplot2.set_xlabel("N, samples")
        self.subplot2.set_ylabel("Jitter(s)")
        self.subplot3.set_xlabel("Z")
        self.subplot3.set_ylabel("Y")
        self.subplot3.set_zlabel("X")

        self.line0 = self.subplot1.plot([], [])[0]
        self.line1 = self.subplot1.plot([], [])[0]
        self.line2 = self.subplot1.plot([], [])[0]
        self.line3 = self.subplot2.plot([], [])[0]
        self.line4 = self.subplot3.scatter3D([], [], [], cmap='Greens')

        self.canvas = FigureCanvasTkAgg(self.fig,
                                        master=self.frameGraph
                                        )  # A tk.DrawingArea.

        # pack_toolbar=False will make it easier to use a layout manager later on.
        self.toolbar = NavigationToolbar2Tk(canvas=self.canvas,
                                            window=self.frameGraph,
                                            pack_toolbar=False
                                            )

        self.canvas.mpl_connect("key_press_event",
                                lambda event: print(f"you pressed {event.key}")
                                )

        self.canvas.mpl_connect("key_press_event",
                                key_press_handler
                                )

        self.bind("<Configure>", self.apply_tight_layout, )  # resize plots when window size changes

        self.received_new_data = False

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
        self.is_time_at_start_recorded = False
        await self.BLE_connector_instance.keep_connections_to_device(uuids=uuids, callbacks=[self.data_callback1])

    async def data_callback1(self, sender, data: bytearray):
        """Called whenever Bluetooth API receives a notification or indication"""
        if not self.is_time_at_start_recorded:
            self.time_at_start = datetime.datetime.utcnow().timestamp()
            self.is_time_at_start_recorded = True

        if sender in self.N:
            self.N[sender] += 1
        else:
            self.N[sender] = 0

        time_delivered = datetime.datetime.utcnow().timestamp()
        jitter = time_delivered - self.time_at_start - (self.N[sender] * sample_delay)
        # time_calculated = time_delivered - jitter
        time_calculated = self.time_at_start + (self.N[sender] * sample_delay)

        data.reverse()  # fix small endian notation
        datahex = data.hex()

        if sender not in self.dfs.keys():
            self.dfs[sender] = pd.DataFrame(columns=["X", "Y", "Z", "Time", "Jitter", "Time Calculated", "Sender", "Raw", "N"])
            self.dfs[sender] = self.dfs[sender].set_index("N")
        #  May be not stable in case of multi threading (so have to use async)
        self.dfs[sender].loc[self.N[sender]] = [twos_comp(int(datahex[0:4], 16), 16) * 0.001,
                                                twos_comp(int(datahex[4:8], 16), 16) * 0.001,
                                                twos_comp(int(datahex[8:12], 16), 16) * 0.001,
                                                time_delivered,
                                                jitter,  # jitter
                                                time_calculated,
                                                sender,
                                                data.__str__()  # raw, in case there is a bug
                                                ]  # use either time or N as index

        self.received_new_data = True

    async def update_plot_loop(self, interval):
        """Updates plots inside UI, at regular intervals"""
        print('Plot started')

        waiter1 = StableWaiter(interval)
        while True:
            try:
                await waiter1.wait_async()

                if self.received_new_data == False or self.button_pause_plotting_var.get() == True:
                    # optimization to prevent re-drawing when there is no new data or when plotting is paused
                    continue
                self.received_new_data = False

                limits = self.subplot1.axis()
                plot_width_last_frame = limits[1] - limits[0]
                right_side_limit_now = self.dfs[20].index[-1]

                # Don't plot invisible data-points, works well when there is no scaling between frames,
                # but may cause not rendering first several data-points properly if scale changes.
                df_visible = self.dfs[20].loc[
                             max(0, math.floor(right_side_limit_now - plot_width_last_frame) -
                                 math.ceil(1 / sample_delay)):
                             right_side_limit_now + 1
                             ]

                self.line0.set_data(df_visible.index, df_visible['X'])
                self.line1.set_data(df_visible.index, df_visible['Y'])
                self.line2.set_data(df_visible.index, df_visible['Z'])
                self.line3.set_data(df_visible.index, df_visible['Jitter'])
                self.line4._offsets3d = (df_visible['Z'], df_visible['Y'], df_visible['X'])

                if self.button_autoresize_X_var.get():
                    # Maximizes X axis
                    self.subplot1.set_xlim(min(self.dfs[20].index),
                                           max(self.dfs[20].index)
                                           )
                    self.subplot2.set_xlim(min(self.dfs[20].index),
                                           max(self.dfs[20].index)
                                           )
                else:
                    # Synchronizes X-zoom across plots(uses only subplot1 as reference) and moves to right most position

                    self.subplot1.set_xlim(right_side_limit_now - plot_width_last_frame,
                                           right_side_limit_now
                                           )
                    self.subplot2.set_xlim(right_side_limit_now - plot_width_last_frame,
                                           right_side_limit_now
                                           )

                if self.button_autoresize_Y_var.get():
                    self.subplot1.set_ylim(min(min(df_visible['X']),
                                               min(df_visible['Y']),
                                               min(df_visible['Z'])
                                               ),
                                           max(max(df_visible['X']),
                                               max(df_visible['Y']),
                                               max(df_visible['Z'])
                                               )
                                           )

                    self.subplot2.set_ylim(min(df_visible['Jitter']),
                                           max(df_visible['Jitter'])
                                           )

                self.subplot3.set_xlim(min(df_visible['Z']),
                                       max(df_visible['Z'])
                                       )
                self.subplot3.set_ylim(min(df_visible['Y']),
                                       max(df_visible['Y'])
                                       )
                self.subplot3.set_zlim(min(df_visible['X']),
                                       max(df_visible['X'])
                                       )

                # if self.button_autoresize_axis_var.get():
                #    self.fig.tight_layout()

                self.canvas.draw()

            except Exception as e:
                print(e)

    async def update_ui_loop(self, interval):
        print('UI started')

        waiter2 = StableWaiter(interval)
        while True:
            try:
                await waiter2.wait_async()
                self.update()
            except Exception as e:
                print(e)

    # def save_csv(self):
    #    print('Saving to .csv ...')
    #    self.df.to_csv(path_or_buf='output/out.csv')
    #    print('Saving finished!')

    def save_json(self):
        try:
            print('Saving to .json ...')
            self.dfs[20].to_json(path_or_buf='output/out.json', orient='index')  # TODO
            print('Saving finished!')
        except Exception as e:
            print(e)

    def load_json(self):
        try:
            print('Loading from .json ...')
            self.dfs[20] = pd.read_json(path_or_buf='output/out.json', orient='index')
            print('Loading finished!')
        except Exception as e:
            print(e)

    def init_dataframe(self):
        try:
            print('Init dataframe ...')
            self.dfs = {}
            self.N = {}
            print('Init dataframe finished!')
        except Exception as e:
            print(e)

    def apply_tight_layout(self, event: tk.Event):
        try:
            if event.widget.widgetName == "canvas":
                self.fig.tight_layout()
        except Exception as e:
            pass

    def close(self):
        print('Exiting...')
        self.loop.run_until_complete(self.BLE_connector_instance.close())
        for task in self.tasks:
            task.cancel()
        self.loop.stop()
        self.destroy()


def twos_comp(val, bits):
    """Computes the 2's complement of int value val
    https://stackoverflow.com/questions/1604464/twos-complement-in-python"""

    if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)  # compute negative value
    return val  # return positive value as is


class StableWaiter:
    def __init__(self, interval):
        self.interval = interval
        self.t1 = datetime.datetime.now()

    async def wait_async(self):
        """Waits at the same intervals independently of CPU speed (if CPU is faster than certain threshold)
        This is not mandatory, but makes UI smoother"""
        t2 = datetime.datetime.now()
        previous_frame_time = ((t2 - self.t1).total_seconds())
        self.t1 = t2

        await asyncio.sleep(min((self.interval * 2) - previous_frame_time, self.interval))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app = App(loop)
    loop.run_forever()
    loop.close()
