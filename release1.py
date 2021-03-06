import asyncio
import datetime
import json
import math
import struct

import matplotlib
import pandas as pd

# import bitstring  # TODO use in the future for easier manipulation of bits

matplotlib.use('TkAgg')  # Makes sure that all windows are rendered using tkinter

import BLE_connector_Bleak
# import BLE_connector_BleuIO

# hotfix to run nested asyncio to correctly close Bleak without having to wait for timeout to reconnect to device again
import nest_asyncio

nest_asyncio.apply()

import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

address_default = 'FE:B7:22:CC:BA:8D'
uuids_default = ['340a1b80-cf4b-11e1-ac36-0002a5d5c51b', ]
write_uuid = '330a1b80-cf4b-11e1-ac36-0002a5d5c51b'


class App(tk.Tk):
    """Main window of app based on tkinter framework.
    Runs asynchronously, dynamically scheduling which loop to run next depending on intervals."""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        """

        :param loop: parent event loop for asynchronous execution, it is not unique in this app
        """
        super().__init__()
        self.loop = loop

        def on_button_close():
            try:
                print('Exiting...')
                self.loop.run_until_complete(self.stop_scanning_handle())
                self.loop.run_until_complete(self.BLE_connector_instance.disconnect())
                for task in self.tasks:
                    task.cancel()
                self.loop.stop()
                self.destroy()
                print('Exiting finished!')
            except Exception as e:
                print(e)
                tk.messagebox.showerror('Error', e.__str__())

        self.protocol("WM_DELETE_WINDOW", on_button_close)
        self.wm_title("SwiftLogger")
        self.iconbitmap('ico/favicon.ico')

        self.geometry("400x115")

        # frameGraph = tk.Frame(master=self,
        #                      highlightbackground="black",
        #                      highlightthickness=1
        #                      )  # div
        # self.plots_init(master=frameGraph)

        frameControls = tk.Frame(master=self,
                                 highlightbackground="black",
                                 highlightthickness=1
                                 )  # div
        self.controls_init(master=frameControls)

        # Packing order is important. Widgets are processed sequentially and if there
        # is no space left, because the window is too small, they are not displayed.
        # The canvas is rather flexible in its size, so we pack it last which makes
        # sure the UI controls are displayed as long as possible.
        frameControls.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # frameGraph.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

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
        # self.tasks.append(
        #    loop.create_task(self.update_plot_loop(interval=1.0))
        # )  # matplotlib is slow with large amounts of data, so update every second
        self.tasks.append(
            loop.create_task(self.update_ui_loop(interval=1 / 60))
        )

        self.tasks.append(
            loop.create_task(self.start_scanning_process())
        )

    # def plots_init(self, master):
    #    """Initializes plots
    #
    #    :param master: reference to parent object
    #    """
    #    plt.rcParams['axes.grid'] = True  # enables all grid lines globally
    #
    #    self.fig = plt.figure(figsize=(5, 4), dpi=100)
    #
    #    self.subplots = {}
    #
    #    self.subplots[1] = self.fig.add_subplot(2, 2, 1)
    #    self.subplots[2] = self.fig.add_subplot(2, 2, 2)
    #    self.subplots[3] = self.fig.add_subplot(2, 2, 3, projection='3d')
    #    # self.subplots[4] = fig.add_subplot(2, 2, 4)
    #
    #    self.subplots[1].set_xlabel("N, samples")
    #    self.subplots[1].set_ylabel("f(N)")
    #    self.subplots[2].set_xlabel("N, samples")
    #    self.subplots[2].set_ylabel("Jitter(s)")
    #    self.subplots[3].set_xlabel("Z")
    #    self.subplots[3].set_ylabel("Y")
    #    self.subplots[3].set_zlabel("X")
    #
    #    self.lines = {}
    #
    #    self.lines[0] = self.subplots[1].plot([], [])[0]
    #    self.lines[1] = self.subplots[1].plot([], [])[0]
    #    self.lines[2] = self.subplots[1].plot([], [])[0]
    #    self.lines[3] = self.subplots[2].plot([], [])[0]
    #    self.lines[4] = self.subplots[3].scatter3D([], [], [], cmap='Greens')
    #
    #    self.canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.fig,
    #                                                                      master=master
    #                                                                      )  # A tk.DrawingArea.
    #
    #    # pack_toolbar=False will make it easier to use a layout manager later on.
    #    self.toolbar = matplotlib.backends.backend_tkagg.NavigationToolbar2Tk(canvas=self.canvas,
    #                                                                          window=master,
    #                                                                          pack_toolbar=False
    #                                                                          )
    #
    #    self.canvas.mpl_connect("key_press_event",
    #                            lambda event: print(f"you pressed {event.key}")
    #                            )
    #
    #    self.canvas.mpl_connect("key_press_event",
    #                            matplotlib.backend_bases.key_press_handler
    #                            )
    #
    #    self.bind("<Configure>", self.apply_tight_layout, )  # resize plots when window size changes
    #
    #    self.received_new_data = False
    #
    #    self.toolbar.pack(side=tk.BOTTOM, fill=tk.BOTH)
    #    self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)

    def controls_init(self, master):
        """Initializes controls

        :param master: reference to parent object
        """
        font = 'Helvetica 15 bold'
        self.current_values = {}

        frameControlsInputOutput = tk.Frame(master=master,
                                            highlightbackground="black",
                                            highlightthickness=1
                                            )  # div
        tk.Label(master=frameControlsInputOutput,
                 text="I/O",
                 font=font,
                 ).pack(side=tk.TOP, fill=tk.BOTH)

        # frameControlsInputOutputFileName = tk.Frame(master=frameControlsInputOutput)  # div
        # tk.Label(master=frameControlsInputOutputFileName, text="File name").grid(row=1, column=0)
        # self.prefix = tk.Entry(master=frameControlsInputOutputFileName)
        # self.prefix.insert(0, "experiment")
        # self.prefix.grid(row=1, column=2)
        # frameControlsInputOutputFileName.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # def on_button_load_json():
        #    try:
        #        print('Loading from .json ...')
        #        self.init_dataframe()
        #        filename = tk.filedialog.askopenfilename(parent=self, title='Choose a file')
        #        print(filename)
        #        with open(filename, 'r') as f:
        #            temp = json.load(f)
        #
        #        for key, value in temp:
        #            # https: // stackoverflow.com / questions / 31728989 / how - i - make - json - loads - turn - str - into - int
        #            self.dfs[int(key)] = pd.DataFrame.from_dict(temp[key],
        #                                                        orient='index')  # TODO replace strings with integers
        #            self.transaction_counters[int(key)] = len(temp[key])  # TODO: check if this is correct, maybe +1 ?
        #
        #        # self.dfs = pd.read_json(path_or_buf='output/out.json', orient='index')
        #        print('Loading finished!')
        #    except Exception as e:
        #        print(e)
        #        tk.messagebox.showerror('Error', e.__str__())

        def on_button_save():
            try:
                print('Saving to .json ...')
                # self.dfs.dump()

                mask = [('Json File', '*.json'),
                        ('All Files', '*.*'),
                        ]

                save_temp = {}
                for key in self.dfs.keys():
                    save_temp[key] = self.dfs[key].to_dict(orient='index')

                # with open(name, 'x') as f:  # 'x' to create file if it doesn't exist, never overwrites

                name = datetime.datetime.now().strftime('experiment_%Y-%m-%d_%H-%M-%S')
                extension_name = tk.StringVar()
                f = tk.filedialog.asksaveasfile(filetypes=mask, initialfile=name, defaultextension=".json", mode='x',
                                                typevariable=extension_name)
                print(extension_name.get())
                if extension_name.get() == 'Json File':
                    json.dump(save_temp, f, indent=4)
                elif extension_name.get() == 'All Files':
                    json.dump(save_temp, f, indent=4)
                else:
                    print('Unknown file extension')
                    tk.messagebox.showerror('Error', 'Unknown file extension')
                f.close()

                print('Saving finished!')
            except Exception as e:
                print(e)
                tk.messagebox.showerror('Error', e.__str__())

        # tk.Button(master=frameControlsInputOutput,
        #          text="Load from *.json",
        #          command=on_button_load_json
        #          ).pack(side=tk.BOTTOM, fill=tk.X)
        tk.Button(master=frameControlsInputOutput,
                  text="Save to file",
                  command=on_button_save
                  ).pack(side=tk.BOTTOM, fill=tk.X)

        frameControlsConnection = tk.Frame(master=master,
                                           highlightbackground="black",
                                           highlightthickness=1
                                           )  # div
        tk.Label(master=frameControlsConnection, text="Select device", font=font).pack(side=tk.TOP)

        def refresh_BLE_devices():
            try:
                # print('Click1')

                devices_list = []
                for device in self.dict_of_devices_global.values():  # dictionary of devices is updated asynchronously
                    devices_list.append(str(device.address) + "/" + str(device.name) + "/" + str(device.rssi))
                devices_list.sort(key=lambda x: -float(x.split("/")[-1]))  # sort by rssi (last element)
                self.device_cbox['values'] = devices_list
            except Exception as e:
                print(e)
                tk.messagebox.showerror('Error', e.__str__())

        def apply_selected_BLE_device(event):
            # print('Click2')

            conected_device_address = self.device_cbox_value.get().split("/")[0]
            print("Connecting to address:", conected_device_address)
            self.loop.run_until_complete(self.BLE_connector_instance.disconnect())
            # replace address inside old instance
            # either use address or BLEDevice instance as parameter
            # self.BLE_connector_instance.__init__(self.dict_of_devices_global[conected_device_address])
            self.BLE_connector_instance.__init__(conected_device_address)

        self.device_cbox_value = tk.StringVar()
        self.device_cbox = tk.ttk.Combobox(master=frameControlsConnection,
                                           values=[],
                                           textvariable=self.device_cbox_value,
                                           postcommand=refresh_BLE_devices,
                                           )
        self.device_cbox.bind('<<ComboboxSelected>>', apply_selected_BLE_device)

        self.device_cbox.pack(side=tk.TOP, fill=tk.X)

        # frameControlsFeedback = tk.Frame(master=master,
        #                                 highlightbackground="black",
        #                                 highlightthickness=1,
        #                                 )  # div
        # tk.Label(master=frameControlsFeedback, text="Feedback", font=font).pack(side=tk.TOP)
        # frameControlsFeedbackGrid = tk.Frame(master=frameControlsFeedback)  # div 2
        #
        # tk.Label(master=frameControlsFeedbackGrid, text="E1").grid(row=0, column=0, sticky='W')
        # self.current_values['E1'] = tk.StringVar()
        # spin_box = tk.Spinbox(
        #    master=frameControlsFeedbackGrid,
        #    values=list(range(0, 55, 5)),
        #    textvariable=self.current_values['E1'],
        #    wrap=True)
        # spin_box.grid(row=0, column=1)
        # tk.Label(master=frameControlsFeedbackGrid, text="(mV)").grid(row=0, column=2, sticky='W')
        #
        # tk.Label(master=frameControlsFeedbackGrid, text="E2").grid(row=1, column=0, sticky='W')
        # self.current_values['E2'] = tk.StringVar()
        # spin_box = tk.Spinbox(
        #    master=frameControlsFeedbackGrid,
        #    values=list(range(0, 55, 5)),
        #    textvariable=self.current_values['E2'],
        #    wrap=True)
        # spin_box.grid(row=1, column=1)
        # tk.Label(master=frameControlsFeedbackGrid, text="(mV)").grid(row=1, column=2, sticky='W')
        #
        # tk.Label(master=frameControlsFeedbackGrid, text="Ep").grid(row=2, column=0, sticky='W')
        # self.current_values['Ep'] = tk.StringVar()
        # spin_box = tk.Spinbox(
        #    master=frameControlsFeedbackGrid,
        #    values=list(range(0, 55, 5)),
        #    textvariable=self.current_values['Ep'],
        #    wrap=True)
        # spin_box.grid(row=2, column=1)
        # tk.Label(master=frameControlsFeedbackGrid, text="(mV)").grid(row=2, column=2, sticky='W')
        #
        # tk.Label(master=frameControlsFeedbackGrid, text="Estep").grid(row=3, column=0, sticky='W')
        # self.current_values['Estep'] = tk.StringVar()
        # spin_box = tk.Spinbox(
        #    master=frameControlsFeedbackGrid,
        #    values=list(range(0, 55, 5)),
        #    textvariable=self.current_values['Estep'],
        #    wrap=True)
        # spin_box.grid(row=3, column=1)
        # tk.Label(master=frameControlsFeedbackGrid, text="(mV)").grid(row=3, column=2, sticky='W')
        #
        # tk.Label(master=frameControlsFeedbackGrid, text="Frequency").grid(row=4, column=0, sticky='W')
        # self.current_values['Frequency'] = tk.StringVar()
        # spin_box = tk.Spinbox(
        #    master=frameControlsFeedbackGrid,
        #    values=list(range(0, 55, 5)),
        #    textvariable=self.current_values['Frequency'],
        #    wrap=True)
        # spin_box.grid(row=4, column=1)
        # tk.Label(master=frameControlsFeedbackGrid, text="(Hz)").grid(row=4, column=2, sticky='W')
        #
        # tk.Label(master=frameControlsFeedbackGrid, text="Delay").grid(row=5, column=0, sticky='W')
        # self.current_values['Delay'] = tk.StringVar()
        # spin_box = tk.Spinbox(
        #    master=frameControlsFeedbackGrid,
        #    values=list(np.arange(0, 0.1, 0.01)),  # to support fractional values
        #    textvariable=self.current_values['Delay'],
        #    wrap=True)
        # spin_box.grid(row=5, column=1)
        # tk.Label(master=frameControlsFeedbackGrid, text="(s)").grid(row=5, column=2, sticky='W')
        #
        # tk.Label(master=frameControlsFeedbackGrid, text="Interval").grid(row=6, column=0, sticky='W')
        # self.current_values['Interval'] = tk.StringVar()
        # spin_box = tk.Spinbox(
        #    master=frameControlsFeedbackGrid,
        #    values=list(range(0, 65, 5)),
        #    textvariable=self.current_values['Interval'],
        #    wrap=True)
        # spin_box.grid(row=6, column=1)
        # tk.Label(master=frameControlsFeedbackGrid, text="(s)").grid(row=6, column=2, sticky='W')
        #
        # def on_button_apply():
        #    print('Button apply was clicked!')
        #    for k, v in self.current_values.items():
        #        print(k, v.get())
        #
        # tk.Button(
        #    master=frameControlsFeedback,
        #    text="Send to device",
        #    command=on_button_apply
        # ).pack(side=tk.BOTTOM, fill=tk.X)
        #
        # frameControlsPlotSettings = tk.Frame(master=master,
        #                                     highlightbackground="black",
        #                                     highlightthickness=1,
        #                                     )  # div
        # tk.Label(master=frameControlsPlotSettings, text="Plot settings", font=font).pack(side=tk.TOP)
        #
        # self.button_autoresize_X_var = tk.IntVar(value=1)
        # tk.Checkbutton(master=frameControlsPlotSettings,
        #               text="Maximize X",
        #               variable=self.button_autoresize_X_var
        #               ).pack(side=tk.TOP, fill=tk.X)
        #
        # self.button_autoresize_Y_var = tk.IntVar(value=1)
        # tk.Checkbutton(master=frameControlsPlotSettings,
        #               text="Maximize Y",
        #               variable=self.button_autoresize_Y_var
        #               ).pack(side=tk.TOP, fill=tk.X)
        #
        # self.button_pause_plotting_var = tk.IntVar(value=0)
        # tk.Checkbutton(master=frameControlsPlotSettings,
        #               text="Pause plotting",
        #               variable=self.button_pause_plotting_var
        #               ).pack(side=tk.TOP, fill=tk.X)
        #
        # frameControlsPID = tk.Frame(master=master,
        #                            highlightbackground="black",
        #                            highlightthickness=1
        #                            )  # div
        # tk.Label(master=frameControlsPID, text="PID", font=font).pack(side=tk.TOP)
        #
        frameControlsInfo = tk.Frame(master=master,
                                     highlightbackground="black",
                                     highlightthickness=1
                                     )  # div
        # tk.Label(master=frameControlsInfo, text="Info", font=font).pack(side=tk.TOP)
        # frameControlsFeedbackGrid = tk.Frame(master=frameControlsInfo)  # div 2
        # frameControlsFeedbackGrid.pack(side=tk.TOP, fill=tk.X)
        #
        # tk.Label(master=frameControlsFeedbackGrid, text="RSSI:").grid(row=0, column=0, sticky='W')
        # self.current_values['RSSI'] = tk.StringVar()
        # tk.Label(master=frameControlsFeedbackGrid, text="-127", textvariable=self.current_values['RSSI']).grid(row=0,
        #                                                                                                       column=1,
        #                                                                                                       sticky='W')

        frameControlsInputOutput.pack(side=tk.TOP, fill=tk.BOTH, expand=False)
        frameControlsConnection.pack(side=tk.TOP, fill=tk.BOTH, expand=False)
        # frameControlsFeedback.pack(side=tk.TOP, fill=tk.BOTH, expand=False)
        # frameControlsFeedbackGrid.pack(side=tk.TOP, fill=tk.BOTH, expand=False)
        # frameControlsPlotSettings.pack(side=tk.TOP, fill=tk.BOTH, expand=False)
        # frameControlsPID.pack(side=tk.TOP, fill=tk.BOTH, expand=False)
        frameControlsInfo.pack(side=tk.TOP, fill=tk.BOTH,
                               expand=True)  # this element is pushing everything else from the bottom

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

    def init_dataframe(self):
        try:
            print('Init dataframes ...')
            # self.dfs = klepto.archives.file_archive(name='output/out', dict={}, cached=True)
            self.dfs = {}
            self.transaction_counters = {}
            print('Init dataframes finished!')
        except Exception as e:
            print(e)

    # def apply_tight_layout(self, event: tk.Event):
    #    try:
    #        if event.widget.widgetName == "canvas":
    #            self.fig.tight_layout()
    #    except Exception as e:
    #        pass

    async def register_data_callback_bleak(self):
        """Sets up notifications using Bleak, and attaches callbacks"""
        self.BLE_connector_instance = BLE_connector_Bleak.BLE_connector(to_connect=False)
        # self.is_time_at_start_recorded = False
        self.transaction = Transaction(9)
        self.last_transaction_time = float('inf')
        self.offest_time = 0
        self.last_time_best_effort = float('-inf')
        self.time_changed_threshold = 0

        await self.BLE_connector_instance.keep_connections_to_device(uuids=uuids_default,
                                                                     callbacks=[self.on_new_data_callback1])

    # rx_packets_recieved = [False] * 4
    # rx_buffer = {}
    # rx_transaction_counter = 0  # can be replaced with RTC when transaction started
    # transaction_completed = False
    # rx_variable_counter = 0

    async def on_new_data_callback1(self, sender, data: bytearray):
        """Called whenever Bluetooth API receives a notification or indication

        :param sender: handle, should be unique for each uuid
        :param data: data received, several messages might be received together if data rate is high
        """

        try:
            time_delivered = datetime.datetime.utcnow().timestamp()

            # if not self.is_time_at_start_recorded:
            #    self.time_at_start = time_delivered
            #    self.is_time_at_start_recorded = True

            # time_delivered = datetime.datetime.utcnow().timestamp()
            # jitter = time_delivered - self.time_at_start - (self.transaction_counters[sender] * sample_delay)
            ## time_calculated = time_delivered - jitter
            # time_calculated = self.time_at_start + (self.transaction_counters[sender] * sample_delay)

            # data_copy = data.copy()

            # data.reverse()  # fix small endian notation
            datahex = data.hex()
            print(datahex)  # TODO

            if self.transaction.add_packet(data=data, time_delivered=time_delivered) == -1:
                # if error, maybe it is beginning of a new transaction? Try to add packet second time
                self.transaction = Transaction(9)
                if self.transaction.add_packet(data=data, time_delivered=time_delivered) == -1:
                    # print("Error of starting new transaction, datahex: ", datahex)
                    return

            data_joined = self.transaction.get_joined_data()
            if data_joined == -1:
                # print("Transaction is not complete")
                return
            print(data_joined)  # TODO

            # print(self.transaction.get_times_of_packet_creation())
            # print(min(self.transaction.get_times_of_packet_creation().values()))
            # print(self.transaction.get_times_of_delivery())
            # print(min(self.transaction.get_times_of_delivery().values()))

            # Time can only increment. If it decremented, it likely means BlueNRG chip rebooted.
            if self.last_transaction_time <= self.transaction.get_min_time_of_transaction_creation():
                # print('Time incremented')
                pass
            else:
                #  This self.offest_time might be stale,
                #  set offset after receiving and discarding 1 full Transaction to flush TX buffer
                self.time_changed_threshold += 1
                if self.time_changed_threshold > 1:
                    self.time_changed_threshold = 0

                    self.offest_time = self.transaction.get_min_time_of_transaction_delivery() - self.transaction.get_min_time_of_transaction_creation()
                    print('Time decremented, offset fixed', self.offest_time)
                else:
                    print("Likely stale data, discarding Transaction")
                    return
            self.last_transaction_time = self.transaction.get_min_time_of_transaction_creation()

            self.time_best_effort = self.transaction.get_min_time_of_transaction_creation() + self.offest_time
            self.jitter_best_effort = self.time_best_effort - self.last_time_best_effort
            self.last_time_best_effort = self.time_best_effort

            # float_length = 8  # (8 hex characters * 4 bit per character = 32 bits = 4 bytes)
            # offset = 4

            # self.rx_packets_recieved[int(datahex[0:2], 16)] = True  # False -> True, but True -> True would be error
            #
            # print(int(datahex[0:2], 16))
            # print(self.rx_packets_recieved)
            #
            # packet_counter = int(datahex[2:4], 16)
            #
            # if self.rx_transaction_counter == packet_counter:
            #    if self.transaction_completed:
            #        print('Error, transaction already received', self.rx_transaction_counter, self.rx_packets_recieved)
            #        return
            #    else:
            #        if self.rx_packets_recieved == [True] * 4:
            #            print('Transaction is completed', self.rx_transaction_counter, self.rx_packets_recieved)
            #            self.transaction_completed = True
            #            print(self.rx_buffer)
            #        else:
            #            print("Transaction in progress...", self.rx_transaction_counter, self.rx_packets_recieved)
            #            while True:
            #                try:
            #                    float_value = hex_to_float(datahex[offset:offset + float_length])
            #                    offset += float_length
            #
            #                    self.rx_buffer[self.rx_variable_counter] = float_value
            #                    self.rx_variable_counter += 1
            #
            #                    # print(N)
            #                    # print(float_value)
            #                except Exception as e:
            #                    # print(e)
            #                    # print("End of data")
            #                    # print(N)
            #                    break
            #
            #
            # else:  # starting new transaction
            #    self.rx_transaction_counter = packet_counter
            #    if self.rx_packets_recieved != [True] * 4:  # if all packets are not received yet
            #        print("Packet loss", self.rx_transaction_counter, self.rx_packets_recieved)
            #
            #    self.rx_packets_recieved = [False] * 4
            #    self.rx_buffer = {}
            #    # self.rx_transaction_counter = 0
            #    self.transaction_completed = False
            #
            #    self.rx_variable_counter = 0
            #    print("Reset rx_buffer")
            #
            ## print(struct.unpack('f', binascii.unhexlify(datahex[2:float_length + 2]))[0])

            if sender not in self.dfs.keys():  # if data recieved from this sender very first time, create new Dataframe
                self.dfs[sender] = pd.DataFrame(
                    columns=["N", "Time of creation without offset", "Time of delivery", "Offset time",
                             "Jitter best effort", "Transaction number", "Data", "Time best effort"]
                )
                self.dfs[sender] = self.dfs[sender].set_index("Time best effort")

            if sender in self.transaction_counters:
                self.transaction_counters[sender] += 1
            else:
                self.transaction_counters[sender] = 0

            #  May be not stable in case of multi threading (so have to use async)
            self.dfs[sender].loc[self.time_best_effort] = [  # time_delivered,
                self.transaction_counters[sender],
                self.transaction.get_min_time_of_transaction_creation(),
                self.transaction.get_min_time_of_transaction_delivery(),
                self.offest_time,
                # avoid infinity, it looks bad on plot
                0 if self.jitter_best_effort == float('inf') else self.jitter_best_effort,
                self.transaction.transaction_number,
                str(data_joined),
            ]  # use either time or N as an index

            self.received_new_data = True
        except Exception as e:
            print(e)
            tk.messagebox.showerror('Error', e.__str__())

    # async def update_plot_loop(self, interval):
    #    """Updates plots inside UI, at regular intervals
    #
    #    :param interval: maximum time between 2 updates, time of execution is taken in account
    #    """
    #
    #    handle = 20
    #    print('Plot started')
    #
    #    waiter = StableWaiter(interval)
    #    while True:
    #        try:
    #            await waiter.wait_async()
    #
    #            if self.received_new_data == False or self.button_pause_plotting_var.get() == True:
    #                # optimization to prevent re-drawing when there is no new data or when plotting is paused
    #                continue
    #            self.received_new_data = False
    #
    #            limits = self.subplots[1].axis()
    #            plot_width_last_frame = limits[1] - limits[0]
    #            right_side_limit_now = self.dfs[handle].index[-1]
    #
    #            # Don't plot invisible data-points, works well when there is no scaling between frames,
    #            # but may cause not rendering first several data-points properly if scale changes between steps.
    #            df_visible = self.dfs[handle].loc[
    #                         max(0, math.floor(right_side_limit_now - plot_width_last_frame) -
    #                             math.ceil(1 / sample_delay)):
    #                         right_side_limit_now + 1
    #                         ]
    #            self.lines[0].set_data(df_visible.index, df_visible['X'])
    #            self.lines[1].set_data(df_visible.index, df_visible['Y'])
    #            self.lines[2].set_data(df_visible.index, df_visible['Z'])
    #            self.lines[3].set_data(df_visible.index, df_visible['Jitter'])
    #            self.lines[4]._offsets3d = (df_visible['Z'], df_visible['Y'], df_visible['X'])
    #
    #            if self.button_autoresize_X_var.get():
    #                # Maximizes X axis
    #                self.subplots[1].set_xlim(min(self.dfs[handle].index),
    #                                          max(self.dfs[handle].index)
    #                                          )
    #                self.subplots[2].set_xlim(min(self.dfs[handle].index),
    #                                          max(self.dfs[handle].index)
    #                                          )
    #            else:
    #                # Synchronizes X-zoom across plots(uses only subplot1 as reference) and moves to right most position
    #
    #                self.subplots[1].set_xlim(right_side_limit_now - plot_width_last_frame,
    #                                          right_side_limit_now
    #                                          )
    #                self.subplots[2].set_xlim(right_side_limit_now - plot_width_last_frame,
    #                                          right_side_limit_now
    #                                          )
    #
    #            if self.button_autoresize_Y_var.get():
    #                self.subplots[1].set_ylim(min(min(df_visible['X']),
    #                                              min(df_visible['Y']),
    #                                              min(df_visible['Z'])
    #                                              ),
    #                                          max(max(df_visible['X']),
    #                                              max(df_visible['Y']),
    #                                              max(df_visible['Z'])
    #                                              )
    #                                          )
    #
    #                self.subplots[2].set_ylim(min(df_visible['Jitter']),
    #                                          max(df_visible['Jitter'])
    #                                          )
    #
    #            self.subplots[3].set_xlim(min(df_visible['Z']),
    #                                      max(df_visible['Z'])
    #                                      )
    #            self.subplots[3].set_ylim(min(df_visible['Y']),
    #                                      max(df_visible['Y'])
    #                                      )
    #            self.subplots[3].set_zlim(min(df_visible['X']),
    #                                      max(df_visible['X'])
    #                                      )
    #
    #            # if self.button_autoresize_axis_var.get():
    #            #    self.fig.tight_layout()
    #
    #            self.canvas.draw()
    #
    #        except Exception as e:
    #            print(e)
    #            tk.messagebox.showerror('Error', e.__str__())

    async def update_ui_loop(self, interval):
        """Updates UI, at regular intervals

        :param interval: maximum time between 2 updates, time of execution is taken in account
        """
        print('UI started')

        waiter = StableWaiter(interval)
        while True:
            try:
                await waiter.wait_async()
                self.update()
            except Exception as e:
                print(e)
                tk.messagebox.showerror('Error', e.__str__())

    async def start_scanning_process(self):
        """Updates RSSI, at regular intervals

        :param interval: maximum time between 2 updates, time of execution is taken in account
        """
        print('Scanning started')

        # async def stop_handle():
        #    print("Stop callback not defined")

        try:
            self.stop_scanning_handle, self.dict_of_devices_global = await self.BLE_connector_instance.start_scanning()
            await asyncio.sleep(0.1)
            print('Scanning stopped')
        except Exception as e:
            print(e)
            try:
                print('Stopping scanning because of an error')
                await self.stop_scanning_handle()
            except Exception as e2:
                print(e2)
                tk.messagebox.showerror('Error', e2.__str__())
            tk.messagebox.showerror('Error', e.__str__())

    async def battery_loop(self, interval):
        """Updates battery voltage, at regular intervals

        :param interval: maximum time between 2 updates, time of execution is taken in account
        """
        print('UI started')

        waiter = StableWaiter(interval)
        while True:
            try:
                await waiter.wait_async()
                # self.update()
            except Exception as e:
                print(e)
                tk.messagebox.showerror('Error', e.__str__())

    # def save_csv(self):
    #    print('Saving to .csv ...')
    #    self.df.to_csv(path_or_buf='output/out.csv')
    #    print('Saving finished!')


class StableWaiter:
    def __init__(self, interval):
        self.interval = interval
        self.t1 = datetime.datetime.now()

    async def wait_async(self):
        """Waits at approximately the same intervals independently of CPU speed
        (if CPU is faster than certain threshold)
        This is not mandatory, but makes UI smoother
        Can be simplified with asyncio.sleep(interval)"""

        t2 = datetime.datetime.now()
        previous_frame_time = ((t2 - self.t1).total_seconds())
        self.t1 = t2

        await asyncio.sleep(min((self.interval * 2) - previous_frame_time, self.interval))


class Packet:
    packet_number_bytes = 1
    transaction_number_bytes = 1
    time_bytes = 4
    metadata_length_total_bytes = packet_number_bytes + transaction_number_bytes + time_bytes
    datapoint_length_bytes = 2

    def __init__(self, data: bytearray, time_delivered):
        self.data = data
        self.time_delivered = time_delivered
        # self.datahex=data.hex()

        # print(data.hex())

        self.transaction_number = self.data[0]
        self.packet_number = self.data[1]
        time_packet_created_bytes = self.data[2:2 + self.time_bytes]
        time_packet_created_bytes.reverse()
        # print(time_transmitted)

        # transmit only 24 hours of time, date is not transmitted since experiment lasts only 6 hours,
        # modify if longer interval is needed
        self.time_created = datetime.datetime(year=2000, month=1, day=1,
                                              hour=time_packet_created_bytes[0],
                                              minute=time_packet_created_bytes[1],
                                              second=time_packet_created_bytes[2],
                                              microsecond=round(
                                                  1000000 * (math.pow(2, 8) - time_packet_created_bytes[3]) /
                                                  (math.pow(2, 8) - 1)
                                              )
                                              ).timestamp()
        # cprint(self.time_transmitted_datetime)

        lenght = len(data) - self.metadata_length_total_bytes  # 2 bytes are metadata
        number_of_datapoints = math.floor(lenght / self.datapoint_length_bytes)  # 2 bytes per datapoint

        self.datapoints = [-1] * number_of_datapoints

        for i in range(number_of_datapoints):
            # if self.packet_number == 3:  # last packet may have less data-points
            #     pass
            self.datapoints[i] = int(self.data[
                                     self.metadata_length_total_bytes + self.datapoint_length_bytes * i:
                                     self.metadata_length_total_bytes + self.datapoint_length_bytes * (i + 1)
                                     ][::-1].hex(),
                                     16
                                     )
        # print(self.datapoints)

    def get_datapoints(self):
        return self.datapoints


class Transaction:
    def __init__(self, size):
        self.size = size
        self.packets: {Packet} = {}
        self.transaction_number = -1
        self.finalized = False

    def add_packet(self, data: bytearray, time_delivered):
        if self.finalized:
            # print("Error, this transaction is already finalized")
            return -1

        packet = Packet(data=data, time_delivered=time_delivered)

        if self.transaction_number == -1:
            # print("First packet of new transaction received")
            self.transaction_number = packet.transaction_number

        if self.transaction_number == packet.transaction_number:
            # print("Adding new packet")
            if packet.packet_number not in self.packets:
                self.packets[packet.packet_number] = packet
            else:
                print("Error, this packet was already received")
                return -1
        else:
            print("Error, count is different, this should never happen")
            return -1

        if len(self.packets) == self.size:
            print("Transaction finished successfully")
            self.finalized = True
            return 0
        else:
            return 1

            # self.packets.append(datahex)
            # self.count=int(datahex[2:4], 16)
        # self.packets.append(datahex)
        # self.rx_packets_recieved[int(datahex[0:2], 16)] = True

    def get_joined_data(self):
        if self.finalized:
            all_datapoints = []
            for i in range(self.size):
                all_datapoints.extend(self.packets[i].get_datapoints())
            return all_datapoints
        else:
            # print("Error, not finalized yet")
            return -1

    def get_times_of_delivery(self):  # for debugging
        # should be in ascending order, but no checks are done
        if self.finalized:
            all_times_of_delivery = {}
            for i in range(self.size):
                all_times_of_delivery[i] = self.packets[i].time_delivered
            return all_times_of_delivery
        else:
            # print("Error, not finalized yet")
            return -1

    def get_min_time_of_transaction_delivery(self):
        if self.finalized:
            return min(self.get_times_of_delivery().values())
        else:
            return -1

    def get_times_of_packet_creation(self):  # for debugging
        # should be in ascending order, but no checks are done
        if self.finalized:
            all_times_of_transmitting = {}
            for i in range(self.size):
                all_times_of_transmitting[i] = self.packets[i].time_created
            return all_times_of_transmitting
        else:
            # print("Error, not finalized yet")
            return -1

    def get_min_time_of_transaction_creation(self):
        if self.finalized:
            return min(self.get_times_of_packet_creation().values())
        else:
            return


def twos_comp(val, bits):
    """Computes the 2's complement of int value val
    https://stackoverflow.com/questions/1604464/twos-complement-in-python"""

    if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)  # compute negative value
    return val  # return positive value as is


def hex_to_float(hex_str):
    """Converts hex string to float"""
    return struct.unpack('f', bytes.fromhex(hex_str))[0]


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app = App(loop)
    loop.run_forever()
