# predator-sense-317-55-for-linux
Linux PredatorSense replacement with fan control, RGB keyboard, battery management and system monitoring.

## Dependencies

### Required

- gtk3
- python-gobject
- python-cairo
- polkit

### Recommended

- python-psutil

### Optional

- nvidia-utils (GPU monitoring)
- xclip (RGB color picker clipboard support)

### Hardware / Kernel Requirements

- Acer Predator laptop
- acer-wmi PredatorSense interface
- linuwu_sense kernel module (RGB support)
- ACPI platform_profile support
- Intel P-State driver
- NVIDIA GPU (optional)

### Installation (Arch / Manjaro)

```bash
sudo pacman -S gtk3 python-gobject python-cairo python-psutil polkit nvidia-utils xclip
```
