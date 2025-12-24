"""System Statistics Collection Service - CPU, Memory, Network, GPU metrics."""

import json
import os
import socket
from datetime import datetime
from typing import Optional

import pynvml
import psutil

from src.config import config
from src.logger import logger
from src.models.stats import (
    CPUStats,
    ContainerStats,
    GPUStats,
    MachineStats,
    MemoryStats,
    NetworkInterfaceStats,
)


class StatsCollector:
    """
    Collects system statistics from the host machine.

    Gathers CPU, memory, network, and GPU metrics using a combination of
    /proc filesystem parsing, psutil, and pynvml for GPU monitoring.
    """

    def __init__(self, proc_path: str = None, sys_path: str = None):
        """
        Initialize the stats collector.

        Args:
            proc_path: Path to host's /proc directory (for containerized access)
            sys_path: Path to host's /sys directory (for hardware info)
        """
        self.proc_path = proc_path or str(config.PROC_PATH)
        self.sys_path = sys_path or str(config.SYS_PATH)
        self.machine_id = config.MACHINE_ID

        # Initialize NVIDIA GPU monitoring
        try:
            pynvml.nvmlInit()
            logger.info("pynvml_initialized", gpu_count=pynvml.nvmlDeviceGetCount())
        except pynvml.NVMLError as e:
            logger.warning("pynvml_init_failed", error=str(e))

        # Storage for network rate calculation
        self._prev_net: dict[str, dict] = {}

    async def collect(self) -> MachineStats:
        """
        Collect all system statistics.

        Returns:
            MachineStats object containing all collected metrics
        """
        return MachineStats(
            machine_id=self.machine_id,
            hostname=socket.gethostname(),
            timestamp=datetime.utcnow(),
            cpu=self._collect_cpu(),
            memory=self._collect_memory(),
            network=self._collect_network(),
            gpus=self._collect_gpus(),
            containers=self._collect_containers(),
        )

    def _collect_cpu(self) -> CPUStats:
        """
        Collect CPU statistics from /proc/cpuinfo and /proc/loadavg.

        Returns:
            CPUStats object with manufacturer, model, cores, threads, and load
        """
        try:
            # Read load average
            with open(f"{self.proc_path}/loadavg") as f:
                load = float(f.read().split()[0])

            # Read CPU info
            with open(f"{self.proc_path}/cpuinfo") as f:
                cpuinfo = f.read()

            # Parse CPU info
            model = ""
            cores = 0
            threads = 0

            # Extract model name
            for line in cpuinfo.splitlines():
                if line.startswith("model name"):
                    model = line.split(":", 1)[1].strip()
                    break

            # Determine manufacturer from model string
            manufacturer = "Unknown"
            if "Intel" in model:
                manufacturer = "Intel"
            elif "AMD" in model:
                manufacturer = "AMD"

            # Get core and thread count
            # First pass: count processor entries to get total threads
            threads = len([l for l in cpuinfo.splitlines() if l.startswith("processor")])

            # Second pass: get physical core count from first processor block
            for line in cpuinfo.splitlines():
                if line.startswith("cpu cores"):
                    cores = int(line.split(":")[1].strip())
                    break

            # If cpu cores not found, assume cores = threads (no hyperthreading)
            if cores == 0:
                cores = threads

            # Calculate load percentage
            load_percent = (load * 100.0) / threads if threads > 0 else 0.0

            return CPUStats(
                manufacturer=manufacturer,
                model=model,
                cores=cores,
                threads=threads,
                load_percent=load_percent,
            )

        except Exception as e:
            logger.error("cpu_collection_failed", error=str(e))
            # Return default values on error
            return CPUStats(
                manufacturer="Unknown",
                model="Unknown",
                cores=1,
                threads=1,
                load_percent=0.0,
            )

    def _collect_memory(self) -> MemoryStats:
        """
        Collect memory statistics from /proc/meminfo.

        Returns:
            MemoryStats object with total, used, and available memory in GB
        """
        try:
            with open(f"{self.proc_path}/meminfo") as f:
                lines = f.read().splitlines()

            # Parse meminfo into dict
            info = {}
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    info[key.strip()] = value.strip()

            # Extract values (in kB)
            total_kb = int(info["MemTotal"].split()[0])
            available_kb = int(info["MemAvailable"].split()[0])

            # Convert kB to GB
            total_gb = total_kb / 1024 / 1024
            available_gb = available_kb / 1024 / 1024
            used_gb = total_gb - available_gb

            return MemoryStats(
                total_gb=total_gb,
                used_gb=used_gb,
                available_gb=available_gb,
            )

        except Exception as e:
            logger.error("memory_collection_failed", error=str(e))
            return MemoryStats(total_gb=0.0, used_gb=0.0, available_gb=0.0)

    def _collect_network(self) -> list[NetworkInterfaceStats]:
        """
        Collect network interface statistics.

        Uses /sys/class/net for interface details and psutil for traffic counters.
        Computes bytes/sec rates from delta since last collection.

        Returns:
            List of NetworkInterfaceStats objects
        """
        interfaces = []

        try:
            # Get traffic counters from psutil
            net_io = psutil.net_io_counters(pernic=True)

            # Iterate physical network interfaces
            net_class_path = f"{self.sys_path}/class/net"
            if not os.path.exists(net_class_path):
                # Fallback to /sys/class/net if sys_path not mounted
                net_class_path = "/sys/class/net"

            for iface in os.listdir(net_class_path):
                # Skip loopback and virtual interfaces
                if iface.startswith(("lo", "veth", "docker", "br-", "virbr")):
                    continue

                try:
                    # Get interface details from sysfs
                    iface_path = f"{net_class_path}/{iface}"

                    # MAC address
                    with open(f"{iface_path}/address") as f:
                        mac = f.read().strip()

                    # Link speed (Mbps) - may not exist for all interfaces
                    try:
                        with open(f"{iface_path}/speed") as f:
                            speed = int(f.read().strip())
                    except (FileNotFoundError, ValueError, OSError):
                        speed = 0

                    # MTU
                    with open(f"{iface_path}/mtu") as f:
                        mtu = int(f.read().strip())

                    # Operational state
                    with open(f"{iface_path}/operstate") as f:
                        is_up = f.read().strip() == "up"

                    # IP addresses (via psutil)
                    addrs = psutil.net_if_addrs().get(iface, [])
                    ip_addresses = [
                        addr.address
                        for addr in addrs
                        if addr.family in (socket.AF_INET, socket.AF_INET6)
                        and not addr.address.startswith("fe80:")  # Skip link-local IPv6
                    ]

                    # Traffic counters
                    counters = net_io.get(iface)
                    bytes_sent = counters.bytes_sent if counters else 0
                    bytes_recv = counters.bytes_recv if counters else 0

                    # Compute rate from previous sample
                    prev = self._prev_net.get(iface, {})
                    current_time = datetime.utcnow()
                    prev_time = prev.get("time", current_time)
                    time_delta = (current_time - prev_time).total_seconds()

                    if time_delta > 0 and "sent" in prev:
                        bytes_sent_rate = (bytes_sent - prev.get("sent", bytes_sent)) / time_delta
                        bytes_recv_rate = (bytes_recv - prev.get("recv", bytes_recv)) / time_delta
                    else:
                        # First collection or zero time delta
                        bytes_sent_rate = 0.0
                        bytes_recv_rate = 0.0

                    # Store for next delta calculation
                    self._prev_net[iface] = {
                        "time": current_time,
                        "sent": bytes_sent,
                        "recv": bytes_recv,
                    }

                    interfaces.append(
                        NetworkInterfaceStats(
                            interface=iface,
                            mac_address=mac,
                            ip_addresses=ip_addresses,
                            speed_mbps=speed,
                            mtu=mtu,
                            is_up=is_up,
                            bytes_sent=bytes_sent,
                            bytes_recv=bytes_recv,
                            bytes_sent_rate=bytes_sent_rate,
                            bytes_recv_rate=bytes_recv_rate,
                        )
                    )

                except (FileNotFoundError, IOError, OSError) as e:
                    logger.debug("network_interface_skipped", interface=iface, error=str(e))
                    continue

        except Exception as e:
            logger.error("network_collection_failed", error=str(e))

        return interfaces

    def _collect_gpus(self) -> list[GPUStats]:
        """
        Collect GPU statistics using pynvml.

        Returns:
            List of GPUStats objects with full GPU metrics
        """
        gpus = []

        try:
            gpu_count = pynvml.nvmlDeviceGetCount()

            for i in range(gpu_count):
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)

                    # Basic identification
                    uuid = pynvml.nvmlDeviceGetUUID(handle)
                    chip_model = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(chip_model, bytes):
                        chip_model = chip_model.decode()

                    # Memory info
                    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    memory_total_gb = mem.total / (1024**3)
                    memory_used_gb = mem.used / (1024**3)

                    # Utilization
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    utilization_percent = util.gpu

                    # Temperature
                    temperature_c = pynvml.nvmlDeviceGetTemperature(
                        handle, pynvml.NVML_TEMPERATURE_GPU
                    )

                    # Power info (may not be supported on all GPUs)
                    try:
                        power_draw_w = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW to W
                        power_limit_w = (
                            pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
                        )
                    except pynvml.NVMLError:
                        power_draw_w = 0.0
                        power_limit_w = 0.0

                    # PCI bus ID
                    pci_info = pynvml.nvmlDeviceGetPciInfo(handle)
                    pci_bus_id = pci_info.busId
                    if isinstance(pci_bus_id, bytes):
                        pci_bus_id = pci_bus_id.decode()

                    # Card manufacturer from PCI subsystem vendor
                    card_manufacturer = self._get_card_manufacturer(pci_bus_id)

                    # Serial number (if available)
                    try:
                        serial = pynvml.nvmlDeviceGetSerial(handle)
                        if isinstance(serial, bytes):
                            serial = serial.decode()
                    except pynvml.NVMLError:
                        serial = None

                    # Chip manufacturer (always NVIDIA for now, future-proof)
                    chip_manufacturer = "NVIDIA"

                    # Model loaded (stub for now, will be implemented with ContainerManager)
                    model_loaded = self._get_model_for_gpu(i)

                    gpus.append(
                        GPUStats(
                            index=i,
                            uuid=uuid,
                            chip_manufacturer=chip_manufacturer,
                            chip_model=chip_model,
                            card_manufacturer=card_manufacturer,
                            pci_bus_id=pci_bus_id,
                            serial=serial,
                            memory_total_gb=memory_total_gb,
                            memory_used_gb=memory_used_gb,
                            utilization_percent=utilization_percent,
                            temperature_c=temperature_c,
                            power_draw_w=power_draw_w,
                            power_limit_w=power_limit_w,
                            model_loaded=model_loaded,
                        )
                    )

                except pynvml.NVMLError as e:
                    logger.error("gpu_collection_failed", index=i, error=str(e))
                    continue

        except pynvml.NVMLError as e:
            logger.error("gpu_enumeration_failed", error=str(e))

        return gpus

    def _get_card_manufacturer(self, pci_bus_id: str) -> str:
        """
        Get GPU card manufacturer from PCI subsystem vendor.

        The PCI subsystem vendor ID identifies the card manufacturer (e.g., eVGA, MSI),
        not the chip maker (NVIDIA). We read from sysfs and look up the vendor name.

        Args:
            pci_bus_id: PCI bus ID (e.g., "0000:01:00.0")

        Returns:
            Card manufacturer name or "Unknown (vendor_id)"
        """
        sys_path = f"{self.sys_path}/bus/pci/devices/{pci_bus_id}/subsystem_vendor"

        # Fallback to /sys if sys_path not mounted
        if not os.path.exists(sys_path):
            sys_path = f"/sys/bus/pci/devices/{pci_bus_id}/subsystem_vendor"

        try:
            with open(sys_path) as f:
                vendor_id = f.read().strip()  # e.g., "0x3842"

            return self._pci_vendor_lookup(vendor_id)

        except (FileNotFoundError, IOError, OSError):
            return "Unknown"

    def _pci_vendor_lookup(self, vendor_id: str) -> str:
        """
        Look up PCI vendor name from vendor ID.

        Args:
            vendor_id: PCI vendor ID (e.g., "0x3842")

        Returns:
            Vendor name or "Unknown (vendor_id)"
        """
        # Common GPU card manufacturers (subsystem vendors)
        vendors = {
            "0x3842": "eVGA",
            "0x1462": "MSI",
            "0x1043": "ASUS",
            "0x10de": "NVIDIA",  # Reference/Founders Edition
            "0x1458": "Gigabyte",
            "0x196e": "PNY",
            "0x1569": "Palit",
            "0x1682": "XFX",
            "0x148c": "PowerColor",
            "0x1da2": "Sapphire",
            "0x1028": "Dell",
            "0x103c": "HP",
            "0x17aa": "Lenovo",
            "0x1849": "ASRock",
            "0x19da": "Zotac",
            "0x1b4c": "Colorful",
            "0x7377": "Colorful",
            "0x1d97": "Shenzhen Lianrui",
        }

        return vendors.get(vendor_id.lower(), f"Unknown ({vendor_id})")

    def _get_model_for_gpu(self, index: int) -> Optional[str]:
        """
        Get the model loaded on a specific GPU.

        This is a stub implementation for now. Will be implemented when
        ContainerManager integration is added.

        Args:
            index: GPU index

        Returns:
            Model name if loaded, None otherwise
        """
        # TODO: Implement with ContainerManager integration
        # Will query running containers and match GPU assignments
        return None

    def _collect_containers(self) -> list[ContainerStats]:
        """
        Collect statistics for running LLM containers.

        This is a stub implementation for now. Will be implemented when
        ContainerManager integration is added.

        Returns:
            List of ContainerStats objects (empty for now)
        """
        # TODO: Implement with ContainerManager integration
        # Will use podman-py to list containers with llm-serve=true label
        return []
