import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time


class ServoController:
    def __init__(self, root):
        self.root = root
        self.root.title("Duck Egg Sorter Controller")
        self.root.geometry("650x720")
        self.root.minsize(600, 650)

        self.serial_connection = None
        self.running = True

        title = tk.Label(
            root,
            text="Duck Egg Sorter Controller",
            font=("Arial", 22, "bold")
        )
        title.pack(pady=15)

        # =========================
        # CONNECTION
        # =========================
        connection_frame = ttk.LabelFrame(
            root,
            text="Servo ESP32 Connection",
            padding=10
        )
        connection_frame.pack(fill="x", padx=20, pady=5)

        self.port_combo = ttk.Combobox(
            connection_frame,
            state="readonly",
            width=20
        )
        self.port_combo.grid(row=0, column=0, padx=5, pady=5)

        ttk.Button(
            connection_frame,
            text="Refresh",
            command=self.refresh_ports
        ).grid(row=0, column=1, padx=5)

        self.connect_button = ttk.Button(
            connection_frame,
            text="Connect",
            command=self.toggle_connection
        )
        self.connect_button.grid(row=0, column=2, padx=5)

        self.connection_status = tk.Label(
            connection_frame,
            text="Disconnected",
            fg="red"
        )
        self.connection_status.grid(row=1, column=0, columnspan=3, pady=5)

        # =========================
        # SERVO STATUS
        # =========================
        status_frame = ttk.LabelFrame(
            root,
            text="Servo Status",
            padding=10
        )
        status_frame.pack(fill="x", padx=20, pady=10)

        self.state_label = tk.Label(
            status_frame,
            text="OFFLINE",
            font=("Arial", 18, "bold")
        )
        self.state_label.pack(pady=5)

        self.angle_label = tk.Label(
            status_frame,
            text="Current Angle: ---°",
            font=("Arial", 12)
        )
        self.angle_label.pack(pady=5)

        # =========================
        # MANUAL SERVO CONTROL
        # =========================
        manual_frame = ttk.LabelFrame(
            root,
            text="Manual Servo Test",
            padding=15
        )
        manual_frame.pack(fill="x", padx=20, pady=10)

        self.angle_slider = ttk.Scale(
            manual_frame,
            from_=0,
            to=180,
            orient="horizontal",
            command=self.slider_changed
        )
        self.angle_slider.set(90)
        self.angle_slider.pack(fill="x", padx=10, pady=10)

        self.selected_angle_label = tk.Label(
            manual_frame,
            text="Selected: 90°"
        )
        self.selected_angle_label.pack(pady=5)

        angle_entry_frame = ttk.Frame(manual_frame)
        angle_entry_frame.pack(pady=5)

        tk.Label(
            angle_entry_frame,
            text="Angle:"
        ).pack(side="left", padx=5)

        self.angle_entry = ttk.Entry(
            angle_entry_frame,
            width=8
        )
        self.angle_entry.insert(0, "90")
        self.angle_entry.pack(side="left", padx=5)

        ttk.Button(
            angle_entry_frame,
            text="MOVE",
            command=self.move_to_entry_angle
        ).pack(side="left", padx=5)

        # Quick angles
        quick_frame = ttk.Frame(manual_frame)
        quick_frame.pack(pady=10)

        for angle in [0, 30, 45, 60, 90, 120, 150, 180]:
            ttk.Button(
                quick_frame,
                text=f"{angle}°",
                command=lambda a=angle: self.move_servo(a)
            ).pack(side="left", padx=2)

        # Fine control
        fine_frame = ttk.Frame(manual_frame)
        fine_frame.pack(pady=10)

        ttk.Button(
            fine_frame,
            text="-10°",
            command=lambda: self.adjust_angle(-10)
        ).pack(side="left", padx=5)

        ttk.Button(
            fine_frame,
            text="-1°",
            command=lambda: self.adjust_angle(-1)
        ).pack(side="left", padx=5)

        ttk.Button(
            fine_frame,
            text="+1°",
            command=lambda: self.adjust_angle(1)
        ).pack(side="left", padx=5)

        ttk.Button(
            fine_frame,
            text="+10°",
            command=lambda: self.adjust_angle(10)
        ).pack(side="left", padx=5)

        # =========================
        # SORTING PRESETS
        # =========================
        preset_frame = ttk.LabelFrame(
            root,
            text="Sorting Position Calibration",
            padding=15
        )
        preset_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(preset_frame, text="Fertile:").grid(
            row=0, column=0, padx=5, pady=5
        )
        self.fertile_entry = ttk.Entry(preset_frame, width=8)
        self.fertile_entry.insert(0, "30")
        self.fertile_entry.grid(row=0, column=1, padx=5)

        ttk.Button(
            preset_frame,
            text="Save",
            command=self.save_fertile
        ).grid(row=0, column=2, padx=5)

        ttk.Button(
            preset_frame,
            text="TEST FERTILE",
            command=lambda: self.send_command("SORT:FERTILE")
        ).grid(row=0, column=3, padx=5)

        tk.Label(preset_frame, text="Infertile:").grid(
            row=1, column=0, padx=5, pady=5
        )
        self.infertile_entry = ttk.Entry(preset_frame, width=8)
        self.infertile_entry.insert(0, "90")
        self.infertile_entry.grid(row=1, column=1, padx=5)

        ttk.Button(
            preset_frame,
            text="Save",
            command=self.save_infertile
        ).grid(row=1, column=2, padx=5)

        ttk.Button(
            preset_frame,
            text="TEST INFERTILE",
            command=lambda: self.send_command("SORT:INFERTILE")
        ).grid(row=1, column=3, padx=5)

        ttk.Button(
            preset_frame,
            text="RESET / NEUTRAL",
            command=lambda: self.send_command("RESET")
        ).grid(
            row=3,
            column=0,
            columnspan=4,
            padx=5,
            pady=15,
            sticky="ew"
        )

        ttk.Button(
            root,
            text="GET STATUS",
            command=lambda: self.send_command("STATUS")
        ).pack(pady=5)

        # =========================
        # SERIAL MONITOR
        # =========================
        log_frame = ttk.LabelFrame(
            root,
            text="Servo ESP32 Serial Monitor",
            padding=10
        )
        log_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.log = tk.Text(
            log_frame,
            height=10,
            state="disabled"
        )
        self.log.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log.yview
        )
        scrollbar.pack(side="right", fill="y")

        self.log.configure(yscrollcommand=scrollbar.set)

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

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        names = [port.device for port in ports]
        self.port_combo["values"] = names

        if names:
            self.port_combo.current(0)
        else:
            self.port_combo.set("")

    def is_connected(self):
        return (
            self.serial_connection is not None
            and self.serial_connection.is_open
        )

    def toggle_connection(self):
        if self.is_connected():
            self.disconnect()
            return

        port = self.port_combo.get().strip()

        if not port:
            messagebox.showerror(
                "Connection Error",
                "Select a COM port."
            )
            return

        try:
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=115200,
                timeout=0.1,
                write_timeout=1
            )

            # ESP32 may reset when serial port opens.
            time.sleep(2)

            self.serial_connection.reset_input_buffer()

            self.connection_status.config(
                text=f"Connected: {port}",
                fg="green"
            )
            self.connect_button.config(text="Disconnect")
            self.state_label.config(text="CONNECTED")
            self.add_log(f"Connected to {port}")

            self.send_command("STATUS")

        except Exception as error:
            self.serial_connection = None
            messagebox.showerror(
                "Connection Error",
                str(error)
            )

    def disconnect(self):
        if self.is_connected():
            try:
                self.serial_connection.close()
            except Exception:
                pass

        self.serial_connection = None

        self.connection_status.config(
            text="Disconnected",
            fg="red"
        )
        self.connect_button.config(text="Connect")
        self.state_label.config(text="OFFLINE")
        self.add_log("Disconnected.")

    def send_command(self, command):
        if not self.is_connected():
            messagebox.showwarning(
                "Not Connected",
                "Connect to the Servo ESP32 first."
            )
            return False

        try:
            self.serial_connection.write(
                (command + "\n").encode("utf-8")
            )
            self.serial_connection.flush()

            self.add_log(f"> {command}")
            return True

        except Exception as error:
            self.add_log(f"SERIAL ERROR: {error}")
            return False

    def move_servo(self, angle):
        angle = int(angle)
        angle = max(0, min(180, angle))

        self.angle_slider.set(angle)

        self.angle_entry.delete(0, tk.END)
        self.angle_entry.insert(0, str(angle))

        self.selected_angle_label.config(
            text=f"Selected: {angle}°"
        )

        self.send_command(f"SERVO:{angle}")

    def move_to_entry_angle(self):
        try:
            angle = int(
                self.angle_entry.get().strip()
            )

        except ValueError:
            messagebox.showwarning(
                "Invalid Angle",
                "Enter an angle from 0 to 180."
            )
            return

        if not 0 <= angle <= 180:
            messagebox.showwarning(
                "Invalid Angle",
                "Angle must be between 0 and 180."
            )
            return

        self.move_servo(angle)

    def adjust_angle(self, amount):
        try:
            current = int(
                self.angle_entry.get().strip()
            )
        except ValueError:
            current = 90

        new_angle = max(
            0,
            min(
                180,
                current + amount
            )
        )

        self.move_servo(new_angle)

    def slider_changed(self, value):
        angle = round(float(value))

        self.selected_angle_label.config(
            text=f"Selected: {angle}°"
        )

        self.angle_entry.delete(0, tk.END)
        self.angle_entry.insert(0, str(angle))

    def get_valid_angle(self, entry):
        try:
            angle = int(
                entry.get().strip()
            )
        except ValueError:
            messagebox.showwarning(
                "Invalid Angle",
                "Angle must be a number."
            )
            return None

        if not 0 <= angle <= 180:
            messagebox.showwarning(
                "Invalid Angle",
                "Angle must be between 0 and 180."
            )
            return None

        return angle

    def save_fertile(self):
        angle = self.get_valid_angle(
            self.fertile_entry
        )
        if angle is not None:
            self.send_command(
                f"SET_FERTILE:{angle}"
            )

    def save_infertile(self):
        angle = self.get_valid_angle(
            self.infertile_entry
        )
        if angle is not None:
            self.send_command(
                f"SET_INFERTILE:{angle}"
            )

    def read_serial(self):
        while self.running:
            try:
                if (
                    self.serial_connection
                    and self.serial_connection.is_open
                    and self.serial_connection.in_waiting
                ):
                    message = (
                        self.serial_connection
                        .readline()
                        .decode("utf-8", errors="ignore")
                        .strip()
                    )

                    if message:
                        self.root.after(
                            0,
                            self.process_message,
                            message
                        )

            except Exception:
                pass

            time.sleep(0.02)

    def process_message(self, message):
        self.add_log(message)

        if message.startswith("ANGLE:"):
            try:
                value = int(
                    message.split(":", 1)[1]
                )
            except ValueError:
                return

            self.angle_label.config(
                text=f"Current Angle: {value}°"
            )
            self.angle_slider.set(value)
            self.angle_entry.delete(0, tk.END)
            self.angle_entry.insert(0, str(value))

        elif message.startswith("FERTILE:"):
            value = message.split(":", 1)[1]
            self.fertile_entry.delete(0, tk.END)
            self.fertile_entry.insert(0, value)

        elif message.startswith("INFERTILE:"):
            value = message.split(":", 1)[1]
            self.infertile_entry.delete(0, tk.END)
            self.infertile_entry.insert(0, value)

        elif message.startswith("STATE:"):
            state = message.split(":", 1)[1]
            self.state_label.config(text=state)

    def add_log(self, message):
        self.log.config(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def close_application(self):
        self.running = False

        if self.is_connected():
            try:
                self.serial_connection.close()
            except Exception:
                pass

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ServoController(root)
    root.mainloop()
