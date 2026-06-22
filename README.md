# predator-sense-317-55-for-linux

The application created due to the lack of a working Predator Sense substitute on this model does not make it clear that it will work on other versions of Predator. The only purpose of this application was to make my personal laptop stop making noises like a jet.

If you encounter a problem, please write in the issue tab. I'll try to help, but I don't promise that it will work 100% :P

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
