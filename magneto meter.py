from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Line, PushMatrix, PopMatrix, Rotate, Rectangle
from plyer import compass, vibrator
import math

# --- 1. MŰSZER: VOLT ÉS AMPER (SÁRGA MUTATÓ MAX: 1000 µT) ---
class PowerMeter(Widget):
    def update(self, total_val, fluct_val):
        self.canvas.clear()
        cx, cy = self.center_x, self.y + 30
        with self.canvas:
            # VOLT SKÁLA - Megnövelt félkör (95-ös sugár)
            Color(0.3, 0.3, 0.3, 1)
            Line(circle=(cx, cy, 95, 0, 180), width=2)
            
            # SKÁLÁZÁS: 1000 µT-nál van teljesen kiakadva (180 foknál)
            volt_angle = 180 - min(180, (total_val / 1000.0) * 180.0)
            Color(1, 0.9, 0, 1) 
            rad = math.radians(volt_angle)
            Line(points=[cx, cy, cx + 90 * math.cos(rad), cy + 90 * math.sin(rad)], width=3)
            
            # AMPER CSÍK (Vonalas erősségmérő - változatlan)
            Color(0.1, 0.1, 0.1, 1)
            Rectangle(pos=(self.x + 20, self.y), size=(self.width - 40, 15))
            
            amp_w = min(self.width - 40, fluct_val * 10)
            if fluct_val > 15: Color(1, 0, 0, 1)
            else: Color(0, 1, 0.5, 1)
            Rectangle(pos=(self.x + 20, self.y), size=(amp_w, 15))

# --- 2. MŰSZER: ANOMÁLIA GRAFIKON (VÁLTOZATLAN MÉRET) ---
class AnomaliaMonitor(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.points = []
    def update(self, val):
        scaled_val = min(self.height, val * 5)
        self.points.append(scaled_val)
        if len(self.points) > 60: self.points.pop(0)
        self.canvas.clear()
        with self.canvas:
            Color(0.05, 0.05, 0.05, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(1, 0.1, 0.1, 0.8) 
            if len(self.points) > 1:
                plot_pts = []
                step = self.width / 60
                for i, p in enumerate(self.points):
                    plot_pts.extend([self.x + (i * step), self.y + p])
                Line(points=plot_pts, width=1.5)

# --- 3. MŰSZER: VEKTOR IRÁNYTŰ (NAGY MUTATÓ + Z TENGELY) ---
class VectorCompass(Widget):
    def update_canvas(self, x, y, z, total):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        with self.canvas:
            # Nagy külső keret (120-as sugár)
            Color(0.2, 0.8, 1.0, 0.3)
            Line(circle=(cx, cy, 120), width=2.5)
            
            # Z TENGELY: Mélység jelzése fehéres körrel
            z_s = min(115, abs(z) * 3.0)
            Color(1, 1, 1, 0.25)
            Line(circle=(cx, cy, z_s), width=2)
            
            # Irányvektor színváltás (80 µT felett piros)
            if total > 80:
                Color(1, 0.2, 0.2, 1)
            else:
                Color(0.2, 1, 0.4, 1)
            
            # Irányszög
            angle = math.degrees(math.atan2(-x, y))
            PushMatrix()
            Rotate(angle=angle, origin=(cx, cy))
            
            # Nagy nyíl
            Line(points=[cx, cy, cx, cy + 110], width=8)
            Line(points=[cx-20, cy+90, cx, cy+118, cx+20, cy+90], width=5)
            PopMatrix()

# --- FŐ PROGRAM ---
class GhostTricorder(App):
    def build(self):
        self.root = BoxLayout(orientation='vertical', padding=10, spacing=5)
        
        # Volt és Amper szekció
        self.root.add_widget(Label(text="VOLTAGE / AMPERAGE (EMF)", size_hint_y=0.04, font_size='11sp'))
        self.power_meter = PowerMeter(size_hint_y=0.22)
        self.root.add_widget(self.power_meter)

        # Anomália Monitor
        mon_layout = BoxLayout(size_hint_y=0.25)
        self.monitor = AnomaliaMonitor(size_hint_x=0.7)
        self.peak_label = Label(text="PEAK\n0.00", size_hint_x=0.3, color=(1,0,0,1), bold=True)
        mon_layout.add_widget(self.monitor)
        mon_layout.add_widget(self.peak_label)
        self.root.add_widget(mon_layout)

        # Élő Mikrotesla (µT) szöveges kijelző az iránytű felett
        self.ut_label = Label(text="0.0 µT", size_hint_y=0.06, font_size='20sp', bold=True, markup=True)
        self.root.add_widget(self.ut_label)

        # Nagy iránytű szekció
        self.vector_display = VectorCompass(size_hint_y=0.43)
        self.root.add_widget(self.vector_display)

        self.last_total = 0
        self.max_peak = 0.0
        try: compass.enable()
        except: pass
        
        # 60 Hz-es maximális pontosságú frissítés
        Clock.schedule_interval(self.main_loop, 1.0 / 60.0)
        return self.root

    def main_loop(self, dt):
        try:
            raw = compass.field
            if not raw or None in raw: return
            x, y, z = raw
            total = math.sqrt(x**2 + y**2 + z**2)
            fluct = abs(total - self.last_total)
            
            if fluct > self.max_peak: self.max_peak = fluct
            
            # Műszerek frissítése
            self.power_meter.update(total, fluct)
            self.monitor.update(fluct)
            self.peak_label.text = f"PEAK\n{self.max_peak:.2f}"
            self.vector_display.update_canvas(x, y, z, total)
            
            # Folyamatos Mikrotesla kiírás színváltással
            c = "ff4444" if total > 80 else "44ff88"
            self.ut_label.text = f"[color={c}]{total:.1f} µT[/color]"
            
            if fluct > 20:
                try: vibrator.vibrate(0.05)
                except: pass
            self.last_total = total
        except: pass

    def on_stop(self):
        compass.disable()

if __name__ == '__main__':
    GhostTricorder().run()
