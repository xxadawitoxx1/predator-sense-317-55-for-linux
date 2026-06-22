#!/usr/bin/env python3
"""
Predator Control — Acer Predator PH317-55 / Manjaro / Hyprland
Zależności: sudo pacman -S python-gobject python-cairo gtk3
Opcjonalnie: python-psutil (dla usage/network)
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf

import os, sys, subprocess, threading, math, json, time
from collections import deque

# ─── ŚCIEŻKI ─────────────────────────────────────────────────────────────────
PS          = "/sys/devices/platform/acer-wmi/predator_sense"
FAN_SPEED   = f"{PS}/fan_speed"
BATT_LIMIT  = f"{PS}/battery_limiter"
LCD_OD      = f"{PS}/lcd_override"
USB_CHG     = f"{PS}/usb_charging"
BOOT_ANIM   = f"{PS}/boot_animation_sound"
BATT_CAL    = f"{PS}/battery_calibration"

PLATFORM_PROFILE         = "/sys/firmware/acpi/platform_profile"
PLATFORM_PROFILE_CHOICES = "/sys/firmware/acpi/platform_profile_choices"

TEMP_PKG    = "/sys/class/thermal/thermal_zone6/temp"
HWMON_CORE  = "/sys/class/hwmon/hwmon4"
BATT_CAP    = "/sys/class/power_supply/BAT1/capacity"
BATT_STS    = "/sys/class/power_supply/BAT1/status"
BATT_VOLT   = "/sys/class/hwmon/hwmon2/in0_input"
BATT_FULL   = "/sys/class/power_supply/BAT1/charge_full"
BATT_DESIGN = "/sys/class/power_supply/BAT1/charge_full_design"
BATT_CYCLES = "/sys/class/power_supply/BAT1/cycle_count"

# RGB – linuwu_sense (four_zoned_kb sysfs)
RGB_FOUR_ZONE = "/sys/module/linuwu_sense/drivers/platform:acer-wmi/acer-wmi/four_zoned_kb/per_zone_mode"

PROFILES = ["quiet", "balanced", "balanced-performance", "performance"]
PROFILE_LABELS = {
    "quiet":               "SILENT",
    "balanced":            "BALANCED",
    "balanced-performance":"PERFORMANCE",
    "performance":         "TURBO",
}
PROFILE_ICONS = {
    "quiet": " ", "balanced": " ",
    "balanced-performance": " ", "performance": " ",
}

# ─── CSS (MONOCHROME / CZARNO-BIAŁE GUI) ──────────────────────────────────────
CSS = """
* {
    font-family: 'Cantarell', 'Ubuntu', 'Liberation Sans', sans-serif;
    color: #ffffff;
}
window {
    background-color: #0b0b0b;
}

/* ── SIDEBAR ── */
.sidebar {
    background-color: #121212;
    border-right: 1px solid #222222;
    min-width: 190px;
}
.sidebar-logo {
    background-color: #1a1a1a;
    border-bottom: 1px solid #222222;
    padding: 18px 12px 14px 12px;
}
.logo-title {
    font-size: 14px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 4px;
}
.logo-sub {
    font-size: 9px;
    color: #888888;
    letter-spacing: 3px;
    margin-top: 3px;
}
.nav-btn {
    background-color: transparent;
    color: #aaaaaa;
    border: none;
    border-radius: 0px;
    padding: 11px 16px;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 2px;
    border-left: 3px solid transparent;
}
.nav-btn:hover {
    background-color: #1a1a1a;
    color: #ffffff;
    border-left-color: #555555;
}
.nav-btn.nav-active {
    background-color: #222222;
    color: #ffffff;
    border-left: 3px solid #ffffff;
    font-weight: 700;
}
.nav-btn label { color: inherit; }
.nav-section-lbl {
    font-size: 8px;
    color: #666666;
    letter-spacing: 3px;
    padding: 12px 16px 4px 16px;
}

/* ── CONTENT ── */
.content-area { background-color: #0b0b0b; }
.page-title {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 3px;
}
.page-sub {
    font-size: 9px;
    color: #888888;
    letter-spacing: 3px;
}
.page-header {
    background-color: #121212;
    border-bottom: 1px solid #222222;
    padding: 14px 20px;
}

/* ── CARDS ── */
.card {
    background-color: #121212;
    border: 1px solid #222222;
    border-radius: 4px;
    padding: 14px;
    margin: 5px;
}
.card-cpu, .card-gpu, .card-fan, .card-batt, .card-rgb, .card-net, .card-usage { 
    border-color: #222222; 
    border-top: 2px solid #ffffff; 
}

/* ── LABELS ── */
.sec-lbl, .sec-lbl-rgb, .sec-lbl-net, .sec-lbl-usage {
    font-size: 11px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 2px;
    margin-left: 5px;
}
.micro-lbl {
    font-size: 10px;
    font-weight: 500;
    color: #888888;
    letter-spacing: 2px;
}
.stat-lbl {
    font-size: 13px;
    font-weight: 500;
    color: #cccccc;
}
.val-lbl {
    font-size: 13px;
    font-weight: 600;
    color: #ffffff;
}
.big-val, .big-val-warm {
    font-size: 42px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -1px;
}
.big-unit {
    font-size: 14px;
    color: #888888;
}
.rpm-lbl, .warn-lbl, .ok-lbl, .cyan-lbl, .rgb-lbl, .net-lbl, .usage-lbl {
    font-size: 24px;
    font-weight: 700;
    color: #ffffff;
}

/* ── PROGRESS BARS ── */
progressbar trough {
    background-color: #1a1a1a;
    border: 1px solid #222222;
    border-radius: 2px;
    min-height: 4px;
}
progressbar progress, .pb-cool progress, .pb-fan progress, .pb-batt progress, .pb-warm progress, .pb-rgb progress, .pb-net progress, .pb-usage progress {
    border-radius: 2px;
    background: #ffffff;
}

/* ── BUTTONS ── */
button {
    background-color: #1a1a1a;
    color: #ffffff;
    border: 1px solid #333333;
    border-radius: 3px;
    padding: 9px 14px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
}
button:hover {
    background-color: #252525;
    border-color: #555555;
    color: #ffffff;
}
button.active, button.turbo-active, button.profile-btn.active, button.profile-btn.turbo-active, button.rgb-btn.active {
    background-color: #ffffff;
    border-color: #ffffff;
    color: #0b0b0b;
    font-weight: 700;
}
button.active label, button.turbo-active label, button.profile-btn.active label, button.profile-btn.turbo-active label, button.rgb-btn.active label {
    color: #0b0b0b;
}
button.turbo-btn, button.action-btn, button.profile-btn, button.rgb-btn, button.rgb-off {
    background-color: #1a1a1a;
    border-color: #333333;
    color: #ffffff;
}
button.turbo-btn:hover, button.action-btn:hover, button.profile-btn:hover, button.rgb-btn:hover, button.rgb-off:hover {
    border-color: #ffffff;
    background-color: #252525;
    color: #ffffff;
}

/* ── SCALES ── */
scale trough {
    background-color: #1a1a1a;
    border: 1px solid #222222;
    border-radius: 2px;
    min-height: 4px;
}
scale highlight, .scale-fan highlight, .scale-batt highlight, .scale-rgb highlight {
    background: #ffffff;
    border-radius: 2px;
}
scale slider, .scale-fan slider, .scale-batt slider, .scale-rgb slider {
    background-color: #ffffff;
    border-radius: 7px;
    min-width: 14px;
    min-height: 14px;
    border: 2px solid #0b0b0b;
}

/* ── SWITCH ── */
switch {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    border-radius: 20px;
}
switch:checked {
    background-color: #ffffff;
    border-color: #ffffff;
}
switch slider {
    background-color: #888888;
    border-radius: 20px;
    margin: 2px;
    min-width: 18px;
    min-height: 18px;
}
switch:checked slider { background-color: #0b0b0b; }

/* ── STATUS BAR ── */
.statusbar, .statusbar-warn {
    background-color: #050505;
    border-top: 1px solid #222222;
    padding: 5px 18px;
    font-size: 9px;
    font-weight: 500;
    color: #aaaaaa;
    letter-spacing: 1px;
}

/* ── NEON SEPARATOR ── */
.neon-sep {
    background-color: #222222;
    min-height: 1px;
    margin: 4px 0px;
}

/* ── ENTRY ── */
entry {
    background-color: #1a1a1a;
    color: #ffffff;
    border: 1px solid #333333;
    border-radius: 3px;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 500;
}
entry:focus {
    border-color: #ffffff;
}
"""

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def rfile(path, default="0"):
    try:
        with open(path) as f: return f.read().strip()
    except: return default

def rtemp(path):
    try: return int(rfile(path,"0"))/1000
    except: return 0.0

def cmd(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=3)
        return r.stdout.strip()
    except: return ""

def pkexec_write(path, value):
    try:
        subprocess.run(["pkexec","tee",path],
            input=str(value).encode(), capture_output=True, timeout=5)
        return True
    except: return False

def gpu_temp():
    v = cmd(["nvidia-smi","--query-gpu=temperature.gpu","--format=csv,noheader,nounits"])
    try: return float(v)
    except: return 0.0

def gpu_fan_pct():
    v = cmd(["nvidia-smi","--query-gpu=fan.speed","--format=csv,noheader,nounits"])
    try: return int(v)
    except: return -1

def gpu_power():
    v = cmd(["nvidia-smi","--query-gpu=power.draw","--format=csv,noheader,nounits"])
    try: return float(v)
    except: return 0.0

def gpu_util():
    v = cmd(["nvidia-smi","--query-gpu=utilization.gpu","--format=csv,noheader,nounits"])
    try: return float(v)
    except: return 0.0

def gpu_vram_used():
    v = cmd(["nvidia-smi","--query-gpu=memory.used","--format=csv,noheader,nounits"])
    try: return float(v)
    except: return 0.0

def gpu_vram_total():
    v = cmd(["nvidia-smi","--query-gpu=memory.total","--format=csv,noheader,nounits"])
    try: return float(v)
    except: return 1.0

def gpu_clocks():
    gc = cmd(["nvidia-smi","--query-gpu=clocks.gr","--format=csv,noheader,nounits"])
    mc = cmd(["nvidia-smi","--query-gpu=clocks.mem","--format=csv,noheader,nounits"])
    try: return int(gc), int(mc)
    except: return 0, 0

def gpu_power_limit():
    v = cmd(["nvidia-smi","--query-gpu=power.limit","--format=csv,noheader,nounits"])
    try: return float(v)
    except: return 0.0

def cpu_cores():
    out = []
    for i in range(1,9):
        p = f"{HWMON_CORE}/temp{i}_input"
        if os.path.exists(p): out.append(rtemp(p))
    return out

def cpu_usage_pct():
    try:
        import psutil
        return psutil.cpu_percent(interval=None)
    except:
        try:
            s1 = open("/proc/stat").readline().split()
            time.sleep(0.1)
            s2 = open("/proc/stat").readline().split()
            idle1 = int(s1[4]); total1 = sum(int(x) for x in s1[1:])
            idle2 = int(s2[4]); total2 = sum(int(x) for x in s2[1:])
            dt = total2-total1
            if dt == 0: return 0.0
            return 100*(1-(idle2-idle1)/dt)
        except: return 0.0

def ram_info():
    try:
        import psutil
        vm = psutil.virtual_memory()
        return vm.used/1024**3, vm.total/1024**3
    except:
        try:
            m = {}
            for l in open("/proc/meminfo"):
                k,v = l.split(":")
                m[k.strip()] = int(v.strip().split()[0])
            total = m.get("MemTotal",0)/1024**2
            avail = m.get("MemAvailable",0)/1024**2
            return total-avail, total
        except: return 0,1

def net_bytes(iface=""):
    try:
        import psutil
        net = psutil.net_io_counters(pernic=True)
        if not iface:
            for k in net:
                if k not in ("lo",) and net[k].bytes_recv > 0:
                    iface = k; break
        if iface in net:
            return net[iface].bytes_recv, net[iface].bytes_sent, iface
        return 0,0,""
    except:
        try:
            ifaces = {}
            for l in open("/proc/net/dev"):
                if ":" in l:
                    parts = l.split(":")
                    name = parts[0].strip()
                    vals = parts[1].split()
                    ifaces[name] = (int(vals[0]), int(vals[8]))
            if not iface:
                for k,v in ifaces.items():
                    if k != "lo" and v[0] > 0:
                        iface = k; break
            if iface in ifaces:
                return ifaces[iface][0], ifaces[iface][1], iface
        except: pass
        return 0,0,""

def top_processes(n=8):
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(["pid","name","cpu_percent","memory_percent"]):
            try:
                procs.append((p.info["pid"], p.info["name"] or "?",
                              p.info["cpu_percent"] or 0,
                              p.info["memory_percent"] or 0))
            except: pass
        return sorted(procs, key=lambda x: x[2], reverse=True)[:n]
    except:
        try:
            out = cmd(["ps","aux","--sort=-%cpu","--no-headers","-o","pid,comm,%cpu,%mem"])
            procs = []
            for l in out.split("\n")[:n]:
                parts = l.split(None, 3)
                if len(parts) >= 4:
                    try: procs.append((int(parts[0]), parts[1][:20], float(parts[2]), float(parts[3])))
                    except: pass
            return procs
        except: return []

def disk_usage():
    try:
        import psutil
        disks = []
        for p in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(p.mountpoint)
                disks.append((p.mountpoint, u.used/1024**3, u.total/1024**3))
            except: pass
        return disks
    except:
        try:
            out = cmd(["df","-h","--output=target,used,size","-x","tmpfs","-x","devtmpfs","-x","squashfs"])
            disks = []
            for l in out.split("\n")[1:]:
                parts = l.split()
                if len(parts) >= 3:
                    try:
                        def parse_size(s):
                            s = s.upper()
                            if s.endswith("G"): return float(s[:-1])
                            if s.endswith("T"): return float(s[:-1])*1024
                            if s.endswith("M"): return float(s[:-1])/1024
                            return 0
                        disks.append((parts[0], parse_size(parts[1]), parse_size(parts[2])))
                    except: pass
            return disks
        except: return []

def batt_health():
    try:
        full = int(rfile(BATT_FULL,"0"))
        design = int(rfile(BATT_DESIGN,"0"))
        if design > 0:
            return (full/design)*100
    except: pass
    return 0.0

def get_fan_rpm():
    try:
        import glob
        fans = sorted(glob.glob("/sys/class/hwmon/hwmon*/fan*_input"))
        rpms = []
        for fan_path in fans:
            try:
                rpm = int(rfile(fan_path, "0"))
                rpms.append(rpm)
            except:
                pass
        cpu_rpm = rpms[0] if len(rpms) > 0 else 0
        gpu_rpm = rpms[1] if len(rpms) > 1 else 0
        return cpu_rpm, gpu_rpm
    except:
        return 0, 0

# ─── CAIRO (MONOCHROME RENDERING) ────────────────────────────────────────────
try:
    import cairo
    HAS_CAIRO = True
except: HAS_CAIRO = False

class GaugeWidget(Gtk.DrawingArea):
    def __init__(self, label="", color=(1,1,1), size=130):
        super().__init__()
        self.label = label
        self.color = (1.0, 1.0, 1.0) # Wymuszona czysta biel
        self.value = 0.0
        self.text  = "--"
        self.unit  = "°C"
        self.set_size_request(size, size)
        self.connect("draw", self._draw)

    def set_val(self, raw, maxv=100, unit="°C"):
        self.value = min(raw / maxv, 1.0)
        self.text  = f"{raw:.0f}"
        self.unit  = unit
        self.queue_draw()

    def _draw(self, w, cr):
        W = w.get_allocated_width()
        H = w.get_allocated_height()
        cx, cy = W/2, H/2
        r = min(W,H)/2 - 12

        # Tło
        cr.set_source_rgba(0.05, 0.05, 0.05, 1)
        cr.arc(cx, cy, r+6, 0, 2*math.pi)
        cr.fill()

        # Pierścień tła (ciemny szary)
        cr.set_source_rgba(0.2, 0.2, 0.2, 1)
        cr.set_line_width(6)
        start = math.pi * 0.75
        end   = math.pi * 2.25
        cr.arc(cx, cy, r, start, end)
        cr.stroke()

        # Pasek postępu (biały)
        if self.value > 0:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.9)
            cr.set_line_width(6)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            arc_end = start + self.value * (end - start)
            cr.arc(cx, cy, r, start, arc_end)
            cr.stroke()

            # Kropka na końcu paska
            tip_x = cx + r * math.cos(arc_end)
            tip_y = cy + r * math.sin(arc_end)
            cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            cr.arc(tip_x, tip_y, 4, 0, 2*math.pi)
            cr.fill()

        # Główny tekst (biały)
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(28)
        te = cr.text_extents(self.text)
        cr.move_to(cx - te[2]/2 - te[0], cy + te[3]/2 - te[1]/2 - 8)
        cr.show_text(self.text)

        # Jednostka (jasnoszary)
        cr.set_source_rgba(0.7, 0.7, 0.7, 1.0)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(11)
        te2 = cr.text_extents(self.unit)
        cr.move_to(cx - te2[2]/2 - te2[0], cy + te[3]/2 - te[1]/2 + 15)
        cr.show_text(self.unit)

        # Opis na dole (szary)
        cr.set_source_rgba(0.5, 0.5, 0.5, 1.0)
        cr.set_font_size(9)
        te3 = cr.text_extents(self.label)
        cr.move_to(cx - te3[2]/2 - te3[0], H - 6)
        cr.show_text(self.label)
        return False


class Graph(Gtk.DrawingArea):
    def __init__(self, color=(1,1,1), n=90, maxv=100):
        super().__init__()
        self.color = (1.0, 1.0, 1.0)
        self.maxv  = maxv
        self.data  = deque([0.0]*n, maxlen=n)
        self.set_size_request(-1, 55)
        self.connect("draw", self._draw)

    def push(self, v):
        self.data.append(float(v))
        self.queue_draw()

    def _draw(self, w, cr):
        if not HAS_CAIRO: return False
        W = w.get_allocated_width()
        H = w.get_allocated_height()
        
        # Tło wykresu
        cr.set_source_rgba(0.07, 0.07, 0.07, 1)
        cr.rectangle(0,0,W,H); cr.fill()

        # Linie siatki
        cr.set_source_rgba(0.2, 0.2, 0.2, 1)
        cr.set_line_width(0.5)
        for i in [25,50,75]:
            y = H - (i/100)*H
            cr.move_to(0,y); cr.line_to(W,y); cr.stroke()

        pts = list(self.data)
        if len(pts)<2: return False
        step = W/(len(pts)-1)

        # Wypełnienie wykresu (subtelny biały gradient/cień)
        cr.set_source_rgba(1, 1, 1, 0.05)
        cr.move_to(0,H)
        for i,v in enumerate(pts):
            cr.line_to(i*step, H-(min(v,self.maxv)/self.maxv)*H)
        cr.line_to(W,H); cr.close_path(); cr.fill()

        # Główna linia wykresu (biała)
        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.set_line_width(1.2)
        for i,v in enumerate(pts):
            x,y = i*step, H-(min(v,self.maxv)/self.maxv)*H
            cr.move_to(x,y) if i==0 else cr.line_to(x,y)
        cr.stroke()
        return False


class RGBPreview(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.set_size_request(-1, 80)
        self.zones = [(255,255,255),(255,255,255),(255,255,255),(255,255,255)]
        self.brightness = 100
        self.connect("draw", self._draw)

    def set_zones(self, zones, brightness=100):
        self.zones = zones
        self.brightness = brightness
        self.queue_draw()

    def _draw(self, w, cr):
        if not HAS_CAIRO: return False
        W = w.get_allocated_width()
        H = w.get_allocated_height()
        cr.set_source_rgba(0.07,0.07,0.07,1)
        cr.rectangle(0,0,W,H); cr.fill()

        kw, kh = W-30, 55
        kx, ky = 15, (H-kh)//2
        cr.set_source_rgba(0.12,0.12,0.12,1)
        cr.rectangle(kx,ky,kw,kh); cr.fill()
        cr.set_source_rgba(0.3,0.3,0.3,1)
        cr.set_line_width(1)
        cr.rectangle(kx,ky,kw,kh); cr.stroke()

        zw = kw//4
        b = self.brightness/100
        for i, (r,g,b_col) in enumerate(self.zones):
            zx = kx + i*zw
            # Monochromatyczne odwzorowanie jasności stref
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.15 * b)
            cr.rectangle(zx+2, ky+2, zw-4, kh-4)
            cr.fill()
            
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.4 * b)
            for row in range(3):
                for col in range(4):
                    kbx = zx+4+col*9
                    kby = ky+6+row*15
                    cr.rectangle(kbx, kby, 7, 11)
                    cr.fill()
        return False


# ─── MAIN APP ─────────────────────────────────────────────────────────────────
class PredatorApp(Gtk.Window):
    def __init__(self, app):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("PREDATOR CONTROL")
        self.set_default_size(980, 680)
        self.active_profile = None
        self._current_page = "home"
        
        self.rgb_zones = [(255,255,255),(255,255,255),(255,255,255),(255,255,255)]
        self.rgb_brightness = 100
        self.rgb_mode = "static"
        self.rgb_speed = 3
        
        self._prev_rx = 0; self._prev_tx = 0
        self._prev_net_time = time.time()
        self._net_iface = ""
        self._net_dl_hist = deque([0.0]*60, maxlen=60)
        self._net_ul_hist = deque([0.0]*60, maxlen=60)
        
        self._cpu_use_hist = deque([0.0]*60, maxlen=60)
        self._ram_hist = deque([0.0]*60, maxlen=60)
        self._gpu_util_hist = deque([0.0]*60, maxlen=60)
        self._css()
        self._ui()
        GLib.timeout_add(2000, self._tick)
        self._tick()

    def _css(self):
        p = Gtk.CssProvider()
        p.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), p,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _lbl(self, text="", css=None, halign=Gtk.Align.START, wrap=False):
        l = Gtk.Label(label=text)
        l.set_halign(halign)
        l.set_line_wrap(wrap)
        if css:
            for c in css.split(): l.get_style_context().add_class(c)
        return l

    def _card(self, *css_classes):
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        b.get_style_context().add_class("card")
        for c in css_classes: b.get_style_context().add_class(c)
        return b

    def _sep(self):
        s = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        s.set_opacity(0.1)
        return s

    def _neon_sep(self):
        s = Gtk.Box()
        s.get_style_context().add_class("neon-sep")
        s.set_size_request(-1, 1)
        return s

    def _sec_lbl(self, text, extra_css=""):
        l = Gtk.Label(label=text)
        l.set_halign(Gtk.Align.START)
        css = "sec-lbl"
        if extra_css: css += " " + extra_css
        for c in css.split(): l.get_style_context().add_class(c)
        return l

    # ─────────────────────────────── UI ──────────────────────────────────────
    def _ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)

        main = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        root.pack_start(main, True, True, 0)

        # SIDEBAR
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.get_style_context().add_class("sidebar")
        main.pack_start(sidebar, False, False, 0)

        logo_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        logo_box.get_style_context().add_class("sidebar-logo")
        logo_box.pack_start(self._lbl("PREDATOR","logo-title"), False,False,0)
        logo_box.pack_start(self._lbl("PH317-55  CONTROL","logo-sub"), False,False,0)
        sidebar.pack_start(logo_box, False, False, 0)

        sidebar.pack_start(self._lbl("MONITOR","nav-section-lbl"), False,False,0)
        self._nav_btns = {}
        pages = [
            ("home",    "HOME"),
            ("temps",   "TEMPERATURY"),
            ("usage",   "UŻYCIE SYSTEMU"),
            ("gpu",     "GPU"),
            ("network", "SIEĆ"),
        ]
        sidebar.pack_start(self._lbl("STEROWANIE","nav-section-lbl"), False,False,0)
        pages += [
            ("fans",    "WENTYLATORY"),
            ("power",   "ZASILANIE"),
            ("rgb",     "PODŚWIETLENIE"),
            ("display", "OPCJE"),
            ("advanced","ZAAWANSOWANE"),
        ]
        for page_id, label in pages:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("nav-btn")
            btn.connect("clicked", self._nav_click, page_id)
            sidebar.pack_start(btn, False, False, 0)
            self._nav_btns[page_id] = btn

        self.sidebar_status = self._lbl("● --","micro-lbl")
        self.sidebar_status.set_margin_start(16)
        self.sidebar_status.set_margin_bottom(8)
        sidebar.pack_end(self.sidebar_status, False,False,0)

        # CONTENT STACK
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)
        self.stack.get_style_context().add_class("content-area")
        main.pack_start(self.stack, True, True, 0)

        self.stack.add_named(self._page_home(),    "home")
        self.stack.add_named(self._page_temps(),   "temps")
        self.stack.add_named(self._page_usage(),   "usage")
        self.stack.add_named(self._page_gpu(),     "gpu")
        self.stack.add_named(self._page_network(), "network")
        self.stack.add_named(self._page_fans(),    "fans")
        self.stack.add_named(self._page_power(),   "power")
        self.stack.add_named(self._page_rgb(),     "rgb")
        self.stack.add_named(self._page_display(), "display")
        self.stack.add_named(self._page_advanced(),"advanced")

        self._nav_click(None, "home")

        self.status = self._lbl("● gotowy","statusbar")
        self.status.set_margin_start(18)
        root.pack_end(self.status, False, False, 0)

    def _nav_click(self, btn, page_id):
        self._current_page = page_id
        self.stack.set_visible_child_name(page_id)
        for pid, b in self._nav_btns.items():
            ctx = b.get_style_context()
            ctx.remove_class("nav-active")
        self._nav_btns[page_id].get_style_context().add_class("nav-active")

    def _page_header(self, title, sub):
        hdr = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        hdr.get_style_context().add_class("page-header")
        hdr.pack_start(self._lbl(title, "page-title"), False,False,0)
        hdr.pack_start(self._lbl(sub, "page-sub"), False,False,0)
        return hdr

    # ─────────────────────────────── HOME PAGE ───────────────────────────────
    def _page_home(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self._page_header("HOME", "PRZEGLĄD SYSTEMU"), False,False,0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_start(16); inner.set_margin_end(16)
        inner.set_margin_top(14); inner.set_margin_bottom(14)
        scroll.add(inner)
        box.pack_start(scroll, True, True, 0)

        inner.pack_start(self._sec_lbl("TEMPERATURY"), False,False,4)
        gauges_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        if HAS_CAIRO:
            self.gauge_cpu = GaugeWidget("CPU", (1,1,1), 140)
            self.gauge_gpu = GaugeWidget("GPU", (1,1,1), 140)
            self.gauge_pwr = GaugeWidget("GPU PWR", (1,1,1), 120)
            for g in [self.gauge_cpu, self.gauge_gpu, self.gauge_pwr]:
                gc = self._card("card-cpu")
                gc.set_halign(Gtk.Align.CENTER)
                gc.pack_start(g, False,False,0)
                gauges_row.pack_start(gc, True,True,0)
        else:
            cpu_c = self._card("card-cpu")
            cpu_c.pack_start(self._lbl("CPU","micro-lbl"), False,False,0)
            self.cpu_temp_lbl = self._lbl("--","big-val")
            cpu_c.pack_start(self.cpu_temp_lbl, False,False,0)
            self.cpu_pb = Gtk.ProgressBar()
            cpu_c.pack_start(self.cpu_pb, False,False,0)
            gauges_row.pack_start(cpu_c, True,True,0)

            gpu_c = self._card("card-gpu")
            gpu_c.pack_start(self._lbl("GPU","micro-lbl"), False,False,0)
            self.gpu_temp_lbl = self._lbl("--","big-val")
            gpu_c.pack_start(self.gpu_temp_lbl, False,False,0)
            self.gpu_pb = Gtk.ProgressBar()
            self.gpu_pb.get_style_context().add_class("pb-cool")
            gpu_c.pack_start(self.gpu_pb, False,False,0)
            gauges_row.pack_start(gpu_c, True,True,0)

        inner.pack_start(gauges_row, False,False,0)

        inner.pack_start(self._sec_lbl("STAN SYSTEMU"), False,False,10)
        stats_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        for attr, label, css_card in [
            ("_qs_cpu","CPU USAGE","card-cpu"),
            ("_qs_ram","RAM","card-batt"),
            ("_qs_gpu_util","GPU UTIL","card-gpu"),
            ("_qs_fan","WENTYLATOR","card-fan"),
        ]:
            c = self._card(css_card)
            c.pack_start(self._lbl(label,"micro-lbl"), False,False,0)
            vl = self._lbl("--","rpm-lbl")
            c.pack_start(vl, False,False,0)
            setattr(self, attr, vl)
            stats_row.pack_start(c, True,True,0)
        inner.pack_start(stats_row, False,False,0)

        if HAS_CAIRO:
            inner.pack_start(self._sec_lbl("HISTORIA"), False,False,10)
            self.g_cpu_temp = Graph((1,1,1))
            self.g_gpu_temp = Graph((1,1,1))
            for g, label, css in [(self.g_cpu_temp,"CPU TEMP","card-cpu"),(self.g_gpu_temp,"GPU TEMP","card-gpu")]:
                gc = self._card(css)
                gc.pack_start(self._lbl(label,"micro-lbl"), False,False,0)
                gc.pack_start(g, True,True,0)
                inner.pack_start(gc, False,False,0)

        return box

    # ─────────────────────────────── TEMPS PAGE ──────────────────────────────
    def _page_temps(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self._page_header("TEMPERATURY", "RDZENIE CPU · PAKIET · GPU"), False,False,0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_start(16); inner.set_margin_end(16)
        inner.set_margin_top(14); inner.set_margin_bottom(14)
        scroll.add(inner)
        box.pack_start(scroll, True, True, 0)

        inner.pack_start(self._sec_lbl("RDZENIE CPU"), False,False,4)
        cores_c = self._card("card-cpu")
        cores_grid = Gtk.Grid(column_spacing=14, row_spacing=8)
        self.core_lbls = []
        self.core_pbs  = []
        for i in range(8):
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            top.pack_start(self._lbl(f"C{i}","micro-lbl"), True,True,0)
            val_l = self._lbl("--°","stat-lbl")
            top.pack_end(val_l, False,False,0)
            pb = Gtk.ProgressBar()
            vbox.pack_start(top, False,False,0)
            vbox.pack_start(pb, False,False,0)
            cores_grid.attach(vbox, i%4, i//4, 1, 1)
            self.core_lbls.append(val_l)
            self.core_pbs.append(pb)
        cores_c.pack_start(cores_grid, False,False,0)
        inner.pack_start(cores_c, False,False,0)

        if HAS_CAIRO:
            inner.pack_start(self._sec_lbl("WYKRESY TEMPERATURY"), False,False,10)
            self.g_cpu_t2 = Graph((1,1,1))
            self.g_gpu_t2 = Graph((1,1,1))
            for g, label, css in [(self.g_cpu_t2,"CPU","card-cpu"),(self.g_gpu_t2,"GPU","card-gpu")]:
                gc = self._card(css)
                gc.pack_start(self._lbl(label,"micro-lbl"), False,False,0)
                gc.pack_start(g, True,True,0)
                inner.pack_start(gc, False,False,0)

        return box

    # ─────────────────────────────── USAGE PAGE ──────────────────────────────
    def _page_usage(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self._page_header("UŻYCIE SYSTEMU", "CPU · RAM · DYSKI · PROCESY"), False,False,0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_start(16); inner.set_margin_end(16)
        inner.set_margin_top(14); inner.set_margin_bottom(14)
        scroll.add(inner)
        box.pack_start(scroll, True, True, 0)

        inner.pack_start(self._sec_lbl("CPU / RAM", "sec-lbl-usage"), False,False,4)
        cr_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        cpu_c = self._card("card-usage")
        cpu_c.pack_start(self._lbl("CPU USAGE","micro-lbl"), False,False,0)
        cpu_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.cpu_use_lbl = self._lbl("-- %","rpm-lbl usage-lbl")
        cpu_top.pack_start(self.cpu_use_lbl, False,False,0)
        cpu_c.pack_start(cpu_top, False,False,0)
        self.cpu_use_pb = Gtk.ProgressBar()
        self.cpu_use_pb.get_style_context().add_class("pb-usage")
        cpu_c.pack_start(self.cpu_use_pb, False,False,0)
        if HAS_CAIRO:
            self.g_cpu_use = Graph((1,1,1), maxv=100)
            cpu_c.pack_start(self.g_cpu_use, True,True,0)
        cr_row.pack_start(cpu_c, True,True,0)

        ram_c = self._card("card-batt")
        ram_c.pack_start(self._lbl("RAM","micro-lbl"), False,False,0)
        self.ram_lbl = self._lbl("-- GB","rpm-lbl cyan-lbl")
        ram_c.pack_start(self.ram_lbl, False,False,0)
        self.ram_total_lbl = self._lbl("/ -- GB","stat-lbl")
        ram_c.pack_start(self.ram_total_lbl, False,False,0)
        self.ram_pb = Gtk.ProgressBar()
        self.ram_pb.get_style_context().add_class("pb-batt")
        ram_c.pack_start(self.ram_pb, False,False,0)
        if HAS_CAIRO:
            self.g_ram = Graph((1,1,1), maxv=100)
            ram_c.pack_start(self.g_ram, True,True,0)
        cr_row.pack_start(ram_c, True,True,0)
        inner.pack_start(cr_row, False,False,0)

        inner.pack_start(self._sec_lbl("DYSKI", "sec-lbl-usage"), False,False,10)
        self.disk_box = self._card("card-usage")
        inner.pack_start(self.disk_box, False,False,0)

        inner.pack_start(self._sec_lbl("TOP PROCESY (CPU %)", "sec-lbl-usage"), False,False,10)
        proc_c = self._card()
        self.proc_grid = Gtk.Grid(column_spacing=16, row_spacing=4)
        proc_c.pack_start(self.proc_grid, False,False,0)
        inner.pack_start(proc_c, False,False,0)

        self._update_usage_static()
        return box

    def _update_usage_static(self):
        for child in self.disk_box.get_children():
            self.disk_box.remove(child)
        self._disk_pbs = []
        for mount, used, total in disk_usage():
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.pack_start(self._lbl(mount[:20],"micro-lbl"), False,False,0)
            pct = used/total if total > 0 else 0
            pb = Gtk.ProgressBar()
            pb.get_style_context().add_class("pb-usage")
            pb.set_fraction(pct)
            pb.set_hexpand(True)
            row.pack_start(pb, True,True,0)
            lbl = self._lbl(f"{used:.1f}/{total:.1f} GB","stat-lbl")
            row.pack_end(lbl, False,False,0)
            self.disk_box.pack_start(row, False,False,0)
        self.disk_box.show_all()

    # ─────────────────────────────── GPU PAGE ────────────────────────────────
    def _page_gpu(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self._page_header("GPU", "NVIDIA — TEMPERATURA · UTILIZATION · VRAM · ZEGARY"), False,False,0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_start(16); inner.set_margin_end(16)
        inner.set_margin_top(14); inner.set_margin_bottom(14)
        scroll.add(inner)
        box.pack_start(scroll, True, True, 0)

        gpu_name = cmd(["nvidia-smi","--query-gpu=name","--format=csv,noheader"])
        if gpu_name:
            inner.pack_start(self._lbl(f" {gpu_name}","stat-lbl"), False,False,4)

        inner.pack_start(self._sec_lbl("METRYKI GPU"), False,False,8)

        if HAS_CAIRO:
            gauges_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            self.gauge_gpu2     = GaugeWidget("TEMP",   (1,1,1), 130)
            self.gauge_gpu_util = GaugeWidget("UTIL",   (1,1,1), 130)
            self.gauge_vram     = GaugeWidget("VRAM %", (1,1,1), 130)
            for g in [self.gauge_gpu2, self.gauge_gpu_util, self.gauge_vram]:
                gc = self._card("card-gpu")
                gc.set_halign(Gtk.Align.CENTER)
                gc.pack_start(g, False,False,0)
                gauges_row.pack_start(gc, True,True,0)
            inner.pack_start(gauges_row, False,False,0)

        stats_c = self._card("card-gpu")
        stats_c.pack_start(self._sec_lbl("SZCZEGÓŁY"), False,False,0)
        sg = Gtk.Grid(column_spacing=20, row_spacing=6)
        self.gpu_stat_lbls = {}
        rows = [
            ("power","MOC BIEŻĄCA","-- W"),
            ("power_lim","LIMIT MOCY","-- W"),
            ("core_clk","ZEGAR RDZENIA","-- MHz"),
            ("mem_clk","ZEGAR PAMIĘCI","-- MHz"),
            ("vram_used","VRAM UŻYTE","-- MB"),
            ("vram_total","VRAM CAŁKOWITE","-- MB"),
            ("fan_pct","WENTYLATOR GPU","-- %"),
        ]
        for i,(k,label,default) in enumerate(rows):
            sg.attach(self._lbl(label,"micro-lbl"), 0, i, 1, 1)
            vl = self._lbl(default,"val-lbl")
            sg.attach(vl, 1, i, 1, 1)
            self.gpu_stat_lbls[k] = vl
        stats_c.pack_start(sg, False,False,0)
        inner.pack_start(stats_c, False,False,0)

        if HAS_CAIRO:
            inner.pack_start(self._sec_lbl("HISTORIA"), False,False,10)
            self.g_gpu_util = Graph((1,1,1), maxv=100)
            self.g_vram = Graph((1,1,1), maxv=100)
            for g, label, css in [(self.g_gpu_util,"GPU UTILIZATION %","card-gpu"),(self.g_vram,"VRAM %","card-gpu")]:
                gc = self._card(css)
                gc.pack_start(self._lbl(label,"micro-lbl"), False,False,0)
                gc.pack_start(g, True,True,0)
                inner.pack_start(gc, False,False,0)

        return box

    # ─────────────────────────────── NETWORK PAGE ────────────────────────────
    def _page_network(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self._page_header("SIEĆ", "PRĘDKOŚĆ · TRANSFER SESJI · INTERFEJS"), False,False,0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_start(16); inner.set_margin_end(16)
        inner.set_margin_top(14); inner.set_margin_bottom(14)
        scroll.add(inner)
        box.pack_start(scroll, True, True, 0)

        inner.pack_start(self._sec_lbl("INTERFEJS", "sec-lbl-net"), False,False,4)
        iface_c = self._card("card-net")
        self.net_iface_lbl = self._lbl("-- wykrywanie...","stat-lbl")
        iface_c.pack_start(self.net_iface_lbl, False,False,0)
        inner.pack_start(iface_c, False,False,8)

        inner.pack_start(self._sec_lbl("PRĘDKOŚĆ BIEŻĄCA", "sec-lbl-net"), False,False,4)
        speed_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        dl_c = self._card("card-net")
        dl_c.pack_start(self._lbl("↓ POBIERANIE","micro-lbl"), False,False,0)
        self.dl_lbl = self._lbl("0.0 KB/s","rpm-lbl net-lbl")
        dl_c.pack_start(self.dl_lbl, False,False,0)
        self.dl_peak_lbl = self._lbl("peak: 0","stat-lbl")
        dl_c.pack_start(self.dl_peak_lbl, False,False,0)
        speed_row.pack_start(dl_c, True,True,0)

        ul_c = self._card("card-net")
        ul_c.pack_start(self._lbl("↑ WYSYŁANIE","micro-lbl"), False,False,0)
        self.ul_lbl = self._lbl("0.0 KB/s","rpm-lbl warn-lbl")
        ul_c.pack_start(self.ul_lbl, False,False,0)
        self.ul_peak_lbl = self._lbl("peak: 0","stat-lbl")
        ul_c.pack_start(self.ul_peak_lbl, False,False,0)
        speed_row.pack_start(ul_c, True,True,0)
        inner.pack_start(speed_row, False,False,0)

        if HAS_CAIRO:
            inner.pack_start(self._sec_lbl("WYKRES PRĘDKOŚCI", "sec-lbl-net"), False,False,10)
            self.g_net_dl = Graph((1,1,1), maxv=1)
            self.g_net_ul = Graph((1,1,1), maxv=1)
            self._net_graph_maxv = 1.0
            for g, label, css in [(self.g_net_dl,"POBIERANIE","card-net"),(self.g_net_ul,"WYSYŁANIE","card-net")]:
                gc = self._card(css)
                gc.pack_start(self._lbl(label,"micro-lbl"), False,False,0)
                gc.pack_start(g, True,True,0)
                inner.pack_start(gc, False,False,0)

        inner.pack_start(self._sec_lbl("TRANSFER SESJI", "sec-lbl-net"), False,False,10)
        totals_c = self._card("card-net")
        totals_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.net_total_dl = self._lbl("↓ 0.0 MB","val-lbl net-lbl")
        self.net_total_ul = self._lbl("↑ 0.0 MB","val-lbl warn-lbl")
        totals_row.pack_start(self.net_total_dl, True,True,0)
        totals_row.pack_start(self.net_total_ul, True,True,0)
        totals_c.pack_start(totals_row, False,False,0)
        inner.pack_start(totals_c, False,False,0)

        rx, tx, iface = net_bytes()
        self._prev_rx = rx; self._prev_tx = tx
        self._net_iface = iface
        self._session_start_rx = rx; self._session_start_tx = tx
        self._net_peak_dl = 0.0; self._net_peak_ul = 0.0

        return box

    def _fmt_speed(self, bps):
        if bps < 1024: return f"{bps:.0f} B/s"
        if bps < 1024**2: return f"{bps/1024:.1f} KB/s"
        return f"{bps/1024**2:.1f} MB/s"

    def _fmt_bytes(self, b):
        if b < 1024**2: return f"{b/1024:.1f} KB"
        if b < 1024**3: return f"{b/1024**2:.1f} MB"
        return f"{b/1024**3:.2f} GB"

    # ─────────────────────────────── FANS PAGE ───────────────────────────────
    def _page_fans(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self._page_header("WENTYLATORY", "PROFILE WYDAJNOŚCI · KONTROLA WENTYLATORÓW"), False,False,0)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_start(16); inner.set_margin_end(16)
        inner.set_margin_top(14); inner.set_margin_bottom(14)
        box.pack_start(inner, True, True, 0)

        inner.pack_start(self._sec_lbl("TRYB WYDAJNOŚCI"), False,False,4)
        prof_c = self._card()
        prof_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.prof_btns = {}

        cur = rfile(PLATFORM_PROFILE,"quiet")
        for val in PROFILES:
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            vbox.set_halign(Gtk.Align.CENTER)
            btn = Gtk.Button(label=f"{PROFILE_LABELS[val]}")
            btn.get_style_context().add_class("profile-btn")
            if val == "performance":
                btn.get_style_context().add_class("turbo-btn")
            if val == cur:
                self.active_profile = val
                ctx = btn.get_style_context()
                if val == "performance": ctx.add_class("turbo-active")
                else: ctx.add_class("active")
            btn.connect("clicked", self._set_profile, val)
            self.prof_btns[val] = btn
            prof_row.pack_start(btn, True,True,0)

        prof_c.pack_start(prof_row, False,False,0)
        self.prof_active_lbl = self._lbl(f"Aktywny: {cur}","micro-lbl")
        self.prof_active_lbl.set_halign(Gtk.Align.CENTER)
        prof_c.pack_start(self.prof_active_lbl, False,False,2)
        inner.pack_start(prof_c, False,False,8)

        inner.pack_start(self._neon_sep(), False,False,4)

        inner.pack_start(self._sec_lbl("RĘCZNA KONTROLA WENTYLATORÓW"), False,False,8)
        fan_c = self._card("card-fan")

        auto_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        auto_row.pack_start(self._lbl("TRYB AUTOMATYCZNY","stat-lbl"), True,True,0)
        self.auto_sw = Gtk.Switch()
        self.auto_sw.set_active(True)
        self.auto_sw.connect("notify::active", self._on_auto)
        auto_row.pack_end(self.auto_sw, False,False,0)
        fan_c.pack_start(auto_row, False,False,0)
        fan_c.pack_start(self._sep(), False,False,4)

        # Gauge'e wentylatorów — dwie kolumny
        gauges_row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        
        for attr, label in [("cpu","CPU FAN"),("gpu","GPU FAN")]:
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            col.set_halign(Gtk.Align.FILL)
            col.set_hexpand(True)
            
            # Gauge do wyświetlania RPM
            if HAS_CAIRO:
                gauge = GaugeWidget(label=label, size=120)
                gauge.set_halign(Gtk.Align.CENTER)
                col.pack_start(gauge, False,False,0)
                setattr(self, f"{attr}_fan_gauge", gauge)
            else:
                val_l = self._lbl("-- RPM","rpm-lbl")
                col.pack_start(val_l, False,False,0)
                setattr(self, f"{attr}_fan_gauge", None)
            
            # Suwak do kontroli RPM — PEŁNA SZEROKOŚĆ
            sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1900, 7300, 100)
            sc.get_style_context().add_class("scale-fan")
            sc.set_value(1900); sc.set_sensitive(False); sc.set_draw_value(False)
            sc.set_hexpand(True)  # ROZCIĄGNIJ HORYZONTALNE
            for rpm in [1900, 3200, 4500, 5800, 7300]:
                sc.add_mark(rpm, Gtk.PositionType.BOTTOM, f"{rpm//1000}k")
            sc.connect("value-changed", self._on_fan_changed_rpm)
            col.pack_start(sc, False,True,0)
            
            # Label wartości RPM pod suwakiem
            val_lbl = self._lbl("AUTO","val-lbl")
            val_lbl.set_halign(Gtk.Align.CENTER)
            col.pack_start(val_lbl, False,False,0)
            
            gauges_row.pack_start(col, False,True,0)
            setattr(self, f"{attr}_fan_sc", sc)
            setattr(self, f"{attr}_fan_val", val_lbl)
            setattr(self, f"{attr}_fan_pb", None)
        
        fan_c.pack_start(gauges_row, False,True,0)

        inner.pack_start(fan_c, False,False,0)

        inner.pack_start(self._neon_sep(), False,False,8)
        read_c = self._card()
        read_c.pack_start(self._sec_lbl("ODCZYT Z SYSTEMU"), False,False,0)
        read_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        for attr, label in [("cpu","CPU FAN"),("gpu","GPU FAN")]:
            vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            vb.pack_start(self._lbl(label,"micro-lbl"), False,False,0)
            rl = self._lbl("--","rpm-lbl")
            vb.pack_start(rl, False,False,0)
            setattr(self, f"{attr}_fan_read", rl)
            read_row.pack_start(vb, True,True,0)
        read_c.pack_start(read_row, False,False,0)
        inner.pack_start(read_c, False,False,0)

        return box

    # ─────────────────────────────── POWER PAGE ──────────────────────────────
    def _page_power(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self._page_header("ZASILANIE", "BATERIA · LIMIT ŁADOWANIA · ZDROWIE · USB"), False,False,0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_start(16); inner.set_margin_end(16)
        inner.set_margin_top(14); inner.set_margin_bottom(14)
        scroll.add(inner)
        box.pack_start(scroll, True, True, 0)

        inner.pack_start(self._sec_lbl("BATERIA"), False,False,0)
        batt_c = self._card("card-batt")

        batt_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.batt_lbl = self._lbl("--","big-val")
        batt_unit = self._lbl("%","big-unit")
        batt_unit.set_valign(Gtk.Align.END)
        batt_unit.set_margin_bottom(8)
        batt_row.pack_start(self.batt_lbl, False,False,0)
        batt_row.pack_start(batt_unit, False,False,0)

        batt_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        batt_info.set_halign(Gtk.Align.END)
        batt_info.set_valign(Gtk.Align.END)
        self.batt_status_lbl = self._lbl("--","stat-lbl")
        self.batt_volt_lbl   = self._lbl("-- V","stat-lbl")
        batt_info.pack_start(self.batt_status_lbl, False,False,0)
        batt_info.pack_start(self.batt_volt_lbl,   False,False,0)
        batt_row.pack_end(batt_info, False,False,0)
        batt_c.pack_start(batt_row, False,False,0)

        self.batt_pb = Gtk.ProgressBar()
        self.batt_pb.get_style_context().add_class("pb-batt")
        batt_c.pack_start(self.batt_pb, False,False,0)
        inner.pack_start(batt_c, False,False,8)

        inner.pack_start(self._sec_lbl("ZDROWIE BATERII"), False,False,4)
        health_c = self._card("card-batt")
        health_grid = Gtk.Grid(column_spacing=20, row_spacing=6)
        self.batt_health_lbl  = self._lbl("-- %","val-lbl cyan-lbl")
        self.batt_cycles_lbl  = self._lbl("--","val-lbl")
        health_grid.attach(self._lbl("ZDROWIE","micro-lbl"), 0, 0, 1, 1)
        health_grid.attach(self.batt_health_lbl, 1, 0, 1, 1)
        health_grid.attach(self._lbl("CYKLE","micro-lbl"), 0, 1, 1, 1)
        health_grid.attach(self.batt_cycles_lbl, 1, 1, 1, 1)
        health_c.pack_start(health_grid, False,False,0)
        self.batt_health_pb = Gtk.ProgressBar()
        self.batt_health_pb.get_style_context().add_class("pb-batt")
        health_c.pack_start(self.batt_health_pb, False,False,4)
        inner.pack_start(health_c, False,False,8)

        inner.pack_start(self._sec_lbl("LIMIT ŁADOWANIA"), False,False,4)
        limit_c = self._card("card-batt")
        limit_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        limit_top.pack_start(self._lbl("Ogranicz maksymalne ładowanie","stat-lbl"), True,True,0)
        self.limit_val = self._lbl("80%","val-lbl cyan-lbl")
        limit_top.pack_end(self.limit_val, False,False,0)
        limit_c.pack_start(limit_top, False,False,0)

        self.limit_sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 20, 100, 5)
        self.limit_sc.get_style_context().add_class("scale-batt")
        self.limit_sc.set_value(80); self.limit_sc.set_draw_value(False)
        for v in [40,60,80,100]:
            self.limit_sc.add_mark(v, Gtk.PositionType.BOTTOM, f"{v}%")
        self.limit_sc.connect("value-changed",
            lambda s: self.limit_val.set_text(f"{int(s.get_value())}%"))
        limit_c.pack_start(self.limit_sc, False,False,0)

        apply_btn = Gtk.Button(label="ZASTOSUJ LIMIT")
        apply_btn.get_style_context().add_class("action-btn")
        apply_btn.connect("clicked", self._apply_limit)
        limit_c.pack_start(apply_btn, False,False,0)
        inner.pack_start(limit_c, False,False,8)

        inner.pack_start(self._sec_lbl("USB CHARGING"), False,False,4)
        usb_c = self._card()
        usb_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        usb_row.pack_start(self._lbl("Ładowanie USB podczas uśpienia","stat-lbl"), True,True,0)
        self.usb_sw = Gtk.Switch()
        self.usb_sw.set_active(rfile(USB_CHG,"0")=="1")
        self.usb_sw.connect("notify::active",
            lambda sw,_: threading.Thread(target=pkexec_write,
                args=(USB_CHG,"1" if sw.get_active() else "0"), daemon=True).start())
        usb_row.pack_end(self.usb_sw, False,False,0)
        usb_c.pack_start(usb_row, False,False,0)
        inner.pack_start(usb_c, False,False,0)

        inner.pack_start(self._sec_lbl("KALIBRACJA"), False,False,8)
        cal_c = self._card()
        cal_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cal_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        cal_info.pack_start(self._lbl("Kalibracja baterii","stat-lbl"), False,False,0)
        cal_info.pack_start(self._lbl("Rozładowuje do 0% i ponownie ładuje do 100%","micro-lbl"), False,False,0)
        cal_row.pack_start(cal_info, True,True,0)
        cal_btn = Gtk.Button(label="KALIBRUJ")
        cal_btn.get_style_context().add_class("action-btn")
        cal_btn.connect("clicked", lambda b: threading.Thread(
            target=pkexec_write, args=(BATT_CAL,"1"), daemon=True).start())
        cal_row.pack_end(cal_btn, False,False,0)
        cal_c.pack_start(cal_row, False,False,0)
        inner.pack_start(cal_c, False,False,0)

        return box

    # ─────────────────────────────── RGB PAGE ────────────────────────────────
    def _page_rgb(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self._page_header("PODŚWIETLENIE", "KLAWIATURA RGB — STREFY · TRYBY · JASNOŚĆ"), False,False,0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_start(16); inner.set_margin_end(16)
        inner.set_margin_top(14); inner.set_margin_bottom(14)
        scroll.add(inner)
        box.pack_start(scroll, True, True, 0)

        inner.pack_start(self._sec_lbl("PODGLĄD KLAWIATURY", "sec-lbl-rgb"), False,False,4)
        if HAS_CAIRO:
            prev_c = self._card("card-rgb")
            self.rgb_preview = RGBPreview()
            prev_c.pack_start(self.rgb_preview, False,False,0)
            inner.pack_start(prev_c, False,False,8)

        inner.pack_start(self._sec_lbl("TRYB EFEKTU", "sec-lbl-rgb"), False,False,4)
        mode_c = self._card("card-rgb")
        mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.rgb_mode_btns = {}
        modes = [("static","STATYCZNY"),("breath","ODDYCHANIE"),("wave","FALA"),("off","WYŁ.")]
        for mode_id, label in modes:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("rgb-btn")
            if mode_id == "off": btn.get_style_context().add_class("rgb-off")
            if mode_id == self.rgb_mode: btn.get_style_context().add_class("active")
            btn.connect("clicked", self._set_rgb_mode, mode_id)
            self.rgb_mode_btns[mode_id] = btn
            mode_row.pack_start(btn, True,True,0)
        mode_c.pack_start(mode_row, False,False,0)

        speed_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        speed_row.pack_start(self._lbl("PRĘDKOŚĆ","stat-lbl"), False,False,0)
        self.rgb_speed_sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 7, 1)
        self.rgb_speed_sc.get_style_context().add_class("scale-rgb")
        self.rgb_speed_sc.set_value(self.rgb_speed)
        self.rgb_speed_sc.set_draw_value(False)
        self.rgb_speed_sc.set_hexpand(True)
        speed_row.pack_start(self.rgb_speed_sc, True,True,0)
        self.rgb_speed_lbl = self._lbl(f"{self.rgb_speed}","val-lbl rgb-lbl")
        self.rgb_speed_sc.connect("value-changed", lambda s: (
            setattr(self, "rgb_speed", int(s.get_value())),
            self.rgb_speed_lbl.set_text(str(int(s.get_value())))
        ))
        speed_row.pack_end(self.rgb_speed_lbl, False,False,0)
        mode_c.pack_start(speed_row, False,False,4)
        inner.pack_start(mode_c, False,False,8)

        inner.pack_start(self._sec_lbl("JASNOŚĆ", "sec-lbl-rgb"), False,False,4)
        bright_c = self._card("card-rgb")
        bright_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.rgb_bright_sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        self.rgb_bright_sc.get_style_context().add_class("scale-rgb")
        self.rgb_bright_sc.set_value(self.rgb_brightness)
        self.rgb_bright_sc.set_draw_value(False)
        self.rgb_bright_sc.set_hexpand(True)
        self.rgb_bright_lbl = self._lbl("100 %","val-lbl rgb-lbl")
        self.rgb_bright_sc.connect("value-changed", self._on_bright_changed)
        bright_row.pack_start(self.rgb_bright_sc, True,True,0)
        bright_row.pack_end(self.rgb_bright_lbl, False,False,0)
        bright_c.pack_start(bright_row, False,False,0)
        inner.pack_start(bright_c, False,False,8)

        inner.pack_start(self._sec_lbl("PICKER RGB", "sec-lbl-rgb"), False,False,4)
        picker_c = self._card("card-rgb")
        
        # Kontener z suwakami R, G, B
        self.rgb_picker = {"r": 255, "g": 255, "b": 255}
        
        for label, key, color in [("RED (R)","r","#ff3333"),("GREEN (G)","g","#33ff33"),("BLUE (B)","b","#3333ff")]:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.pack_start(self._lbl(label,"micro-lbl"), False,False,0)
            
            sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 255, 1)
            sc.set_value(self.rgb_picker[key])
            sc.set_hexpand(True)
            sc.set_draw_value(False)
            for v in [0, 85, 170, 255]:
                sc.add_mark(v, Gtk.PositionType.BOTTOM, str(v))
            
            val_lbl = self._lbl("255","val-lbl")
            sc.connect("value-changed", self._on_rgb_picker_changed, key, val_lbl)
            
            row.pack_start(sc, True,True,0)
            row.pack_end(val_lbl, False,False,0)
            picker_c.pack_start(row, False,False,0)
            setattr(self, f"rgb_{key}_sc", sc)
        
        # Preview koloru
        picker_c.pack_start(self._sep(), False,False,4)
        preview_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        preview_row.pack_start(self._lbl("PODGLĄD","micro-lbl"), False,False,0)
        
        self.rgb_picker_preview = Gtk.DrawingArea()
        self.rgb_picker_preview.set_size_request(80, 40)
        self.rgb_picker_preview._color = (255, 255, 255)
        
        def make_preview_draw(da):
            def draw(w, cr):
                r, g, b = da._color
                cr.set_source_rgb(r/255, g/255, b/255)
                cr.rectangle(0, 0, w.get_allocated_width(), w.get_allocated_height())
                cr.fill()
                return False
            return draw
        
        self.rgb_picker_preview.connect("draw", make_preview_draw(self.rgb_picker_preview))
        preview_row.pack_start(self.rgb_picker_preview, False,False,0)
        
        self.rgb_picker_hex = self._lbl("#FFFFFF","val-lbl")
        preview_row.pack_end(self.rgb_picker_hex, False,False,0)
        picker_c.pack_start(preview_row, False,False,4)
        
        # Przycisk: kopiuj do schowka / zastosuj
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        copy_btn = Gtk.Button(label="KOPIUJ HEX")
        copy_btn.get_style_context().add_class("action-btn")
        copy_btn.connect("clicked", self._rgb_picker_copy)
        
        apply_picker_btn = Gtk.Button(label="ZASTOSUJ DO STREFY 1")
        apply_picker_btn.get_style_context().add_class("action-btn")
        apply_picker_btn.connect("clicked", self._rgb_picker_apply)
        
        apply_all_btn = Gtk.Button(label="DO WSZYSTKICH")
        apply_all_btn.get_style_context().add_class("action-btn")
        apply_all_btn.connect("clicked", self._rgb_picker_apply_all)
        
        btn_row.pack_start(copy_btn, True,True,0)
        btn_row.pack_start(apply_picker_btn, True,True,0)
        btn_row.pack_start(apply_all_btn, True,True,0)
        picker_c.pack_start(btn_row, False,False,0)
        
        inner.pack_start(picker_c, False,False,8)

        inner.pack_start(self._sec_lbl("KOLORY STREF (WPISZ HEX)", "sec-lbl-rgb"), False,False,4)
        zones_c = self._card("card-rgb")
        self.zone_color_entries = []
        zone_names = ["STREFA 1", "STREFA 2", "STREFA 3", "STREFA 4"]
        DEFAULT_ZONE_COLORS = ["FFFFFF","FFFFFF","FFFFFF","FFFFFF"]

        for i, (zname, zdefault) in enumerate(zip(zone_names, DEFAULT_ZONE_COLORS)):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.pack_start(self._lbl(zname,"micro-lbl"), False,False,0)
            entry = Gtk.Entry()
            entry.set_text(zdefault)
            entry.set_max_length(6)
            entry.set_width_chars(8)
            entry.connect("changed", self._on_zone_color_changed, i)
            row.pack_start(entry, False,False,0)
            
            color_da = Gtk.DrawingArea()
            color_da.set_size_request(40, 20)
            r,g,b = self.rgb_zones[i]
            color_da._rgb = (r,g,b)
            def make_draw(da):
                def draw(w,cr):
                    rr,gg,bb = da._rgb
                    cr.set_source_rgb(rr/255,gg/255,bb/255)
                    cr.rectangle(0,0,40,20); cr.fill()
                    return False
                return draw
            color_da.connect("draw", make_draw(color_da))
            row.pack_start(color_da, False,False,0)
            self.zone_color_entries.append((entry, color_da))
            zones_c.pack_start(row, False,False,4)

        apply_rgb_btn = Gtk.Button(label="ZASTOSUJ KONFIGURACJĘ")
        apply_rgb_btn.get_style_context().add_class("action-btn")
        apply_rgb_btn.connect("clicked", self._apply_rgb)
        zones_c.pack_start(apply_rgb_btn, False,False,4)
        inner.pack_start(zones_c, False,False,0)

        return box

    # ─────────────────────────────── DISPLAY PAGE ────────────────────────────
    def _page_display(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self._page_header("OPCJE", "WYŚWIETLACZ · SYSTEM · STATUS STEROWNIKA"), False,False,0)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_start(16); inner.set_margin_end(16)
        inner.set_margin_top(14); inner.set_margin_bottom(14)
        box.pack_start(inner, True, True, 0)

        def switch_card(title, desc, path, default="0"):
            c = self._card()
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            left.pack_start(self._lbl(title,"stat-lbl"), False,False,0)
            left.pack_start(self._lbl(desc,"micro-lbl"), False,False,0)
            row.pack_start(left, True,True,0)
            sw = Gtk.Switch()
            sw.set_active(rfile(path,default)=="1")
            sw.connect("notify::active",
                lambda s,_,p=path: threading.Thread(target=pkexec_write,
                    args=(p,"1" if s.get_active() else "0"), daemon=True).start())
            row.pack_end(sw, False,False,0)
            c.pack_start(row, False,False,0)
            return c

        inner.pack_start(self._sec_lbl("WYŚWIETLACZ"), False,False,0)
        inner.pack_start(switch_card(
            "LCD Overdrive",
            "Szybszy czas reakcji matrycy (może powodować ghosting)",
            LCD_OD), False,False,8)

        inner.pack_start(self._sec_lbl("SYSTEM"), False,False,4)
        inner.pack_start(switch_card(
            "Animacja i dźwięk startowy",
            "Dźwięk Predator przy uruchamianiu laptopa",
            BOOT_ANIM, "1"), False,False,8)
        inner.pack_start(switch_card(
            "USB Charging",
            "Ładowanie USB gdy laptop uśpiony",
            USB_CHG), False,False,8)

        inner.pack_start(self._neon_sep(), False,False,8)
        inner.pack_start(self._sec_lbl("STATUS STEROWNIKA"), False,False,4)
        info_c = self._card()
        ps_ok = os.path.exists(PS)
        info_grid = Gtk.Grid(column_spacing=20, row_spacing=6)
        rows = [
            ("linuwu_sense",    "załadowany ✅" if os.path.exists("/sys/module/linuwu_sense") else "brak ❌"),
            ("predator_sense",  "dostępny ✅" if ps_ok else "brak ❌"),
            ("predator_v4",     rfile("/sys/module/linuwu_sense/parameters/predator_v4","?")),
            ("platform_profile",rfile(PLATFORM_PROFILE,"brak")),
            ("kernel",          cmd(["uname","-r"])),
            ("GPU",             cmd(["nvidia-smi","--query-gpu=name","--format=csv,noheader"])),
        ]
        for i,(k,v) in enumerate(rows):
            info_grid.attach(self._lbl(k,"micro-lbl"), 0, i, 1, 1)
            info_grid.attach(self._lbl(v,"stat-lbl"), 1, i, 1, 1)
        info_c.pack_start(info_grid, False,False,0)
        inner.pack_start(info_c, False,False,0)

        return box

    # ─────────────────────────────── TICK ────────────────────────────────────
    def _tick(self):
        ct = rtemp(TEMP_PKG)
        gt = gpu_temp()
        gp = gpu_power()
        cores = cpu_cores()

        if HAS_CAIRO:
            try:
                self.gauge_cpu.set_val(ct, 100, "°C")
                self.gauge_gpu.set_val(gt, 100, "°C")
                self.gauge_pwr.set_val(gp, 130, "W")
                self.g_cpu_temp.push(ct)
                self.g_gpu_temp.push(gt)
            except: pass
            try:
                self.g_cpu_t2.push(ct)
                self.g_gpu_t2.push(gt)
            except: pass
        else:
            try:
                self.cpu_temp_lbl.set_text(f"{ct:.0f}")
                self.gpu_temp_lbl.set_text(f"{gt:.0f}" if gt>0 else "--")
                self.cpu_pb.set_fraction(min(ct/100,1))
                self.gpu_pb.set_fraction(min(gt/100,1))
            except: pass

        for i,(lbl,pb) in enumerate(zip(self.core_lbls, self.core_pbs)):
            if i < len(cores):
                t = cores[i]
                lbl.set_text(f"{t:.0f}°")
                pb.set_fraction(min(t/100,1))

        fan_raw = rfile(FAN_SPEED,"0,0").split(",")
        try:
            cpu_f = int(fan_raw[0])
            gpu_f = int(fan_raw[1]) if len(fan_raw)>1 else 0
        except: cpu_f=gpu_f=0
        
        cpu_rpm, gpu_rpm = get_fan_rpm()
        
        self.cpu_fan_read.set_text(f"{cpu_f}% ({cpu_rpm} RPM)" if cpu_f>0 else f"AUTO ({cpu_rpm} RPM)")
        self.gpu_fan_read.set_text(f"{gpu_f}% ({gpu_rpm} RPM)" if gpu_f>0 else f"AUTO ({gpu_rpm} RPM)")
        
        # Aktualizuj gauge'e wentylatorów
        try:
            if HAS_CAIRO:
                cpu_gauge = getattr(self, "cpu_fan_gauge", None)
                gpu_gauge = getattr(self, "gpu_fan_gauge", None)
                if cpu_gauge: cpu_gauge.set_val(cpu_rpm, 7300, "RPM")
                if gpu_gauge: gpu_gauge.set_val(gpu_rpm, 7300, "RPM")
        except: pass

        batt = rfile(BATT_CAP,"0")
        bst  = rfile(BATT_STS,"--")
        try:
            bi = int(batt)
            self.batt_lbl.set_text(f"{bi}")
            self.batt_pb.set_fraction(bi/100)
        except: pass
        self.batt_status_lbl.set_text(bst)
        try:
            v = int(rfile(BATT_VOLT,"0"))/1000
            self.batt_volt_lbl.set_text(f"{v:.2f} V")
        except: pass

        health = batt_health()
        if health > 0:
            self.batt_health_lbl.set_text(f"{health:.1f} %")
            self.batt_health_pb.set_fraction(health/100)
        cycles = rfile(BATT_CYCLES,"--")
        self.batt_cycles_lbl.set_text(cycles)

        gf = gpu_fan_pct()

        cpu_use = cpu_usage_pct()
        self._cpu_use_hist.append(cpu_use)
        ram_used, ram_total = ram_info()
        ram_pct = ram_used/ram_total*100 if ram_total > 0 else 0
        self._ram_hist.append(ram_pct)
        gpu_u = gpu_util()
        self._gpu_util_hist.append(gpu_u)

        try:
            self.cpu_use_lbl.set_text(f"{cpu_use:.0f} %")
            self.cpu_use_pb.set_fraction(min(cpu_use/100,1))
            self.ram_lbl.set_text(f"{ram_used:.1f} GB")
            self.ram_total_lbl.set_text(f"/ {ram_total:.1f} GB")
            self.ram_pb.set_fraction(min(ram_pct/100,1))
            if HAS_CAIRO:
                self.g_cpu_use.push(cpu_use)
                self.g_ram.push(ram_pct)
        except: pass

        try:
            procs = top_processes(8)
            for child in self.proc_grid.get_children():
                self.proc_grid.remove(child)
            headers = ["PID","NAZWA","CPU%","MEM%"]
            for j,h in enumerate(headers):
                l = self._lbl(h,"micro-lbl")
                self.proc_grid.attach(l, j, 0, 1, 1)
            for i,(pid,name,cpu,mem) in enumerate(procs):
                for j,val in enumerate([str(pid), name[:18], f"{cpu:.1f}", f"{mem:.1f}"]):
                    l = self._lbl(val,"stat-lbl")
                    self.proc_grid.attach(l, j, i+1, 1, 1)
            self.proc_grid.show_all()
        except: pass

        vram_used = gpu_vram_used()
        vram_total = gpu_vram_total()
        vram_pct = vram_used/vram_total*100 if vram_total > 0 else 0
        gc_mhz, gm_mhz = gpu_clocks()
        gpl = gpu_power_limit()
        try:
            if HAS_CAIRO:
                self.gauge_gpu2.set_val(gt, 100, "°C")
                self.gauge_gpu_util.set_val(gpu_u, 100, "%")
                self.gauge_vram.set_val(vram_pct, 100, "%")
                self.g_gpu_util.push(gpu_u)
                self.g_vram.push(vram_pct)
            self.gpu_stat_lbls["power"].set_text(f"{gp:.0f} W")
            self.gpu_stat_lbls["power_lim"].set_text(f"{gpl:.0f} W" if gpl > 0 else "-- W")
            self.gpu_stat_lbls["core_clk"].set_text(f"{gc_mhz} MHz" if gc_mhz > 0 else "-- MHz")
            self.gpu_stat_lbls["mem_clk"].set_text(f"{gm_mhz} MHz" if gm_mhz > 0 else "-- MHz")
            self.gpu_stat_lbls["vram_used"].set_text(f"{vram_used:.0f} MB")
            self.gpu_stat_lbls["vram_total"].set_text(f"{vram_total:.0f} MB")
            self.gpu_stat_lbls["fan_pct"].set_text(f"{gf} %" if gf >= 0 else "-- %")
        except: pass

        try:
            now = time.time()
            rx, tx, iface = net_bytes(self._net_iface)
            dt = now - self._prev_net_time
            if dt > 0 and self._prev_rx > 0:
                dl_bps = (rx - self._prev_rx) / dt
                ul_bps = (tx - self._prev_tx) / dt
                dl_bps = max(dl_bps, 0)
                ul_bps = max(ul_bps, 0)
                self._net_dl_hist.append(dl_bps)
                self._net_ul_hist.append(ul_bps)
                self._net_peak_dl = max(self._net_peak_dl, dl_bps)
                self._net_peak_ul = max(self._net_peak_ul, ul_bps)
                self.dl_lbl.set_text(self._fmt_speed(dl_bps))
                self.ul_lbl.set_text(self._fmt_speed(ul_bps))
                self.dl_peak_lbl.set_text(f"peak: {self._fmt_speed(self._net_peak_dl)}")
                self.ul_peak_lbl.set_text(f"peak: {self._fmt_speed(self._net_peak_ul)}")
                if HAS_CAIRO:
                    mx = max(max(self._net_dl_hist), max(self._net_ul_hist), 1)
                    self.g_net_dl.maxv = mx
                    self.g_net_ul.maxv = mx
                    self.g_net_dl.push(dl_bps)
                    self.g_net_ul.push(ul_bps)
            sess_dl = rx - getattr(self, "_session_start_rx", rx)
            sess_ul = tx - getattr(self, "_session_start_tx", tx)
            self.net_total_dl.set_text(f"↓ {self._fmt_bytes(sess_dl)}")
            self.net_total_ul.set_text(f"↑ {self._fmt_bytes(sess_ul)}")
            if iface:
                self._net_iface = iface
                self.net_iface_lbl.set_text(f"Interfejs: {iface}")
            self._prev_rx = rx; self._prev_tx = tx; self._prev_net_time = now
        except: pass

        try:
            self._qs_cpu.set_text(f"{cpu_use:.0f}%")
            self._qs_ram.set_text(f"{ram_used:.1f}G")
            self._qs_gpu_util.set_text(f"{gpu_u:.0f}%")
            fan_txt = f"{cpu_rpm} RPM" if cpu_rpm > 0 else "--"
            self._qs_fan.set_text(fan_txt)
        except: pass

        self.sidebar_status.set_text(f"CPU {ct:.0f}°  GPU {gt:.0f}°")

        txt = f"●  cpu {ct:.0f}°C  ·  gpu {gt:.0f}°C  ·  fan {gf}%  ·  cpu_use {cpu_use:.0f}%  ·  bat {batt}%"
        self.status.set_text(txt)
        return True

    # ─────────────────────────────── ACTIONS ─────────────────────────────────
    def _set_profile(self, btn, val):
        def do():
            pkexec_write(PLATFORM_PROFILE, val)
            GLib.idle_add(self._profile_done, val)
        threading.Thread(target=do, daemon=True).start()

    def _profile_done(self, val):
        self.active_profile = val
        for v, btn in self.prof_btns.items():
            ctx = btn.get_style_context()
            ctx.remove_class("active")
            ctx.remove_class("turbo-active")
        ctx = self.prof_btns[val].get_style_context()
        ctx.remove_class("turbo-btn")
        if val == "performance": ctx.add_class("turbo-active")
        else: ctx.add_class("active")
        self.prof_active_lbl.set_text(f"Aktywny: {PROFILE_LABELS[val]}")
        self.status.set_text(f"✓  tryb zmieniony → {val}")

    def _on_auto(self, sw, _):
        auto = sw.get_active()
        self.cpu_fan_sc.set_sensitive(not auto)
        self.gpu_fan_sc.set_sensitive(not auto)
        if auto:
            self.cpu_fan_sc.set_value(1900)
            self.gpu_fan_sc.set_value(1900)
            self.cpu_fan_val.set_text("AUTO")
            self.gpu_fan_val.set_text("AUTO")
            threading.Thread(target=pkexec_write,
                args=(FAN_SPEED,"0,0"), daemon=True).start()

    def _on_fan_changed_rpm(self, _scale):
        if self.auto_sw.get_active(): return
        cpu_rpm = int(self.cpu_fan_sc.get_value())
        gpu_rpm = int(self.gpu_fan_sc.get_value())
        
        MIN_RPM, MAX_RPM = 1900, 7300
        cpu_pct = max(0, int((cpu_rpm - MIN_RPM) / (MAX_RPM - MIN_RPM) * 100))
        gpu_pct = max(0, int((gpu_rpm - MIN_RPM) / (MAX_RPM - MIN_RPM) * 100))
        
        self.cpu_fan_val.set_text(f"{cpu_rpm} RPM")
        self.gpu_fan_val.set_text(f"{gpu_rpm} RPM")
        
        # Aktualizuj gauge'e
        try:
            if HAS_CAIRO:
                cpu_gauge = getattr(self, "cpu_fan_gauge", None)
                gpu_gauge = getattr(self, "gpu_fan_gauge", None)
                if cpu_gauge: cpu_gauge.set_val(cpu_rpm, 7300, "RPM")
                if gpu_gauge: gpu_gauge.set_val(gpu_rpm, 7300, "RPM")
        except: pass
        
        threading.Thread(target=pkexec_write,
            args=(FAN_SPEED, f"{cpu_pct},{gpu_pct}"), daemon=True).start()

    def _apply_limit(self, _btn):
        val = int(self.limit_sc.get_value())
        threading.Thread(target=pkexec_write,
            args=(BATT_LIMIT, val), daemon=True).start()
        self.status.set_text(f"✓  limit baterii → {val}%")

    def _set_rgb_mode(self, btn, mode_id):
        self.rgb_mode = mode_id
        for mid, b in self.rgb_mode_btns.items():
            ctx = b.get_style_context()
            ctx.remove_class("active")
        self.rgb_mode_btns[mode_id].get_style_context().add_class("active")
        self._write_rgb()

    def _on_bright_changed(self, sc):
        self.rgb_brightness = int(sc.get_value())
        self.rgb_bright_lbl.set_text(f"{self.rgb_brightness} %")
        try: self.rgb_preview.set_zones(self.rgb_zones, self.rgb_brightness)
        except: pass

    def _on_zone_color_changed(self, entry, zone_idx):
        txt = entry.get_text().strip().lstrip("#")
        if len(txt) == 6:
            try:
                r = int(txt[0:2],16)
                g = int(txt[2:4],16)
                b = int(txt[4:6],16)
                self.rgb_zones[zone_idx] = (r,g,b)
                entry_widget, color_da = self.zone_color_entries[zone_idx]
                color_da._rgb = (r,g,b)
                color_da.queue_draw()
                try: self.rgb_preview.set_zones(self.rgb_zones, self.rgb_brightness)
                except: pass
            except: pass

    def _apply_rgb(self, _btn):
        self._write_rgb()
        self.status.set_text("✓  konfiguracja RGB zastosowana")

    def _on_rgb_picker_changed(self, sc, key, val_lbl):
        """Aktualizuj wartość RGB pickera."""
        value = int(sc.get_value())
        self.rgb_picker[key] = value
        val_lbl.set_text(str(value))
        
        # Aktualizuj preview
        r, g, b = self.rgb_picker['r'], self.rgb_picker['g'], self.rgb_picker['b']
        self.rgb_picker_preview._color = (r, g, b)
        hex_color = f"#{r:02X}{g:02X}{b:02X}"
        self.rgb_picker_hex.set_text(hex_color)
        self.rgb_picker_preview.queue_draw()

    def _rgb_picker_copy(self, _btn):
        """Kopiuj wybrany kolor do schowka."""
        r, g, b = self.rgb_picker['r'], self.rgb_picker['g'], self.rgb_picker['b']
        hex_color = f"{r:02X}{g:02X}{b:02X}"
        
        # Kopiuj do schowka xclip/xsel
        try:
            subprocess.run(["xclip", "-selection", "clipboard"], 
                          input=hex_color.encode(), timeout=1)
            self.status.set_text(f"✓  Skopiowano: {hex_color}")
        except:
            # Fallback - pokaż w status
            self.status.set_text(f"Kolor: {hex_color} (skopiuj ręcznie)")

    def _rgb_picker_apply(self, _btn):
        """Zastosuj wybrany kolor do Strefy 1."""
        r, g, b = self.rgb_picker['r'], self.rgb_picker['g'], self.rgb_picker['b']
        hex_color = f"{r:02X}{g:02X}{b:02X}"
        
        # Aktualizuj entry Strefy 1
        if self.zone_color_entries:
            entry, color_da = self.zone_color_entries[0]
            entry.set_text(hex_color)
            self.rgb_zones[0] = (r, g, b)
            color_da._rgb = (r, g, b)
            color_da.queue_draw()
            try: self.rgb_preview.set_zones(self.rgb_zones, self.rgb_brightness)
            except: pass
        
        self.status.set_text(f"✓  Strefa 1 → {hex_color}")

    def _rgb_picker_apply_all(self, _btn):
        """Zastosuj wybrany kolor do WSZYSTKICH stref (1-4)."""
        r, g, b = self.rgb_picker['r'], self.rgb_picker['g'], self.rgb_picker['b']
        hex_color = f"{r:02X}{g:02X}{b:02X}"
        
        # Aktualizuj wszystkie entry'i i strefy
        for zone_idx in range(4):
            if zone_idx < len(self.zone_color_entries):
                entry, color_da = self.zone_color_entries[zone_idx]
                entry.set_text(hex_color)
                self.rgb_zones[zone_idx] = (r, g, b)
                color_da._rgb = (r, g, b)
                color_da.queue_draw()
        
        try: self.rgb_preview.set_zones(self.rgb_zones, self.rgb_brightness)
        except: pass
        
        self.status.set_text(f"✓  WSZYSTKIE STREFY → {hex_color}")

    def _write_rgb(self):
        def do():
            if not os.path.exists(RGB_FOUR_ZONE):
                GLib.idle_add(self.status.set_text,
                    "⚠  RGB: brak four_zoned_kb — sprawdź moduł linuwu_sense")
                return

            mode_id    = self.rgb_mode
            brightness = self.rgb_brightness

            if mode_id == "off":
                value = "000000,000000,000000,000000,0"
                try:
                    with open(RGB_FOUR_ZONE, "w") as f: f.write(value)
                except PermissionError:
                    subprocess.run(["pkexec", "tee", RGB_FOUR_ZONE], input=value.encode(), capture_output=True, timeout=5)
                return

            if mode_id in ("breath", "neon", "wave", "shifting", "zoom"):
                zones = [self.rgb_zones[0]] * 4
            else:
                zones = list(self.rgb_zones[:4])
                while len(zones) < 4:
                    zones.append(zones[-1] if zones else (255, 255, 255))

            parts = [f"{r:02x}{g:02x}{b:02x}" for r, g, b in zones]
            value = ",".join(parts) + f",{brightness}"

            try:
                with open(RGB_FOUR_ZONE, "w") as f: f.write(value)
            except PermissionError:
                subprocess.run(["pkexec", "tee", RGB_FOUR_ZONE], input=value.encode(), capture_output=True, timeout=5)
            except Exception as e:
                print(f"[RGB] błąd zapisu: {e}", file=sys.stderr)

        threading.Thread(target=do, daemon=True).start()

    def _page_advanced(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self._page_header("ZAAWANSOWANE", "KONTROLA CPU · WYDAJNOŚĆ"), False,False,0)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_start(16); inner.set_margin_end(16)
        inner.set_margin_top(14); inner.set_margin_bottom(14)
        scroll.add(inner)
        box.pack_start(scroll, True, True, 0)
        
        # ─── INTEL PSTATE - MAX PERFORMANCE %
        inner.pack_start(self._sec_lbl("INTEL PSTATE - LIMITER WYDAJNOŚCI"), False,False,4)
        max_perf_c = self._card("card-adv")
        
        max_perf_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        max_perf_row.pack_start(self._lbl("Max Performance %:","stat-lbl"), True,True,0)
        self.cpu_max_perf_val = self._lbl("100%","val-lbl cyan-lbl")
        max_perf_row.pack_end(self.cpu_max_perf_val, False,False,0)
        max_perf_c.pack_start(max_perf_row, False,False,0)
        
        self.cpu_max_perf_sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 10, 100, 10)
        self.cpu_max_perf_sc.set_value(100)
        self.cpu_max_perf_sc.set_draw_value(False)
        for p in [10, 30, 50, 70, 100]:
            self.cpu_max_perf_sc.add_mark(p, Gtk.PositionType.BOTTOM, f"{p}%")
        self.cpu_max_perf_sc.connect("value-changed",
            lambda s: self.cpu_max_perf_val.set_text(f"{int(s.get_value())}%"))
        max_perf_c.pack_start(self.cpu_max_perf_sc, False,False,0)
        
        apply_max_perf_btn = Gtk.Button(label="ZASTOSUJ MAX PERFORMANCE")
        apply_max_perf_btn.get_style_context().add_class("action-btn")
        apply_max_perf_btn.connect("clicked", self._apply_cpu_max_perf)
        max_perf_c.pack_start(apply_max_perf_btn, False,False,4)
        
        inner.pack_start(max_perf_c, False,False,0)
        
        # ─── TURBO BOOST
        inner.pack_start(self._sep(), False,False,8)
        inner.pack_start(self._sec_lbl("INTEL TURBO BOOST"), False,False,4)
        turbo_c = self._card("card-adv")
        
        turbo_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        turbo_row.pack_start(self._lbl("Turbo Boost:","stat-lbl"), True,True,0)
        self.cpu_turbo_sw = Gtk.Switch()
        self.cpu_turbo_sw.set_active(True)
        self.cpu_turbo_sw.connect("notify::active", self._on_cpu_turbo_toggle)
        turbo_row.pack_end(self.cpu_turbo_sw, False,False,0)
        turbo_c.pack_start(turbo_row, False,False,0)
        
        turbo_c.pack_start(self._lbl(
            "Wyłączenie Turbo Boost zmniejsza pobór energii i temperaturę",
            "micro-lbl"), False,False,2)
        
        inner.pack_start(turbo_c, False,False,0)
        
        # ─── CPU SCALING GOVERNOR
        inner.pack_start(self._sep(), False,False,8)
        inner.pack_start(self._sec_lbl("SCALING GOVERNOR"), False,False,4)
        gov_c = self._card("card-adv")
        
        gov_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        gov_row.pack_start(self._lbl("Governor:","stat-lbl"), True,True,0)
        self.cpu_governor_lbl = self._lbl("powersave","val-lbl")
        gov_row.pack_end(self.cpu_governor_lbl, False,False,0)
        gov_c.pack_start(gov_row, False,False,0)
        
        gov_btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        for gov, label in [("powersave", "POWERSAVE"), ("schedutil", "BALANCED"), ("performance", "PERFORMANCE")]:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("profile-btn")
            btn.connect("clicked", self._apply_cpu_governor, gov)
            gov_btn_row.pack_start(btn, True,True,0)
        
        gov_c.pack_start(gov_btn_row, False,False,4)
        gov_c.pack_start(self._lbl(
            "powersave: oszczędzanie  •  balanced: inteligentnie ~50%  •  performance: maksymalna",
            "micro-lbl"), False,False,2)
        
        inner.pack_start(gov_c, False,False,0)
        
        return box

    # ─── CPU CONTROL METHODS ──────────────────────────────────────────────────
    def _apply_cpu_max_perf(self, btn):
        """Ustaw max performance % dla CPU."""
        perf = int(self.cpu_max_perf_sc.get_value())
        
        def do():
            try:
                pkexec_write("/sys/devices/system/cpu/intel_pstate/max_perf_pct", str(perf))
                GLib.idle_add(lambda: self.status.set_text(f"✓  Max performance ustawiony na {perf}%"))
            except Exception as e:
                GLib.idle_add(lambda: self.status.set_text(f"✗  Błąd: {str(e)}"))
        
        threading.Thread(target=do, daemon=True).start()

    def _on_cpu_turbo_toggle(self, sw, _):
        """Toggle Intel Turbo Boost."""
        enabled = sw.get_active()
        no_turbo = "0" if enabled else "1"
        
        def do():
            try:
                pkexec_write("/sys/devices/system/cpu/intel_pstate/no_turbo", no_turbo)
                status = "✓  Turbo Boost włączony" if enabled else "✓  Turbo Boost wyłączony"
                GLib.idle_add(lambda: self.status.set_text(status))
            except Exception as e:
                GLib.idle_add(lambda: self.status.set_text(f"✗  Błąd: {str(e)}"))
        
        threading.Thread(target=do, daemon=True).start()

    def _apply_cpu_governor(self, btn, governor):
        """Ustaw CPU scaling governor (powersave/schedutil/performance)."""
        gov_label = {
            "powersave": "POWERSAVE",
            "schedutil": "BALANCED",
            "performance": "PERFORMANCE"
        }.get(governor, governor)
        
        self.cpu_governor_lbl.set_text(gov_label)
        
        # Jeśli BALANCED - ustaw też Max Performance na 50%
        if governor == "schedutil":
            self.cpu_max_perf_sc.set_value(50)
        
        def do():
            try:
                # Ustaw dla wszystkich CPU
                cmd = f"echo {governor} | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
                subprocess.run(cmd, shell=True, capture_output=True, timeout=5, 
                             preexec_fn=lambda: os.setpgrp())
                GLib.idle_add(lambda: self.status.set_text(f"✓  Governor zmieniony na {gov_label}"))
            except Exception as e:
                GLib.idle_add(lambda: self.status.set_text(f"✗  Błąd: {str(e)}"))
        
        threading.Thread(target=do, daemon=True).start()


# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    window = PredatorApp(None)
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    print("✓ Aplikacja uruchomiona w trybie monochromatycznym", flush=True)
    Gtk.main()