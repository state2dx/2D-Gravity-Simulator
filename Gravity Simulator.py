import sys
import math
import random
from PyQt6.QtCore import QTimer, QPointF, Qt, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPalette
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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Apply view transformation
        painter.translate(self.offset)
        painter.scale(self.scale, self.scale)

        # Remove outline by setting pen to NoPen
        painter.setPen(Qt.PenStyle.NoPen)

        for p in self.particles:
            painter.setBrush(QBrush(p.color))
            painter.drawEllipse(QPointF(p.x, p.y), p.radius, p.radius)

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

        controls.setLayout(layout)
        dock.setWidget(controls)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def clear_canvas(self):
        self.canvas.particles = []
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