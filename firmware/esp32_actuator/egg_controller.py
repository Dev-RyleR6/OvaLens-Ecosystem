import tkinter as tk
from tkinter import ttk, messagebox

import serial
import serial.tools.list_ports

import threading
import time


# ============================================================
# DUCK EGG INDEX CONTROLLER
#
# Python Desktop Controller
#
# Features:
# - USB Serial connection
# - Automatic egg cycle
# - Safe STOP -> software HOME
# - Manual jogging
# - Chamber calibration
# - Output calibration
# - Speed adjustment
# - SINGLE speed & distance test
# ============================================================


class EggController:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "Duck Egg Index Controller"
        )

        self.root.geometry(
            "820x900"
        )

        self.root.minsize(
            760,
            700
        )


        # ====================================================
        # SERIAL STATE
        # ====================================================

        self.serial_connection = None

        self.running = True


        # ====================================================
        # SCROLLABLE MAIN WINDOW
        # ====================================================

        outer_frame = ttk.Frame(
            root
        )

        outer_frame.pack(
            fill="both",
            expand=True
        )


        canvas = tk.Canvas(
            outer_frame,
            highlightthickness=0
        )


        main_scrollbar = ttk.Scrollbar(
            outer_frame,
            orient="vertical",
            command=canvas.yview
        )


        self.main_frame = ttk.Frame(
            canvas
        )


        self.main_frame.bind(
            "<Configure>",
            lambda event:
                canvas.configure(
                    scrollregion=
                    canvas.bbox("all")
                )
        )


        canvas_window = (
            canvas.create_window(
                (0, 0),
                window=self.main_frame,
                anchor="nw"
            )
        )


        def resize_main_frame(event):

            canvas.itemconfigure(
                canvas_window,
                width=event.width
            )


        canvas.bind(
            "<Configure>",
            resize_main_frame
        )


        canvas.configure(
            yscrollcommand=
            main_scrollbar.set
        )


        canvas.pack(
            side="left",
            fill="both",
            expand=True
        )


        main_scrollbar.pack(
            side="right",
            fill="y"
        )


        # ====================================================
        # TITLE
        # ====================================================

        title = tk.Label(
            self.main_frame,
            text="Duck Egg Index Controller",
            font=("Arial", 22, "bold")
        )

        title.pack(
            pady=15
        )


        # ====================================================
        # ESP32 CONNECTION
        # ====================================================

        connection_frame = ttk.LabelFrame(
            self.main_frame,
            text="ESP32 Connection",
            padding=10
        )

        connection_frame.pack(
            fill="x",
            padx=20,
            pady=5
        )


        self.port_combo = ttk.Combobox(
            connection_frame,
            state="readonly",
            width=20
        )

        self.port_combo.grid(
            row=0,
            column=0,
            padx=5,
            pady=5
        )


        ttk.Button(
            connection_frame,
            text="Refresh",
            command=self.refresh_ports
        ).grid(
            row=0,
            column=1,
            padx=5
        )


        self.connect_button = ttk.Button(
            connection_frame,
            text="Connect",
            command=self.toggle_connection
        )

        self.connect_button.grid(
            row=0,
            column=2,
            padx=5
        )


        self.connection_status = tk.Label(
            connection_frame,
            text="Disconnected",
            fg="red"
        )

        self.connection_status.grid(
            row=1,
            column=0,
            columnspan=3,
            pady=5
        )


        # ====================================================
        # SYSTEM STATUS
        # ====================================================

        status_frame = ttk.LabelFrame(
            self.main_frame,
            text="System Status",
            padding=10
        )

        status_frame.pack(
            fill="x",
            padx=20,
            pady=10
        )


        self.machine_status = tk.Label(
            status_frame,
            text="OFFLINE",
            font=("Arial", 18, "bold")
        )

        self.machine_status.pack(
            pady=5
        )


        self.position_label = tk.Label(
            status_frame,
            text="Position: ---"
        )

        self.position_label.pack(
            pady=3
        )


        # ====================================================
        # MAIN CONTROLS
        # ====================================================

        controls_frame = ttk.LabelFrame(
            self.main_frame,
            text="Main Controls",
            padding=15
        )

        controls_frame.pack(
            fill="x",
            padx=20,
            pady=5
        )


        ttk.Button(
            controls_frame,
            text="START AUTO LOOP",
            command=lambda:
                self.send_command(
                    "START"
                )
        ).grid(
            row=0,
            column=0,
            padx=8,
            pady=8,
            sticky="ew"
        )


        ttk.Button(
            controls_frame,
            text="STOP & HOME",
            command=lambda:
                self.send_command(
                    "STOP"
                )
        ).grid(
            row=0,
            column=1,
            padx=8,
            pady=8,
            sticky="ew"
        )


        ttk.Button(
            controls_frame,
            text="RETURN HOME",
            command=lambda:
                self.send_command(
                    "HOME"
                )
        ).grid(
            row=1,
            column=0,
            padx=8,
            pady=8,
            sticky="ew"
        )


        ttk.Button(
            controls_frame,
            text="GET STATUS",
            command=lambda:
                self.send_command(
                    "STATUS"
                )
        ).grid(
            row=1,
            column=1,
            padx=8,
            pady=8,
            sticky="ew"
        )


        controls_frame.columnconfigure(
            0,
            weight=1
        )

        controls_frame.columnconfigure(
            1,
            weight=1
        )


        # ====================================================
        # CALIBRATION
        # ====================================================

        calibration_frame = ttk.LabelFrame(
            self.main_frame,
            text="Conveyor Calibration",
            padding=15
        )

        calibration_frame.pack(
            fill="x",
            padx=20,
            pady=10
        )


        self.cal_position_label = tk.Label(
            calibration_frame,
            text="Current Position: --- steps",
            font=("Arial", 12, "bold")
        )

        self.cal_position_label.grid(
            row=0,
            column=0,
            columnspan=6,
            pady=(0, 12)
        )


        # ====================================================
        # JOG BUTTONS
        # ====================================================

        jog_values = [
            (-100, "◀ -100"),
            (-10, "◀ -10"),
            (-1, "◀ -1"),
            (1, "+1 ▶"),
            (10, "+10 ▶"),
            (100, "+100 ▶")
        ]


        for column, (
            value,
            button_text
        ) in enumerate(jog_values):

            ttk.Button(
                calibration_frame,
                text=button_text,
                command=lambda v=value:
                    self.jog(v)
            ).grid(
                row=1,
                column=column,
                padx=4,
                pady=5,
                sticky="ew"
            )


        for column in range(6):

            calibration_frame.columnconfigure(
                column,
                weight=1
            )


        # ====================================================
        # HOME
        # ====================================================

        ttk.Button(
            calibration_frame,
            text="SET CURRENT AS HOME",
            command=self.set_home
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            padx=4,
            pady=(15, 5),
            sticky="ew"
        )


        ttk.Button(
            calibration_frame,
            text="RETURN HOME",
            command=lambda:
                self.send_command(
                    "HOME"
                )
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            padx=4,
            pady=5,
            sticky="ew"
        )


        # ====================================================
        # CHAMBER
        # ====================================================

        ttk.Button(
            calibration_frame,
            text="SAVE CHAMBER",
            command=lambda:
                self.send_command(
                    "SETCHAMBER"
                )
        ).grid(
            row=2,
            column=2,
            columnspan=2,
            padx=4,
            pady=(15, 5),
            sticky="ew"
        )


        ttk.Button(
            calibration_frame,
            text="GO TO CHAMBER",
            command=lambda:
                self.send_command(
                    "GOTO:CHAMBER"
                )
        ).grid(
            row=3,
            column=2,
            columnspan=2,
            padx=4,
            pady=5,
            sticky="ew"
        )


        # ====================================================
        # OUTPUT
        # ====================================================

        ttk.Button(
            calibration_frame,
            text="SAVE OUTPUT",
            command=lambda:
                self.send_command(
                    "SETOUTPUT"
                )
        ).grid(
            row=2,
            column=4,
            columnspan=2,
            padx=4,
            pady=(15, 5),
            sticky="ew"
        )


        ttk.Button(
            calibration_frame,
            text="GO TO OUTPUT",
            command=lambda:
                self.send_command(
                    "GOTO:OUTPUT"
                )
        ).grid(
            row=3,
            column=4,
            columnspan=2,
            padx=4,
            pady=5,
            sticky="ew"
        )


        # ====================================================
        # CALIBRATION LABELS
        # ====================================================

        self.home_label = tk.Label(
            calibration_frame,
            text="Home: 0 steps"
        )

        self.home_label.grid(
            row=4,
            column=0,
            columnspan=2,
            pady=10
        )


        self.chamber_label = tk.Label(
            calibration_frame,
            text="Chamber: ---"
        )

        self.chamber_label.grid(
            row=4,
            column=2,
            columnspan=2,
            pady=10
        )


        self.output_label = tk.Label(
            calibration_frame,
            text="Output: ---"
        )

        self.output_label.grid(
            row=4,
            column=4,
            columnspan=2,
            pady=10
        )


        # ====================================================
        # MAIN SPEED CONTROL
        # ====================================================

        speed_frame = ttk.Frame(
            calibration_frame
        )

        speed_frame.grid(
            row=5,
            column=0,
            columnspan=6,
            pady=10
        )


        tk.Label(
            speed_frame,
            text="Step Delay:"
        ).pack(
            side="left",
            padx=5
        )


        self.speed_entry = ttk.Entry(
            speed_frame,
            width=10
        )

        self.speed_entry.insert(
            0,
            "800"
        )

        self.speed_entry.pack(
            side="left",
            padx=5
        )


        tk.Label(
            speed_frame,
            text="µs"
        ).pack(
            side="left"
        )


        ttk.Button(
            speed_frame,
            text="SET SPEED",
            command=self.set_motor_speed
        ).pack(
            side="left",
            padx=10
        )


        self.speed_label = tk.Label(
            speed_frame,
            text="Current: 800 µs"
        )

        self.speed_label.pack(
            side="left",
            padx=10
        )


        # ====================================================
        # SINGLE SPEED & DISTANCE TEST
        # ====================================================

        test_frame = ttk.LabelFrame(
            self.main_frame,
            text="Speed & Distance Test",
            padding=15
        )

        test_frame.pack(
            fill="x",
            padx=20,
            pady=10
        )


        # ----------------------------------------------------
        # DISTANCE
        # ----------------------------------------------------

        tk.Label(
            test_frame,
            text="Distance:"
        ).grid(
            row=0,
            column=0,
            padx=5,
            pady=5,
            sticky="e"
        )


        self.test_distance_entry = ttk.Entry(
            test_frame,
            width=12
        )

        self.test_distance_entry.insert(
            0,
            "500"
        )

        self.test_distance_entry.grid(
            row=0,
            column=1,
            padx=5
        )


        tk.Label(
            test_frame,
            text="steps"
        ).grid(
            row=0,
            column=2,
            sticky="w"
        )


        # ----------------------------------------------------
        # TEST SPEED
        # ----------------------------------------------------

        tk.Label(
            test_frame,
            text="Step Delay:"
        ).grid(
            row=1,
            column=0,
            padx=5,
            pady=5,
            sticky="e"
        )


        self.test_speed_entry = ttk.Entry(
            test_frame,
            width=12
        )

        self.test_speed_entry.insert(
            0,
            "800"
        )

        self.test_speed_entry.grid(
            row=1,
            column=1,
            padx=5
        )


        tk.Label(
            test_frame,
            text="µs"
        ).grid(
            row=1,
            column=2,
            sticky="w"
        )


        # ----------------------------------------------------
        # TEST BUTTONS
        # ----------------------------------------------------

        ttk.Button(
            test_frame,
            text="RUN TEST",
            command=self.run_motion_test
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            padx=5,
            pady=15,
            sticky="ew"
        )


        ttk.Button(
            test_frame,
            text="STOP & HOME",
            command=self.stop_and_home
        ).grid(
            row=2,
            column=2,
            columnspan=2,
            padx=5,
            pady=15,
            sticky="ew"
        )


        ttk.Button(
            test_frame,
            text="RETURN HOME",
            command=lambda:
                self.send_command(
                    "HOME"
                )
        ).grid(
            row=3,
            column=0,
            columnspan=4,
            padx=5,
            pady=5,
            sticky="ew"
        )


        self.test_status_label = tk.Label(
            test_frame,
            text="Ready for test"
        )

        self.test_status_label.grid(
            row=4,
            column=0,
            columnspan=4,
            pady=8
        )


        for column in range(4):

            test_frame.columnconfigure(
                column,
                weight=1
            )


        # ====================================================
        # SERIAL MONITOR
        # ====================================================

        log_frame = ttk.LabelFrame(
            self.main_frame,
            text="ESP32 Serial Monitor",
            padding=10
        )

        log_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(10, 20)
        )


        self.log = tk.Text(
            log_frame,
            height=12,
            state="disabled"
        )

        self.log.pack(
            side="left",
            fill="both",
            expand=True
        )


        log_scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log.yview
        )

        log_scrollbar.pack(
            side="right",
            fill="y"
        )


        self.log.configure(
            yscrollcommand=
            log_scrollbar.set
        )


        # ====================================================
        # INITIALIZATION
        # ====================================================

        self.refresh_ports()


        self.reader_thread = threading.Thread(
            target=self.read_serial,
            daemon=True
        )

        self.reader_thread.start()


        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close_application
        )


    # ========================================================
    # REFRESH SERIAL PORTS
    # ========================================================

    def refresh_ports(self):

        ports = (
            serial.tools
            .list_ports
            .comports()
        )


        port_names = [
            port.device
            for port in ports
        ]


        self.port_combo[
            "values"
        ] = port_names


        # Prefer COM5 because that is your current ESP32 port.
        if "COM5" in port_names:

            self.port_combo.set(
                "COM5"
            )

        elif port_names:

            self.port_combo.current(
                0
            )

        else:

            self.port_combo.set(
                ""
            )


    # ========================================================
    # CONNECTION CHECK
    # ========================================================

    def is_connected(self):

        return (
            self.serial_connection
            is not None
            and
            self.serial_connection.is_open
        )


    # ========================================================
    # CONNECT / DISCONNECT
    # ========================================================

    def toggle_connection(self):

        if self.is_connected():

            self.disconnect()

            return


        port = (
            self.port_combo
            .get()
            .strip()
        )


        if not port:

            messagebox.showerror(
                "Connection Error",
                "No COM port selected."
            )

            return


        try:

            self.serial_connection = (
                serial.Serial(
                    port=port,
                    baudrate=115200,
                    timeout=0.1,
                    write_timeout=1
                )
            )


            # ESP32 often resets when the COM port opens.
            time.sleep(2)


            # Remove old boot text.
            self.serial_connection.reset_input_buffer()


            self.connection_status.config(
                text=f"Connected: {port}",
                fg="green"
            )


            self.connect_button.config(
                text="Disconnect"
            )


            self.machine_status.config(
                text="CONNECTED"
            )


            self.add_log(
                f"Connected to {port}"
            )


            # Get current ESP32 settings.
            self.send_command(
                "STATUS"
            )


        except Exception as error:

            self.serial_connection = None


            messagebox.showerror(
                "Connection Error",
                str(error)
            )


    # ========================================================
    # DISCONNECT SAFELY
    # ========================================================

    def disconnect(self):

        if self.is_connected():

            try:

                # Request stop before releasing serial port.
                self.serial_connection.write(
                    b"STOP\n"
                )

                self.serial_connection.flush()

                time.sleep(0.1)

            except Exception:

                pass


            try:

                self.serial_connection.close()

            except Exception:

                pass


        self.serial_connection = None


        self.connection_status.config(
            text="Disconnected",
            fg="red"
        )


        self.connect_button.config(
            text="Connect"
        )


        self.machine_status.config(
            text="OFFLINE"
        )


        self.add_log(
            "Disconnected."
        )


    # ========================================================
    # SEND SERIAL COMMAND
    # ========================================================

    def send_command(
        self,
        command
    ):

        if not self.is_connected():

            messagebox.showwarning(
                "Not Connected",
                "Connect to the ESP32 first."
            )

            return False


        try:

            message = (
                command + "\n"
            )


            self.serial_connection.write(
                message.encode(
                    "utf-8"
                )
            )


            self.serial_connection.flush()


            self.add_log(
                f"> {command}"
            )


            return True


        except Exception as error:

            self.add_log(
                f"SERIAL ERROR: {error}"
            )


            return False


    # ========================================================
    # JOG
    # ========================================================

    def jog(
        self,
        steps
    ):

        self.send_command(
            f"JOG:{steps}"
        )


    # ========================================================
    # SET HOME
    # ========================================================

    def set_home(self):

        if not self.is_connected():

            messagebox.showwarning(
                "Not Connected",
                "Connect to the ESP32 first."
            )

            return


        confirmed = (
            messagebox.askyesno(
                "Set Home",
                "Set the CURRENT physical "
                "position as HOME (0)?"
            )
        )


        if confirmed:

            self.send_command(
                "SETHOME"
            )


    # ========================================================
    # SET MAIN MOTOR SPEED
    # ========================================================

    def set_motor_speed(self):

        try:

            speed = int(
                self.speed_entry
                .get()
                .strip()
            )


        except ValueError:

            messagebox.showwarning(
                "Invalid Speed",
                "Enter a valid number."
            )

            return


        if not (
            200 <= speed <= 5000
        ):

            messagebox.showwarning(
                "Invalid Speed",
                "Step delay must be between "
                "200 and 5000 µs."
            )

            return


        self.send_command(
            f"SPEED:{speed}"
        )


    # ========================================================
    # SINGLE SPEED & DISTANCE TEST
    # ========================================================

    def run_motion_test(self):

        if not self.is_connected():

            messagebox.showwarning(
                "Not Connected",
                "Connect to the ESP32 first."
            )

            return


        try:

            distance = int(
                self.test_distance_entry
                .get()
                .strip()
            )


            speed = int(
                self.test_speed_entry
                .get()
                .strip()
            )


        except ValueError:

            messagebox.showwarning(
                "Invalid Test Settings",
                "Distance and speed "
                "must both be numbers."
            )

            return


        if distance <= 0:

            messagebox.showwarning(
                "Invalid Distance",
                "Distance must be greater "
                "than 0 steps."
            )

            return


        if not (
            200 <= speed <= 5000
        ):

            messagebox.showwarning(
                "Invalid Speed",
                "Step delay must be between "
                "200 and 5000 µs."
            )

            return


        # First configure requested speed.
        if not self.send_command(
            f"SPEED:{speed}"
        ):

            return


        # Then perform ONE movement.
        if not self.send_command(
            f"TEST:{distance}"
        ):

            return


        self.test_status_label.config(
            text=(
                f"Running test: "
                f"{distance} steps at "
                f"{speed} µs"
            )
        )


    # ========================================================
    # STOP & HOME
    # ========================================================

    def stop_and_home(self):

        if not self.is_connected():

            return


        self.send_command(
            "STOP"
        )


        self.test_status_label.config(
            text=(
                "Stopping and returning "
                "to HOME..."
            )
        )


    # ========================================================
    # SERIAL READER THREAD
    # ========================================================

    def read_serial(self):

        while self.running:

            try:

                if (
                    self.serial_connection
                    and
                    self.serial_connection.is_open
                    and
                    self.serial_connection.in_waiting
                ):

                    line = (
                        self.serial_connection
                        .readline()
                        .decode(
                            "utf-8",
                            errors="ignore"
                        )
                        .strip()
                    )


                    if line:

                        self.root.after(
                            0,
                            self.process_message,
                            line
                        )


            except Exception:

                pass


            time.sleep(
                0.02
            )


    # ========================================================
    # PROCESS ESP32 RESPONSE
    # ========================================================

    def process_message(
        self,
        message
    ):

        self.add_log(
            message
        )


        # ====================================================
        # POSITION
        # ====================================================

        if message.startswith(
            "POSITION:"
        ):

            value = (
                message.split(
                    ":",
                    1
                )[1]
            )


            self.position_label.config(
                text=(
                    f"Position: "
                    f"{value} steps"
                )
            )


            self.cal_position_label.config(
                text=(
                    f"Current Position: "
                    f"{value} steps"
                )
            )


        # ====================================================
        # CHAMBER POSITION
        # ====================================================

        elif message.startswith(
            "CHAMBER:"
        ):

            value = (
                message.split(
                    ":",
                    1
                )[1]
            )


            self.chamber_label.config(
                text=(
                    f"Chamber: "
                    f"{value} steps"
                )
            )


        # ====================================================
        # OUTPUT POSITION
        # ====================================================

        elif message.startswith(
            "OUTPUT:"
        ):

            value = (
                message.split(
                    ":",
                    1
                )[1]
            )


            self.output_label.config(
                text=(
                    f"Output: "
                    f"{value} steps"
                )
            )


        # ====================================================
        # SPEED
        # ====================================================

        elif message.startswith(
            "SPEED:"
        ):

            value = (
                message.split(
                    ":",
                    1
                )[1]
            )


            self.speed_label.config(
                text=(
                    f"Current: "
                    f"{value} µs"
                )
            )


            self.speed_entry.delete(
                0,
                tk.END
            )


            self.speed_entry.insert(
                0,
                value
            )


        # ====================================================
        # SAVED CHAMBER
        # ====================================================

        elif message.startswith(
            "OK:CHAMBER:"
        ):

            value = (
                message.split(
                    ":",
                    2
                )[2]
            )


            self.chamber_label.config(
                text=(
                    f"Chamber: "
                    f"{value} steps"
                )
            )


        # ====================================================
        # SAVED OUTPUT
        # ====================================================

        elif message.startswith(
            "OK:OUTPUT:"
        ):

            value = (
                message.split(
                    ":",
                    2
                )[2]
            )


            self.output_label.config(
                text=(
                    f"Output: "
                    f"{value} steps"
                )
            )


        # ====================================================
        # HOME SET
        # ====================================================

        elif message == "OK:HOME_SET":

            self.home_label.config(
                text="Home: 0 steps"
            )


        # ====================================================
        # SINGLE TEST MOVEMENT
        # ====================================================

        elif message.startswith(
            "STATE:TEST_MOVING:"
        ):

            distance = (
                message.split(
                    ":",
                    2
                )[2]
            )


            self.machine_status.config(
                text="TEST MOVING"
            )


            self.test_status_label.config(
                text=(
                    f"Moving to "
                    f"{distance} steps..."
                )
            )


        # ====================================================
        # TEST COMPLETE
        # ====================================================

        elif message == (
            "STATE:TEST_COMPLETE"
        ):

            self.machine_status.config(
                text="TEST COMPLETE"
            )


            self.test_status_label.config(
                text=(
                    "Test complete - motor "
                    "stopped at target position"
                )
            )


        # ====================================================
        # TEST INTERRUPTED
        # ====================================================

        elif message == (
            "STATE:TEST_INTERRUPTED"
        ):

            self.test_status_label.config(
                text=(
                    "Test interrupted"
                )
            )


        # ====================================================
        # GENERIC STATES
        # ====================================================

        elif message.startswith(
            "STATE:"
        ):

            state = (
                message.split(
                    ":",
                    1
                )[1]
            )


            display_state = (
                state.replace(
                    "_",
                    " "
                )
            )


            self.machine_status.config(
                text=display_state
            )


            if state == "RETURNING_HOME":

                self.test_status_label.config(
                    text=(
                        "Returning HOME..."
                    )
                )


            elif state == "HOME":

                self.test_status_label.config(
                    text=(
                        "HOME - ready"
                    )
                )


            elif state == "STOPPED":

                self.test_status_label.config(
                    text=(
                        "Stopped at HOME"
                    )
                )


        # ====================================================
        # TEST REQUIRES HOME
        # ====================================================

        elif message == (
            "ERROR:TEST_REQUIRES_HOME"
        ):

            self.test_status_label.config(
                text=(
                    "Return HOME before "
                    "running another test."
                )
            )


        # ====================================================
        # SYSTEM BUSY
        # ====================================================

        elif message == (
            "ERROR:SYSTEM_BUSY"
        ):

            self.test_status_label.config(
                text=(
                    "System busy - stop or "
                    "wait for current movement."
                )
            )


    # ========================================================
    # SERIAL LOG
    # ========================================================

    def add_log(
        self,
        message
    ):

        self.log.config(
            state="normal"
        )


        self.log.insert(
            "end",
            message + "\n"
        )


        self.log.see(
            "end"
        )


        self.log.config(
            state="disabled"
        )


    # ========================================================
    # CLOSE APPLICATION SAFELY
    # ========================================================

    def close_application(self):

        self.running = False


        if self.is_connected():

            try:

                # Ask ESP32 to stop before closing.
                self.serial_connection.write(
                    b"STOP\n"
                )

                self.serial_connection.flush()

                time.sleep(
                    0.1
                )

            except Exception:

                pass


            try:

                self.serial_connection.close()

            except Exception:

                pass


        self.root.destroy()


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = EggController(
        root
    )

    root.mainloop()