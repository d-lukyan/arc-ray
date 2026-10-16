import sys
import os
import glob
import psutil
from PyQt6.QtCore import QTimer, Qt, QPoint
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel

class SystemWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.setup_autostart() 
        
        self.gpu_temp_path = self.find_radeon_temp_path()
        self.gpu_busy_path = self.find_radeon_pm_info_path()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

        self.old_pos = None

    def initUI(self):
       
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.Tool | 
                            Qt.WindowType.WindowStaysOnBottomHint)
                            
        self.setAttribute(Qt.WidgetAttribute.WA_X11DoNotAcceptFocus, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        

        try:
            import subprocess
            import shutil
            if shutil.which("xprop") is not None:
                win_id = str(self.winId())
                subprocess.check_call([
                    "xprop", "-f", "_NET_WM_STATE", "32a", 
                    "-id", win_id, 
                    "-set", "_NET_WM_STATE", "_NET_WM_STATE_SKIP_TASKBAR"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 180);
                border-radius: 10px;
            }
            QLabel {
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        
        self.cpu_label = QLabel("CPU: Загрузка... | Temp: --°C")
        self.gpu_label = QLabel("GPU: Загрузка... | Temp: --°C")
        self.ram_label = QLabel("RAM: Загрузка...")
        self.disk_label = QLabel("DISK: Загрузка...")
        
        container_layout.addWidget(self.cpu_label)
        container_layout.addWidget(self.gpu_label)
        container_layout.addWidget(self.ram_label)
        container_layout.addWidget(self.disk_label)
        
        layout.addWidget(self.container)
        self.setLayout(layout)
        
        self.resize(220, 140)
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, 40)


    def find_radeon_temp_path(self):
        """Находит системный файл температуры для видеокарты AMD"""
        for path in glob.glob('/sys/class/hwmon/hwmon*/name'):
            try:
                with open(path, 'r') as f:
                    if 'radeon' in f.read():
                        dir_path = os.path.dirname(path)
                        temp_file = os.path.join(dir_path, 'temp1_input')
                        if os.path.exists(temp_file):
                            return temp_file
            except Exception:
                pass
        return None

    def find_radeon_pm_info_path(self):
        """Автоматический поиск файла radeon_pm_info в системе"""
        possible_paths = glob.glob('/sys/kernel/debug/dri/*/radeon_pm_info')
        if possible_paths:
            return possible_paths[0]
        return None

    def get_gpu_info(self):
        """Чтение реальной нагрузки % и температуры видеокарты AMD Radeon"""
        temp_str = "--°C"
        if self.gpu_temp_path:
            try:
                with open(self.gpu_temp_path, 'r') as f:
                    temp_str = f"{int(int(f.read().strip()) / 1000)}°C"
            except Exception:
                pass

        usage_str = "0%"
        if self.gpu_busy_path:
            try:
                with open(self.gpu_busy_path, 'r') as f:
                    for line in f:
                        if "load" in line.lower() or "gpu" in line.lower():
                            parts = [s for s in line.split() if s.isdigit()]
                            if parts:
                                usage_str = f"{parts[0]}%"
                                return usage_str, temp_str
            except Exception:
                pass
        
        if os.path.exists('/sys/class/drm/card0/device/power_profile'):
            try:
                with open('/sys/class/drm/card0/device/power_profile', 'r') as f:
                    usage_str = f.read().strip().capitalize()
            except Exception:
                usage_str = "Active"
                
        return usage_str, temp_str

    def update_stats(self):
        cpu_usage = psutil.cpu_percent()
        cpu_temp = "--"
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            for key in ["coretemp", "k10temp", "acpitz"]:
                if key in temps and temps[key]:
                    cpu_temp = int(temps[key][0].current)
                    break
        self.cpu_label.setText(f'CPU: {cpu_usage}% | {cpu_temp}°C')

        gpu_usage, gpu_temp = self.get_gpu_info()
        self.gpu_label.setText(f'GPU: {gpu_usage} | {gpu_temp}')

        ram = psutil.virtual_memory()
        used_gb = ram.used / (1024**3)
        total_gb = ram.total / (1024**3)
        self.ram_label.setText(f'RAM: {ram.percent}% ({used_gb:.1f}/{total_gb:.1f} GB)')

        disk = psutil.disk_usage('/')
        self.disk_label.setText(f'DISK: {disk.percent}%')


    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def setup_autostart(self):
        """Автоматическое создание .desktop файла в автозагрузке XFCE"""
        autostart_dir = os.path.expanduser("~/.config/autostart")
        os.makedirs(autostart_dir, exist_ok=True)
        desktop_file_path = os.path.join(autostart_dir, "arc-ray.desktop")
        
        if not os.path.exists(desktop_file_path):
            python_path = sys.executable  
            script_path = os.path.abspath(__file__)
            
            desktop_content = f"""[Desktop Entry]
Type=Application
Exec={python_path} {script_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=ArcRay Widget
Comment=System Monitor Widget
"""
            try:
                with open(desktop_file_path, "w") as f:
                    f.write(desktop_content)
            except Exception:
                pass
                
                
                
if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = SystemWidget()
    widget.show()
    sys.exit(app.exec())
