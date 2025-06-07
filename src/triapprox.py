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


import mylibrary.myutil as mu


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
		util.cast(self.thread.signal_target).connect(lambda img_size: self.display(img_size))
		util.cast(self.thread.signal_approx).connect(lambda img_size, img_data: self.display(img_size, img_data=img_data))
		util.cast(self.thread.signal_log).connect(self.thread_log)
		util.cast(self.thread.signal_finished).connect(self.thread_finished)

		self.plot = util.plot(self.widget, None, x=(0, Fitter.GENERATION), y=(0, 1))
		self.graph, self.values = None, []
		self.indicator = pyqtgraph.InfiniteLine(pos=0, pen="g")

		self.timer = util.timer(1000, self.clocking)
		self.preloads = {img_name: Fitter.load(img_name) for img_name in ["mona_lisa", "firefox", "darwin"]}
		self.targets = None
		self.radioButton_monalisa.click()

	def switch(self, img_name, img_size=128):
		self.targets = None
		util.pixmap(self.label_target, Qt.GlobalColor.transparent)
		util.pixmap(self.label_approx, Qt.GlobalColor.transparent)

		if img_name == "custom":
			path = QFileDialog.getOpenFileName(filter="*.png")[0]
			if not path:
				return
			self.targets = Fitter.load(path, preload=False)
		else:
			self.targets = self.preloads[img_name]
		self.display(img_size)

	def fit(self):
		if not self.targets:
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

			self.thread.targets = self.targets
			self.thread.start()

	def display(self, img_size, img_data=None):
		if img_data:
			image = QImage(img_data, img_size, img_size, img_size * 3, QImage.Format.Format_RGB888)
			self.label_approx.setPixmap(QPixmap(image))
		else:
			image = QImage(self.targets[img_size].data, img_size, img_size, img_size * 3, QImage.Format.Format_RGB888)
			self.label_target.setPixmap(QPixmap(image))

	def clocking(self):
		self.timer.second += 1
		h, m, s = self.timer.second // 3600, (self.timer.second // 60) % 60, self.timer.second % 60
		self.pushButton_fit.setText(f"{h:02}:{m:02}:{s:02}")
		if self.timer.second % 60 == 0:
			self.plot.addItem(pyqtgraph.InfiniteLine(pos=len(self.values), pen="m"))

	def thread_log(self, step, diff, perturbation):
		self.plainTextEdit_log2.setPlainText(
			f"{step + 1}\n"
			f"{diff:.4f}\n"
			f"{perturbation[0]}\n"
			f"{perturbation[1]}"
		)


		self.values.append(diff)
		self.graph.setData(self.values)
		self.indicator.setPos(step)

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
	def load(path, preload=True):
		path = f"../static/triapprox/{path}.png" if preload else path
		img = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
		return {
			16: cv2.GaussianBlur(cv2.resize(img, (16, 16)), (5, 5), 0).astype(np.uint8),
			32: cv2.GaussianBlur(cv2.resize(img, (32, 32)), (3, 3), 0).astype(np.uint8),
			64: cv2.resize(img, (64, 64)).astype(np.uint8),
			128: cv2.resize(img, (128, 128)).astype(np.uint8)
		}

	@staticmethod
	def tri_initialize(img_size):
		return tuple(np.random.randint(img_size, size=6)), tuple(np.random.randint(256, size=4))

	@staticmethod
	def tri_layer(img_size, triangle):
		layer = np.zeros((img_size, img_size, 4), dtype=np.uint8)
		(x1, y1, x2, y2, x3, y3), (r, g, b, a) = triangle
		pts = [np.array([(x1, y1), (x2, y2), (x3, y3)], dtype=int)]
		color = [int(b), int(g), int(r), int(a)]
		cv2.fillPoly(layer, pts, color)
		return layer[:, :, :-1], layer[:, :, -1:] / 255

	@staticmethod
	def tri_buffer(layers, tri, background, layer):
		layer, alpha = layer
		buffers = [alpha * layer + (1 - alpha) * background]
		for i in range(tri + 1, len(layers)):
			layer, alpha = layers[i]
			buffers.append(alpha * layer + (1 - alpha) * buffers[-1])
		return buffers

	@staticmethod
	def perturb(img_size, triangle, prob, perturbation):
		coord, color = triangle
		if prob:
			coord = tuple(c + random.randint(-perturbation[0], perturbation[0]) for c in coord)
		else:
			color = tuple(c + random.randint(-perturbation[1], perturbation[1]) for c in color)
		return np.clip(coord, 0, img_size - 1), np.clip(color, 0, 255)


class Thread(QThread):
	signal_target = pyqtSignal(int)
	signal_approx = pyqtSignal(int, bytes)
	signal_log = pyqtSignal(int, float, tuple)
	signal_finished = pyqtSignal()

	def __init__(self):
		super().__init__()
		self.running = False
		self.targets = None

	# @mu.performance
	def run(self):
		triangles = layers = buffers = img = diff = img_size = perturbation = None

		self.running = True
		for step in range(Fitter.GENERATION):
			if not self.running:
				break

			if (img_size is None) or (img_size == 16 and diff >= 0.8) or (img_size == 32 and diff >= 0.75) or (img_size == 64 and diff >= 0.65):
				if img_size is None:
					img_size = 8
				triangles, img_size, layers, buffers, img, diff = self.initialize_stage(img_size * 2, triangles)
				# triangles, img_size = self.initialize_stage(img_size * 2, triangles)

				util.cast(self.signal_target).emit(img_size)
				util.cast(self.signal_approx).emit(img_size, img.tobytes())


			# if img_size is None:
			# 	triangles, img_size, layers, buffers, img, diff = self.initialize_stage(16, triangles)
			# if img_size == 16 and diff >= 0.8:
			# 	triangles, img_size, layers, buffers, img, diff = self.initialize_stage(32, triangles)
			# if img_size == 32 and diff >= 0.75:
			# 	triangles, img_size, layers, buffers, img, diff = self.initialize_stage(64, triangles)
			# 	# print(f"{diff:.4f}")
			# if img_size == 64 and diff >= 0.65:
			# 	triangles, img_size, layers, buffers, img, diff = self.initialize_stage(128, triangles)

			if img_size == 128 and diff >= 0.75:
				break

			if img_size == 16:
				perturbation = 10, 35
			if img_size == 32:
				perturbation = 8, 30
			if img_size == 64:
				perturbation = 6, 25
			if img_size == 128:
				break
				perturbation = 4, 4
			if img_size == 128 and diff >= 0.6:
				perturbation = 3, 3
				break
			# if img_size == 128 and diff >= 0.575:
			# 	perturbation = 3, 3
			# if img_size == 128 and diff >= 0.625:
			# 	perturbation = 2, 2
			# if img_size == 128 and diff >= 0.675:
			# 	perturbation = 1, 1

			tri = Fitter.TRI[step]
			new_triangle = Fitter.perturb(img_size, triangles[tri], Fitter.PROB[step], perturbation)
			new_layer = Fitter.tri_layer(img_size, new_triangle)
			new_buffers = Fitter.tri_buffer(layers, tri, (Fitter.BASE[img_size] if tri == 0 else buffers[tri - 1]), new_layer)
			new_img = np.clip(new_buffers[-1], 0, 255).astype(np.uint8)
			new_diff = ssim(self.targets[img_size], new_img, channel_axis=2)

			if new_diff > diff:
				# if img_size == 128:
				# 	print((np.array(new_triangle[0]) - np.array(triangles[tri][0])).tolist(), (np.array(new_triangle[1]) - np.array(triangles[tri][1])).tolist())
				diff = new_diff
				img = new_img
				triangles[tri] = new_triangle
				layers[tri] = new_layer
				buffers[tri:] = new_buffers

			util.cast(self.signal_log).emit(step, diff, perturbation)
			util.cast(self.signal_approx).emit(img_size, img.tobytes())
		util.cast(self.signal_finished).emit()

	@staticmethod
	def initialize_stage(img_size, triangles):
		if triangles:
			triangles = [(tuple(t * 2 for t in triangle[0]), triangle[1]) for triangle in triangles]
		else:
			triangles = [Fitter.tri_initialize(img_size) for _ in range(Fitter.TRIANGLE_COUNT)]

		layers = [Fitter.tri_layer(img_size, triangle) for i, triangle in enumerate(triangles)]
		buffers = Fitter.tri_buffer(layers, 0, Fitter.BASE[img_size], layers[0])
		img = np.clip(buffers[-1], 0, 255).astype(np.uint8)
		diff = -1#ssim(self.targets[img_size], img, channel_axis=2)



		return triangles, img_size, layers, buffers, img, diff


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
