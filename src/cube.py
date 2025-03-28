from cube_ui import Ui_MainWindow
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication, QMainWindow
from engine import *
from functools import partial
from itertools import product
import numpy as np
import re
import sys
import util

CAMERA = Camera()
CUBELET = Model.mirror()

ORDER = 3
IDENTITY = np.array([[[i * ORDER ** 2 + j * ORDER + k for k in range(ORDER)] for j in range(ORDER)] for i in range(ORDER)])
SPIN = np.zeros((ORDER, ORDER, ORDER, 3), dtype=int)

REGEX = re.compile("^[RrUuFfLlDdBb]['2]?$")
SLICE = {
	(1, 0, 0): [(i,) for i in range(ORDER)][::-1],
	(-1, 0, 0): [(i,) for i in range(ORDER)],
	(0, 1, 0): [(slice(None), i, slice(None)) for i in range(ORDER)][::-1],
	(0, -1, 0): [(slice(None), i, slice(None)) for i in range(ORDER)],
	(0, 0, 1): [(slice(None), slice(None), i) for i in range(ORDER)][::-1],
	(0, 0, -1): [(slice(None), slice(None), i) for i in range(ORDER)]
}


class MyCore(QMainWindow, Ui_MainWindow):
	identities, spins = None, None
	twist_axis, twist_angle, twist_delta, twist_bodily = None, None, None, None
	mouse_pos = None
	acts = []

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../cube/cube"))

		util.button(self.toolButton_replay, self.replay, "replay")

		util.button(self.pushButton_reset_camera, self.reset_camera)
		for act, a, offset in product("RUFLDB", " 0", (0, 32)):
			button_name = f"toolButton_{chr(ord(act) + offset)}{a}".strip()
			if hasattr(self, button_name):
				button = getattr(self, button_name)
				util.button(button, partial(self.acts.append, (chr(ord(act) + offset) + a).replace("0", "'")))
				button.setStyleSheet("font-size: 30px")

		self.openGLWidget.initializeGL = self.initialize_gl
		self.openGLWidget.resizeGL = self.resize_gl
		self.openGLWidget.paintGL = self.paint_gl

		util.button(self.pushButton_restore, self.restore)


		self.timer = QTimer()
		self.timer.setInterval(15)
		util.cast(self.timer).timeout.connect(self.openGLWidget.update)





	def initialize_gl(self, reset=True):
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		glEnable(GL_DEPTH_TEST)
		gluPerspective(60, self.openGLWidget.width() / self.openGLWidget.height(), 0.1, 100.)

		self.restore() if reset else None
		self.timer.start()

	def resize_gl(self, _weight, _height):
		self.initialize_gl(reset=False)

	def paint_gl(self):
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		CAMERA.translate()

		if self.checkBox.isChecked():
			Mesh.world_axes()
		glColor(1, 1, 1)

		if not self.twist_axis and self.acts:
			self.twist(self.acts.pop(0))
		self.twist_angle += self.twist_delta * bool(self.twist_axis)

		for i, j, k in product(range(ORDER), repeat=3):
			coordinate = i, j, k
			identity = self.identities[*coordinate]
			cubelet = (identity // ORDER ** 2, (identity % ORDER ** 2) // ORDER, identity % ORDER)

			glPushMatrix()
			self._rotate(coordinate)
			self._translate(coordinate)
			self._spin(cubelet)
			self._draw(identity, cubelet)
			glPopMatrix()

		if abs(self.twist_angle) == 90:
			self._transform()
			self.twist_axis, self.twist_angle, self.twist_delta, self.twist_bodily = None, 0, 0, False



	def _rotate(self, coordinate):
		twist_r = self.twist_axis == (1, 0, 0) and (coordinate[0] == ORDER - 1 or self.twist_bodily)
		twist_l = self.twist_axis == (-1, 0, 0) and (coordinate[0] == 0 or self.twist_bodily)
		twist_u = self.twist_axis == (0, 1, 0) and (coordinate[1] == ORDER - 1 or self.twist_bodily)
		twist_d = self.twist_axis == (0, -1, 0) and (coordinate[1] == 0 or self.twist_bodily)
		twist_f = self.twist_axis == (0, 0, 1) and (coordinate[2] == ORDER - 1 or self.twist_bodily)
		twist_b = self.twist_axis == (0, 0, -1) and (coordinate[2] == 0 or self.twist_bodily)
		if twist_r or twist_l or twist_u or twist_d or twist_f or twist_b:
			glRotate(self.twist_angle, *self.twist_axis)

	@staticmethod
	def _translate(coordinate):
		glTranslate(*(np.array(coordinate) - (ORDER - 1) / 2))

	def _spin(self, cubelet):
		if self.spins[*cubelet, 0] > 0:
			glRotate(self.spins[*cubelet, 0], *(-1, 0, 0))


		if self.spins[*cubelet, 0] < 0:
			glRotate(self.spins[*cubelet, 0], *(1, 0, 0))

		if self.spins[*cubelet, 1] > 0:
			glRotate(self.spins[*cubelet, 1], *(0, -1, 0))
		if self.spins[*cubelet, 1] < 0:
			glRotate(self.spins[*cubelet, 1], *(0, 1, 0))

		if self.spins[*cubelet, 2] > 0:
			glRotate(self.spins[*cubelet, 2], *(0, 0, -1))
		if self.spins[*cubelet, 2] < 0:
			glRotate(self.spins[*cubelet, 2], *(0, 0, 1))

	def _transform(self):
		for i, j, k in product(range(ORDER), repeat=3):
			twist_r = self.twist_axis == (1, 0, 0) and (i == ORDER - 1 or self.twist_bodily)
			twist_l = self.twist_axis == (-1, 0, 0) and (i == 0 or self.twist_bodily)
			twist_u = self.twist_axis == (0, 1, 0) and (j == ORDER - 1 or self.twist_bodily)
			twist_d = self.twist_axis == (0, -1, 0) and (j == 0 or self.twist_bodily)
			twist_f = self.twist_axis == (0, 0, 1) and (k == ORDER - 1 or self.twist_bodily)
			twist_b = self.twist_axis == (0, 0, -1) and (k == 0 or self.twist_bodily)

			coordinate = i, j, k
			identity = self.identities[*coordinate]
			cubelet = (identity // ORDER ** 2, (identity % ORDER ** 2) // ORDER, identity % ORDER)

			rot = (self.twist_delta // abs(self.twist_delta)) * 90
			if twist_r or twist_l:
				self.spins[*cubelet] += (rot, 0, 0)
			if twist_u or twist_d:
				self.spins[*cubelet] += (0, rot, 0)
			if twist_f or twist_b:
				self.spins[*cubelet] += (0, 0, rot)

			if cubelet == (2, 2, 2):
				print(self.spins[*cubelet])






		rot = self.twist_delta // abs(self.twist_delta)
		rot *= 1 if self.twist_axis in ((1, 0, 0), (0, -1, 0), (0, 0, 1)) else -1
		for s in SLICE[self.twist_axis][:ORDER * self.twist_bodily + 1]:
			self.identities[s] = np.rot90(self.identities[s], rot)

	@staticmethod
	def _draw(identity, cubelet):
		#fill = identity in (0, 2, 6, 8, 18, 20, 24, 26)
		fill = identity == 26
		#fill = False
		CUBELET[*cubelet].draw(fill)

	def twist(self, act):
		if not self.twist_axis:
			self.twist_axis = (
				"Rr".count(act[0]) - "Ll".count(act[0]),
				"Uu".count(act[0]) - "Dd".count(act[0]),
				"Ff".count(act[0]) - "Bb".count(act[0])
			)
			self.twist_angle = 0
			self.twist_delta = (1 if act[-1] == "'" else -1) * 6
			self.twist_bodily = act.islower()






	def restore(self):
		self.reset_camera()
		self.identities, self.spins = IDENTITY.copy(), SPIN.copy()
		self.twist_axis, self.twist_angle, self.twist_delta, self.twist_bodily = None, 0, 0, False



	def replay(self):
		self.acts.clear()
		acts = [a.strip() for a in self.lineEdit.text().split(" ") if a.strip()]
		for a in acts:
			a = a.strip()
			if not a:
				continue

			if not REGEX.fullmatch(a):
				return util.dialog("公式输入有误", "error")

			self.acts.append(a)
			if a[-1] == "2":
				self.acts.append(a)
















	def keyPressEvent(self, a0):
		if a0.key() == Qt.Key.Key_Up or a0.key() == Qt.Key.Key_W:
			CAMERA.translate("U")
		elif a0.key() == Qt.Key.Key_Down or a0.key() == Qt.Key.Key_S:
			CAMERA.translate("D")
		elif a0.key() == Qt.Key.Key_Left or a0.key() == Qt.Key.Key_A:
			CAMERA.translate("L")
		elif a0.key() == Qt.Key.Key_Right or a0.key() == Qt.Key.Key_D:
			CAMERA.translate("R")

	def mousePressEvent(self, a0):
		self.mouse_pos = a0.pos()

	def mouseMoveEvent(self, a0):
		mouse_previous = np.array([self.mouse_pos.x(), self.mouse_pos.y()])
		mouse_current = np.array([a0.pos().x(), a0.pos().y()])
		mouse_change = mouse_current - mouse_previous
		CAMERA.rotate(-mouse_change[0], mouse_change[1])
		self.mouse_pos = a0.pos()

	def wheelEvent(self, a0):
		if a0.angleDelta().y() > 0:
			CAMERA.scaled(1)
		elif a0.angleDelta().y() < 0:
			CAMERA.scaled(-1)




	@staticmethod
	def reset_camera():
		pass
		#CAMERA.forward, CAMERA.right, CAMERA.up = FORWARD, RIGHT, UP
		#CAMERA.eye, CAMERA.yaw, CAMERA.pitch = EYE, YAW, PITCH
		#print(CAMERA.eye)
		#gluLookAt(*CAMERA.eye, *(CAMERA.eye + CAMERA.forward), *CAMERA.up)




if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
