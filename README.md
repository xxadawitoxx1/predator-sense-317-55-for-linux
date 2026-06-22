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
## Screenshots

### Home
<img width="1895" height="1007" alt="Home" src="https://github.com/user-attachments/assets/35ca5df9-2514-4cbb-a08c-dd4a4af4ad1c" />

### Temperatures
<img width="1897" height="1018" alt="Temperatures" src="https://github.com/user-attachments/assets/6beee1ce-bda0-4676-9bf3-42af23443208" />

### System Usage
<img width="1898" height="1013" alt="System Usage" src="https://github.com/user-attachments/assets/8ace405f-529c-4e6b-a3f9-3fed47ceb4da" />

### GPU
<img width="1890" height="1012" alt="GPU" src="https://github.com/user-attachments/assets/0682d2a6-199b-4ff3-b75c-a0ea4eccd911" />

### Network
<img width="1883" height="1012" alt="Network" src="https://github.com/user-attachments/assets/d9184fff-ea23-49fb-85bd-28b5422758fb" />

### Fans
<img width="1894" height="1022" alt="Fans" src="https://github.com/user-attachments/assets/ada8d4f3-7fd8-4fae-a30e-96564d20db34" />

### Power
<img width="1888" height="1013" alt="Power" src="https://github.com/user-attachments/assets/91f43003-ea3a-4e43-90d8-2d218de80d9b" />

### Backlight
<img width="1903" height="1018" alt="Backlight" src="https://github.com/user-attachments/assets/ae1cb43a-c0fb-4f0b-a46f-98134e31a78c" />

### Options
<img width="1890" height="1006" alt="Options" src="https://github.com/user-attachments/assets/3ab5d459-8aa4-4b6c-b3cd-e68674a040ae" />

### Advanced
<img width="1874" height="1011" alt="Advanced" src="https://github.com/user-attachments/assets/fdbaef6d-1e6e-47c2-b2a1-f632be8b6321" />
