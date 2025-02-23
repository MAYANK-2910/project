import tkinter as tk
from tkinter import ttk
import psutil
import cpuinfo
import platform
import os
import math
import time
import ctypes
from collections import deque
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Load the overclocking shared library (compiled from the C code)
try:
    oc_lib = ctypes.CDLL('./overclock.so')
    # Set the function signature for set_cpu_multiplier(core, multiplier)
    oc_lib.set_cpu_multiplier.argtypes = [ctypes.c_int, ctypes.c_int]
except Exception as e:
    print("Overclock library not found:", e)
    oc_lib = None

def get_motherboard_info():
    os_name = platform.system()
    try:
        if os_name == "Windows":
            import wmi
            w = wmi.WMI()
            for board in w.Win32_BaseBoard():
                return f"{board.Manufacturer} {board.Product}".strip()
        elif os_name == "Linux":
            vendor = product = "Unknown"
            with open('/sys/class/dmi/id/board_vendor', 'r') as f:
                vendor = f.read().strip()
            with open('/sys/class/dmi/id/board_name', 'r') as f:
                product = f.read().strip()
            return f"{vendor} {product}"
        else:
            return "Unsupported OS"
    except Exception as e:
        return "Unavailable"

def get_system_info():
    info = {}
    cpu = cpuinfo.get_cpu_info()
    mem = psutil.virtual_memory()
    
    info['cpu'] = {
        'name': cpu.get('brand_raw', 'Unknown'),
        'arch': cpu.get('arch_string_raw', 'Unknown'),
        'cores': psutil.cpu_count(logical=False),
        'threads': psutil.cpu_count(logical=True),
        'freq': psutil.cpu_freq().current if psutil.cpu_freq() else None
    }
    
    info['system'] = {
        'os': f"{platform.system()} {platform.release()}",
        'version': platform.version(),
        'memory': {
            'total': mem.total // (1024**3),
            'available': mem.available // (1024**3)
        }
    }
    
    info['motherboard'] = get_motherboard_info()
    return info

class OverclockingGUI:
    def __init__(self, master):
        self.master = master
        self.system_info = get_system_info()
        self.running = True
        self.setup_gui()
        self.setup_overclocking()  # additional setup if needed

    def setup_gui(self):
        self.master.title("PyCPU Control Center")
        self.master.geometry("1280x800")
        
        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.master)
        self.tabs = {
            'info': ttk.Frame(self.notebook),
            'monitor': ttk.Frame(self.notebook),
            'overclock': ttk.Frame(self.notebook)
        }
        self.notebook.add(self.tabs['info'], text="Info")
        self.notebook.add(self.tabs['monitor'], text="Monitor")
        self.notebook.add(self.tabs['overclock'], text="Overclock")
        self.notebook.pack(expand=True, fill='both')
        
        # Create each tab's content
        self.create_info_tab()
        self.create_monitor_tab()
        self.create_overclock_tab()
    
    def create_info_tab(self):
        info = self.system_info
        info_text = (
            "----------------- System Information -----------------\n\n"
            "Processor Information:\n"
            f"Name: {info['cpu']['name']}\n"
            f"Architecture: {info['cpu']['arch']}\n"
            f"Cores (Physical): {info['cpu']['cores']}\n"
            f"Threads (Logical): {info['cpu']['threads']}\n"
            f"Current Frequency: {info['cpu']['freq']} MHz\n\n"
            "Operating System:\n"
            f"OS: {info['system']['os']}\n"
            f"Version: {info['system']['version']}\n\n"
            "Memory Information:\n"
            f"Total RAM: {info['system']['memory']['total']} GB\n"
            f"Available RAM: {info['system']['memory']['available']} GB\n\n"
            "Motherboard Information:\n"
            f"Model: {info['motherboard']}\n"
            "--------------------------------------------------------"
        )
        label = tk.Label(self.tabs['info'], text=info_text, justify=tk.LEFT, font=("Helvetica", 10))
        label.pack(anchor="w", padx=10, pady=10)
    
    def create_monitor_tab(self):
        # Create a frame for the CPU monitoring graph
        self.monitor_frame = ttk.Frame(self.tabs['monitor'])
        self.monitor_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        self.num_cores = psutil.cpu_count(logical=True)
        self.fig = Figure(figsize=(8, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("CPU Usage Monitor")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Usage (%)")
        self.ax.set_ylim(0, 100)
        
        self.lines = []
        self.data = []
        self.x_data = []
        self.start_time = time.time()
        
        # Initialize a line (with a fixed-length deque) for each core
        for i in range(self.num_cores):
            line, = self.ax.plot([], [], label=f"Core {i}", linewidth=1.5)
            self.lines.append(line)
            self.data.append(deque(maxlen=300))
        self.ax.legend(fontsize=8)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.monitor_frame)
        self.canvas.get_tk_widget().pack(expand=True, fill='both')
        
        # Start updating the monitor
        self.update_monitor()
    
    def update_monitor(self):
        current_time = time.time() - self.start_time
        self.x_data.append(current_time)
        usage = psutil.cpu_percent(percpu=True)
        for i, u in enumerate(usage):
            self.data[i].append(u)
            # Update each line with the latest data from the deque
            x_vals = list(self.x_data)[-len(self.data[i]):]
            self.lines[i].set_data(x_vals, list(self.data[i]))
        self.ax.set_xlim(max(0, current_time - 60), current_time + 1)
        self.canvas.draw_idle()
        if self.running:
            self.master.after(1000, self.update_monitor)
    
    def create_overclock_tab(self):
        frame = self.tabs['overclock']
        title = tk.Label(frame, text="CPU Overclocking Controls", font=('Arial', 14))
        title.pack(pady=10)
        
        warning = tk.Label(frame, text="WARNING: Overclocking can damage hardware!", fg='red')
        warning.pack(pady=5)
        
        # Create overclock controls for each physical core
        self.core_controls = []
        physical_cores = self.system_info['cpu']['cores']
        for core in range(physical_cores):
            cf = ttk.Frame(frame)
            cf.pack(pady=2, padx=10, fill='x')
            
            label = ttk.Label(cf, text=f"Core {core} Controls:")
            label.pack(side=tk.LEFT)
            
            # Multiplier slider: range is example values; adjust as needed.
            mult_scale = ttk.Scale(cf, from_=20, to=60, orient='horizontal',
                                   command=lambda v, c=core: self.update_multiplier(c, v))
            mult_scale.set(30)  # default multiplier
            mult_scale.pack(side=tk.LEFT, padx=5, fill='x', expand=True)
            
            # Voltage slider: dummy control for display purposes.
            volt_scale = ttk.Scale(cf, from_=0.8, to=1.5, orient='horizontal',
                                   command=lambda v, c=core: self.update_voltage(c, v))
            volt_scale.set(1.0)  # default voltage
            volt_scale.pack(side=tk.LEFT, padx=5, fill='x', expand=True)
            
            self.core_controls.append((mult_scale, volt_scale))
        
        self.oc_status = tk.Label(frame, text="Ready", font=("Arial", 10))
        self.oc_status.pack(pady=10)
    
    def update_multiplier(self, core, value):
        try:
            if oc_lib:
                # Call the C library function set_cpu_multiplier(core, multiplier)
                oc_lib.set_cpu_multiplier(core, int(float(value)))
                self.oc_status.config(text=f"Core {core} multiplier set to {int(float(value))}", fg='black')
            else:
                self.oc_status.config(text="Overclock library not available", fg='red')
        except Exception as e:
            self.oc_status.config(text=f"Error: {str(e)}", fg='red')
    
    def update_voltage(self, core, value):
        # Dummy implementation for voltage control; requires hardware-specific code.
        self.oc_status.config(text=f"Core {core} voltage adjustment: {float(value):.2f}V", fg='black')
    
    def setup_overclocking(self):
        # Additional overclocking setup can be implemented here if needed.
        pass
    
    def safe_exit(self):
        self.running = False
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = OverclockingGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.safe_exit)
    root.mainloop()
