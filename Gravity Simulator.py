import sys
import math
import random
from PyQt6.QtCore import QTimer, QPointF, Qt, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPalette, QFont
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QDockWidget, QComboBox, QDialog, QDoubleSpinBox,
                             QFormLayout, QDialogButtonBox)


class Particle:
    def __init__(self, pos, mass, velocity, color):
        self.x, self.y = pos.x(), pos.y()
        self.mass = mass
        self.vx, self.vy = velocity
        self.ax = 0.0
        self.ay = 0.0
        self.radius = math.sqrt(mass)
        self.color = color
        self.trail = []  # list of previous positions

class Canvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self.G = 6.674 # Increased for visibility
        self.offset = QPointF(0, 0)
        self.scale = 1.0
        self.last_pos = QPoint()

        # Pure black background
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black)
        self.setAutoFillBackground(True)
        self.setPalette(pal)

    def draw_mass(self, painter, particle):
        # Calculate text color based on particle color brightness
        color = particle.color
        brightness = (color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114)
        text_color = QColor(0, 0, 0) if brightness > 128 else QColor(255, 255, 255)

        painter.setPen(QPen(text_color))
        painter.setFont(QFont("Arial", 10))
        text = f"{int(particle.mass)}"

        # Calculate text position
        text_rect = painter.fontMetrics().boundingRect(text)
        x = particle.x - text_rect.width() / 2
        y = particle.y + text_rect.height() / 2

        painter.drawText(QPointF(x, y), text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.offset)
        painter.scale(self.scale, self.scale)
        painter.setPen(Qt.PenStyle.NoPen)

        for p in self.particles:
            # Draw trail
            if len(p.trail) >= 2:
                trail_pen = QPen(p.color)
                trail_pen.setWidthF(0.5)
                trail_pen.setColor(p.color.lighter(150))
                painter.setPen(trail_pen)
                for i in range(len(p.trail) - 1):
                    painter.drawLine(p.trail[i], p.trail[i + 1])

            # Draw particle
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(p.color))
            painter.drawEllipse(QPointF(p.x, p.y), p.radius, p.radius)

            # Draw velocity vector
            painter.setPen(QPen(Qt.GlobalColor.white, 0.5))
            painter.drawLine(QPointF(p.x, p.y), QPointF(p.x + p.vx, p.y + p.vy))

            # Draw mass text
            painter.setPen(QPen(Qt.GlobalColor.white))
            self.draw_mass(painter, p)


    def add_particle(self, particle):
        self.particles.append(particle)
        self.update()

    def update_physics(self, dt):
        # Reset accelerations
        for p in self.particles:
            p.ax = 0.0
            p.ay = 0.0

        # Calculate forces
        for i in range(len(self.particles)):
            for j in range(i + 1, len(self.particles)):
                p1 = self.particles[i]
                p2 = self.particles[j]

                dx = p2.x - p1.x
                dy = p2.y - p1.y
                r_sq = dx * dx + dy * dy + 1000  # Softening
                r = math.sqrt(r_sq)

                force = self.G * p1.mass * p2.mass / r_sq
                fx = force * dx / r
                fy = force * dy / r

                p1.ax += fx / p1.mass
                p1.ay += fy / p1.mass
                p2.ax -= fx / p2.mass
                p2.ay -= fy / p2.mass

        # Update positions
        for p in self.particles:
            p.vx += p.ax * dt
            p.vy += p.ay * dt
            p.x += p.vx * dt
            p.y += p.vy * dt

            # Add to trail
            p.trail.append(QPointF(p.x, p.y))
            if len(p.trail) > 100:  # limit trail length
                p.trail.pop(0)

        self.handle_collisions()
        self.update()

    def handle_collisions(self):
        to_remove = []
        for i in range(len(self.particles)):
            for j in range(i + 1, len(self.particles)):
                p1 = self.particles[i]
                p2 = self.particles[j]

                distance = math.hypot(p1.x - p2.x, p1.y - p2.y)
                if distance < p1.radius + p2.radius:
                    if p1.mass > p2.mass:
                        main = p1
                        other = p2
                    else:
                        main = p2
                        other = p1

                    main.mass += other.mass
                    main.radius = math.sqrt(main.mass)
                    main.vx = (main.vx * main.mass + other.vx * other.mass) / (main.mass + other.mass)
                    main.vy = (main.vy * main.mass + other.vy * other.mass) / (main.mass + other.mass)
                    to_remove.append(other)

        for p in to_remove:
            self.particles.remove(p)


class PresetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Preset System")

        layout = QVBoxLayout()
        self.list_widget = QComboBox()
        self.list_widget.addItems([
            "Binary Stars",
            "Solar System",
            "Galaxy Core",
            "Random Cluster"
        ])

        layout.addWidget(self.list_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

class GravitySimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2D Gravity Simulator")
        self.setGeometry(100, 100, 1200, 800)

        # Create canvas
        self.canvas = Canvas()
        self.setCentralWidget(self.canvas)

        # Setup controls
        self.create_controls()

        # Simulation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.simulate_step)
        self.dt = 0.1

        # Default values
        self.current_mass = 100.0
        self.current_vx = 0.0
        self.current_vy = 0.0

        preset_btn = QPushButton("Preset Systems")
        preset_btn.clicked.connect(self.show_presets)

    def show_presets(self):
        dialog = PresetDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_preset(dialog.list_widget.currentText())

    def load_preset(self, name):
        self.canvas.particles = []

        if name == "Binary Stars":
            self.create_binary_stars()
        elif name == "Solar System":
            self.create_solar_system()
        elif name == "Galaxy Core":
            self.create_galaxy_core()
        elif name == "Random Cluster":
            self.create_random_cluster()

        self.canvas.offset = QPointF(0, 0)
        self.canvas.scale = 1.0
        self.canvas.update()

    # Preset system creation methods
    def create_binary_stars(self):
        sun_color = QColor(255, 255, 0)
        offset = 300
        velocity = 1.5

        self.canvas.add_particle(Particle(
            QPointF(-offset, 0),
            mass=1000,
            velocity=(0, velocity),
            color=sun_color
        ))
        self.canvas.add_particle(Particle(
            QPointF(offset, 0),
            mass=1000,
            velocity=(0, -velocity),
            color=sun_color
        ))

    def create_solar_system(self):
        sun_color = QColor(255, 255, 0)
        planet_colors = [QColor(100, 100, 255), QColor(255, 100, 100), QColor(100, 255, 100)]

        # Sun
        self.canvas.add_particle(Particle(
            QPointF(0, 0),
            mass=5000,
            velocity=(0, 0),
            color=sun_color
        ))

        # Planets
        for i in range(3):
            distance = 150 * (i + 1)
            orbital_speed = math.sqrt(self.canvas.G * 5000 / distance)
            self.canvas.add_particle(Particle(
                QPointF(distance, 0),
                mass=10 + i * 5,
                velocity=(0, orbital_speed),
                color=planet_colors[i]
            ))

    def create_galaxy_core(self):
        # Central black hole
        self.canvas.add_particle(Particle(
            QPointF(0, 0),
            mass=10000,
            velocity=(0, 0),
            color=QColor(0, 0, 0)
        ))

        # Surrounding stars
        for i in range(50):
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(100, 500)
            mass = random.uniform(10, 50)
            orbital_speed = math.sqrt(self.canvas.G * 10000 / distance)

            self.canvas.add_particle(Particle(
                QPointF(distance * math.cos(angle), distance * math.sin(angle)),
                mass=mass,
                velocity=(orbital_speed * math.sin(angle), -orbital_speed * math.cos(angle)),
                color=QColor(random.randint(150, 255), random.randint(150, 255), random.randint(150, 255))
            ))

    def create_random_cluster(self):
        for _ in range(50):
            x = random.uniform(-400, 400)
            y = random.uniform(-400, 400)
            mass = random.uniform(10, 100)
            vx = random.uniform(-1, 1)
            vy = random.uniform(-1, 1)

            self.canvas.add_particle(Particle(
                QPointF(x, y),
                mass=mass,
                velocity=(vx, vy),
                color=QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            ))


    def create_controls(self):
        dock = QDockWidget("Controls", self)
        controls = QWidget()
        layout = QVBoxLayout()

        # Mass input
        self.mass_input = QLineEdit("100.0")
        layout.addWidget(QLabel("Mass (kg):"))
        layout.addWidget(self.mass_input)

        # Velocity inputs (stacked vertically)
        velocity_layout = QVBoxLayout()
        velocity_layout.addWidget(QLabel("Velocity:"))

        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("X:"))
        self.velocity_x = QLineEdit("0.0")
        x_layout.addWidget(self.velocity_x)
        velocity_layout.addLayout(x_layout)

        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Y:"))
        self.velocity_y = QLineEdit("0.0")
        y_layout.addWidget(self.velocity_y)
        velocity_layout.addLayout(y_layout)

        layout.addLayout(velocity_layout)

        # Color control
        self.color_combo = QComboBox()
        self.color_combo.addItems(["Random", "White", "Red", "Green", "Blue", "Yellow"])
        layout.addWidget(QLabel("Color:"))
        layout.addWidget(self.color_combo)

        # Control buttons (stacked vertically)
        btn_layout = QVBoxLayout()
        self.sim_btn = QPushButton("Start")
        self.sim_btn.clicked.connect(self.toggle_simulation)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_canvas)
        btn_layout.addWidget(self.sim_btn)
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)

        reset_view_btn = QPushButton("Reset View")
        reset_view_btn.clicked.connect(self.reset_view)
        btn_layout.addWidget(reset_view_btn)

        preset_btn = QPushButton("Preset Systems")
        preset_btn.clicked.connect(self.show_presets)
        layout.addWidget(preset_btn)  # Add to the local layout

        controls.setLayout(layout)
        dock.setWidget(controls)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def clear_canvas(self):
        self.canvas.particles = []
        self.canvas.update()

    def reset_view(self):
        self.canvas.offset = QPointF(0, 0)
        self.canvas.scale = 1.0
        self.canvas.update()


    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            try:
                # Convert screen to simulation coordinates
                pos = event.position()
                x = (pos.x() - self.canvas.offset.x()) / self.canvas.scale
                y = (pos.y() - self.canvas.offset.y()) / self.canvas.scale

                mass = float(self.mass_input.text())
                vx = float(self.velocity_x.text())
                vy = float(self.velocity_y.text())
                color = self.get_color()

                particle = Particle(
                    pos=QPointF(x, y),
                    mass=mass,
                    velocity=(vx, vy),
                    color=color
                )
                self.canvas.add_particle(particle)
            except ValueError:
                pass
        elif event.button() == Qt.MouseButton.LeftButton:
            self.canvas.last_pos = event.position()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.position() - self.canvas.last_pos
            self.canvas.offset += delta
            self.canvas.last_pos = event.position()
            self.canvas.update()

    def wheelEvent(self, event):
        zoom_factor = 1.1
        if event.angleDelta().y() < 0:
            zoom_factor = 1 / zoom_factor

        # Zoom relative to mouse position
        old_pos = (event.position() - self.canvas.offset) / self.canvas.scale
        self.canvas.scale *= zoom_factor
        new_pos = (event.position() - self.canvas.offset) / self.canvas.scale
        self.canvas.offset += (new_pos - old_pos) * self.canvas.scale

        self.canvas.update()

    def get_color(self):
        text = self.color_combo.currentText()
        if text == "Random":
            return QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        return {
            "White": QColor(255, 255, 255),
            "Red": QColor(255, 0, 0),
            "Green": QColor(0, 255, 0),
            "Blue": QColor(0, 0, 255),
            "Yellow": QColor(255, 255, 0)
        }[text]

    def toggle_simulation(self):
        if self.sim_btn.text() == "Start":
            self.sim_btn.setText("Stop")
            self.timer.start(16)
        else:
            self.sim_btn.setText("Start")
            self.timer.stop()

    def simulate_step(self):
        self.canvas.update_physics(self.dt)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GravitySimulator()
    window.show()
    sys.exit(app.exec())
