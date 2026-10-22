import pynvml

def try_read(label, fn):
    try:
        print(label, fn())
    except pynvml.NVMLError as e:
        print(label, f"not available ({e})")

pynvml.nvmlInit()
h = pynvml.nvmlDeviceGetHandleByIndex(0)

try_read("GPU:", lambda: pynvml.nvmlDeviceGetName(h))
try_read("Util %:", lambda: pynvml.nvmlDeviceGetUtilizationRates(h).gpu)
try_read("Temp C:", lambda: pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU))
try_read("Power W:", lambda: pynvml.nvmlDeviceGetPowerUsage(h) / 1000)

try:
    mem = pynvml.nvmlDeviceGetMemoryInfo(h)
    print(f"VRAM: {mem.used / 1e9:.1f} / {mem.total / 1e9:.1f} GB")
except pynvml.NVMLError:
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, value = line.split(":")
            info[key] = int(value.split()[0]) * 1024
    used = info["MemTotal"] - info["MemAvailable"]
    print(f"Shared memory: {used / 1e9:.1f} / {info['MemTotal'] / 1e9:.1f} GB")

pynvml.nvmlShutdown()
