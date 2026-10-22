"""Reads live GPU stats for the fire and the hardware panels."""
import pynvml

pynvml.nvmlInit()
_gpu = pynvml.nvmlDeviceGetHandleByIndex(0)


def _safe(read, default=None):
    """Run one reading; if the GPU doesn't support it, return the default."""
    try:
        return read()
    except pynvml.NVMLError:
        return default


def _shared_memory():
    """The GB10 shares memory with the CPU, so read it from the system instead."""
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, value = line.split(":")
            info[key] = int(value.split()[0]) * 1024  # the file lists kB
    return info["MemTotal"] - info["MemAvailable"], info["MemTotal"]


def read_stats() -> dict:
    """Return one snapshot of the GPU's state."""
    util = _safe(lambda: pynvml.nvmlDeviceGetUtilizationRates(_gpu).gpu, 0)
    temp = _safe(lambda: pynvml.nvmlDeviceGetTemperature(_gpu, pynvml.NVML_TEMPERATURE_GPU))
    power = _safe(lambda: pynvml.nvmlDeviceGetPowerUsage(_gpu) / 1000)

    mem = _safe(lambda: pynvml.nvmlDeviceGetMemoryInfo(_gpu))
    if mem is not None:
        used, total = mem.used, mem.total
    else:
        used, total = _shared_memory()

    return {
        "gpu": util,
        "temp": temp,
        "power": round(power, 1) if power is not None else None,
        "mem_used": round(used / 1e9, 1),
        "mem_total": round(total / 1e9, 1),
    }