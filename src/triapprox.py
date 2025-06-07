from PyQt6.QtCore import pyqtSignal, QThread, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow
from skimage.metrics import structural_similarity as ssim
from triapprox_ui import Ui_MainWindow
import cv2
import numpy as np
import random
import pyqtgraph
import sys
import util


class MyCore(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../triapprox/logo"))

		self.radioButton_monalisa.clicked.connect(lambda: self.switch("mona_lisa"))
		self.radioButton_firefox.clicked.connect(lambda: self.switch("firefox"))
		self.radioButton_darwin.clicked.connect(lambda: self.switch("darwin"))
		self.radioButton_custom.clicked.connect(lambda: self.switch("custom"))
		util.button(self.pushButton_fit, self.fit, "../triapprox/fit")

		self.thread = Thread()
		util.cast(self.thread.signal_reference).connect(lambda img_size: self.display(img_size))
		util.cast(self.thread.signal_approx).connect(lambda img_size, data: self.display(img_size, data=data))
		util.cast(self.thread.signal_log).connect(self.thread_log)
		util.cast(self.thread.signal_finished).connect(self.thread_finished)

		self.plot = util.plot(self.widget, None, x=(0, Fitter.GENERATION), y=(0, 1))
		self.graph, self.values = None, []
		self.indicator = pyqtgraph.InfiniteLine(pos=0, pen="g")

		self.timer = util.timer(1000, self.clocking)
		self.preloads = {name: self.load(name) for name in ["mona_lisa", "firefox", "darwin"]}
		self.references = None
		self.radioButton_monalisa.click()

	@staticmethod
	def load(path, preload=True):
		path = f"../static/triapprox/{path}.png" if preload else path
		reference = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
		return {
			16: cv2.GaussianBlur(cv2.resize(reference, (16, 16)), (5, 5), 0).astype(np.uint8),
			32: cv2.GaussianBlur(cv2.resize(reference, (32, 32)), (3, 3), 0).astype(np.uint8),
			64: cv2.resize(reference, (64, 64)).astype(np.uint8),
			128: cv2.resize(reference, (128, 128)).astype(np.uint8)
		}

	def switch(self, name, img_size=128):
		self.references = None
		util.pixmap(self.label_reference, Qt.GlobalColor.transparent)
		util.pixmap(self.label_approx, Qt.GlobalColor.transparent)

		if name == "custom":
			path = QFileDialog.getOpenFileName(filter="*.png")[0]
			if not path:
				return
			self.references = self.load(path, preload=False)
		else:
			self.references = self.preloads[name]
		self.display(img_size)

	def fit(self):
		if not self.references:
			return util.dialog("请选择图片", "error")

		if self.pushButton_fit.running:
			util.cast(self.thread.signal_finished).emit()
		else:
			util.toggle(self.pushButton_fit, "terminate")
			self.pushButton_fit.setText("00:00:00")

			self.radioButton_monalisa.setEnabled(False)
			self.radioButton_firefox.setEnabled(False)
			self.radioButton_darwin.setEnabled(False)
			self.radioButton_custom.setEnabled(False)

			self.plot.clear()
			self.graph = self.plot.plot([], [], pen="y")
			self.values.clear()
			self.plot.addItem(self.indicator)

			self.timer.second = 0
			self.timer.start()

			self.thread.references = self.references
			self.thread.start()

	def display(self, img_size, data=None):
		if data:
			image = QImage(data, img_size, img_size, img_size * 3, QImage.Format.Format_RGB888)
			self.label_approx.setPixmap(QPixmap(image))
		else:
			image = QImage(self.references[img_size].data, img_size, img_size, img_size * 3, QImage.Format.Format_RGB888)
			self.label_reference.setPixmap(QPixmap(image))

	def clocking(self):
		self.timer.second += 1
		h, m, s = self.timer.second // 3600, (self.timer.second // 60) % 60, self.timer.second % 60
		self.pushButton_fit.setText(f"{h:02}:{m:02}:{s:02}")
		if self.timer.second % 60 == 0:
			self.plot.addItem(pyqtgraph.InfiniteLine(pos=len(self.values), pen="m"))

	def thread_log(self, step, diff, perturbation):
		self.plainTextEdit_log2.setPlainText(f"{step + 1}\n{diff:.4f}\n{perturbation[0]}\n{perturbation[1]}")
		self.indicator.setPos(step)
		self.values.append(diff)
		self.graph.setData(self.values)

	def thread_finished(self):
		self.thread.running = False
		self.timer.stop()
		util.toggle(self.pushButton_fit, "../triapprox/fit")
		# self.pushButton_approx.setText("拟合")

		self.radioButton_monalisa.setEnabled(True)
		self.radioButton_firefox.setEnabled(True)
		self.radioButton_darwin.setEnabled(True)
		self.radioButton_custom.setEnabled(True)


class Fitter:
	TRIANGLE_COUNT = 50
	GENERATION = 100000
	IMG_SIZE = (16, 32, 64, 128)

	BASE = {img_size: np.zeros((img_size, img_size, 3), dtype=np.uint8) for img_size in IMG_SIZE}
	PROB = np.random.randint(2, size=GENERATION, dtype=np.uint8)
	TRI = np.random.randint(TRIANGLE_COUNT, size=GENERATION, dtype=np.uint8)

	@staticmethod
	def initialize(img_size):
		return tuple(np.random.randint(img_size, size=6)), tuple(np.random.randint(256, size=4))

	@staticmethod
	def perturb(img_size, triangle, prob, perturbation):
		coord, color = triangle
		if prob:
			coord = tuple(c + random.randint(-perturbation[0], perturbation[0]) for c in coord)
		else:
			color = tuple(c + random.randint(-perturbation[1], perturbation[1]) for c in color)
		return np.clip(coord, 0, img_size - 1), np.clip(color, 0, 255)

	@staticmethod
	def overlay(img_size, triangle):
		layer = np.zeros((img_size, img_size, 4), dtype=np.uint8)
		(x1, y1, x2, y2, x3, y3), (r, g, b, a) = triangle
		pts = [np.array([(x1, y1), (x2, y2), (x3, y3)], dtype=int)]
		color = int(b), int(g), int(r), int(a)
		cv2.fillPoly(layer, pts, color)
		return layer[:, :, :-1], layer[:, :, -1:] / 255

	@staticmethod
	def blend(layers, tri, background, layer):
		layer, alpha = layer
		buffers = [alpha * layer + (1 - alpha) * background]
		for i in range(tri + 1, len(layers)):
			layer, alpha = layers[i]
			buffers.append(alpha * layer + (1 - alpha) * buffers[-1])
		return buffers


class Thread(QThread):
	signal_reference = pyqtSignal(int)
	signal_approx = pyqtSignal(int, bytes)
	signal_log = pyqtSignal(int, float, tuple)
	signal_finished = pyqtSignal()

	def __init__(self):
		super().__init__()
		self.running = False
		self.references = None

	def run(self):
		buffers = approx = diff = perturbation = None



		img_size = None
		triangles, layers = [None] * Fitter.TRIANGLE_COUNT, [None] * Fitter.TRIANGLE_COUNT

		self.running = True
		for step in range(Fitter.GENERATION):
			if not self.running:
				break

			if img_size is None or (img_size == 16 and diff >= 0.8) or (img_size == 32 and diff >= 0.75) or (img_size == 64 and diff >= 0.65):
				img_size = (img_size * 2) if img_size else Fitter.IMG_SIZE[0]
				buffers, approx, diff = self.initialize_stage(img_size, triangles, layers)
				util.cast(self.signal_reference).emit(img_size)
				util.cast(self.signal_approx).emit(img_size, approx.tobytes())
				continue

			if img_size == 16:
				perturbation = 10, 35
			if img_size == 32:
				perturbation = 8, 30
			if img_size == 64:
				perturbation = 6, 25
			if img_size == 128:
				perturbation = 4, 4
			if img_size == 128 and diff >= 0.6:
				perturbation = 3, 3
				break
			if img_size == 128 and diff >= 0.75:
				break
			# if img_size == 128 and diff >= 0.575:
			# 	perturbation = 3, 3
			# if img_size == 128 and diff >= 0.625:
			# 	perturbation = 2, 2
			# if img_size == 128 and diff >= 0.675:
			# 	perturbation = 1, 1

			tri = Fitter.TRI[step]
			new_triangle = Fitter.perturb(img_size, triangles[tri], Fitter.PROB[step], perturbation)
			new_layer = Fitter.overlay(img_size, new_triangle)
			new_buffers = Fitter.blend(layers, tri, (Fitter.BASE[img_size] if tri == 0 else buffers[tri - 1]), new_layer)
			new_approx = np.clip(new_buffers[-1], 0, 255).astype(np.uint8)
			new_diff = ssim(self.references[img_size], new_approx, channel_axis=2)

			if new_diff > diff:
				diff = new_diff
				approx = new_approx
				triangles[tri] = new_triangle
				layers[tri] = new_layer
				buffers[tri:] = new_buffers

			util.cast(self.signal_log).emit(step, diff, perturbation)
			util.cast(self.signal_approx).emit(img_size, approx.tobytes())
		util.cast(self.signal_finished).emit()

	@staticmethod
	def initialize_stage(img_size, triangles, layers):
		for i, triangle in enumerate(triangles):
			triangles[i] = Fitter.initialize(img_size) if img_size == 16 else (tuple(c * 2 for c in triangle[0]), triangle[1])
		for i in range(len(layers)):
			layers[i] = Fitter.overlay(img_size, triangles[i])

		buffers = Fitter.blend(layers, 0, Fitter.BASE[img_size], layers[0])
		approx = np.clip(buffers[-1], 0, 255).astype(np.uint8)
		diff = -1
		return buffers, approx, diff


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
