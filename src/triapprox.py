from PyQt6.QtCore import pyqtSignal, QThread, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow
from skimage.metrics import structural_similarity as ssim
from triapprox_ui import Ui_MainWindow
import cv2
import numpy as np
import pyqtgraph
import random
import sys
import util


class MyCore(QMainWindow, Ui_MainWindow):
	LOG = "\n\n".join(["iteration:\t    %s", "metric:\t    %s (%s)", "pertubation:\t    %s (coord)  %s (color)"])
	PRELOAD = "mona_lisa", "firefox", "darwin"

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

		self.plot = util.plot(self.widget, None, x=(0, Fitter.MAX_ITERATION), y=(0, 1))
		self.graph, self.values = None, []
		self.indicator = pyqtgraph.InfiniteLine(pos=0, pen="g")

		self.timer = util.timer(1000, self.clocking)
		self.preloads = {name: self.load(name) for name in self.PRELOAD}
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

	def thread_log(self, iteration, method, metric, perturbation):
		self.plainTextEdit_log.setPlainText(self.LOG % (iteration + 1, f"{metric:.4f}", method, *perturbation))
		self.indicator.setPos(iteration)
		self.values.append(metric)
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
	MAX_ITERATION = 100000
	IMG_SIZE = (16, 32, 64, 128)

	BACKGROUND = {img_size: np.zeros((img_size, img_size, 3), dtype=np.uint8) for img_size in IMG_SIZE}
	LAYER = {img_size: np.zeros((img_size, img_size, 4), dtype=np.uint8) for img_size in IMG_SIZE}#float32

	@staticmethod
	def initialize(img_size):
		return tuple(np.random.randint(img_size, size=6).tolist()), tuple(np.random.randint(256, size=4).tolist())

	@staticmethod
	def perturb(triangle, prob, perturbation, coord_bounds, color_bounds=(0, 255)):
		coord, color = triangle
		if prob:
			coord = [c + random.randint(-perturbation[0], perturbation[0]) for c in coord]
		else:
			color = [c + random.randint(-perturbation[1], perturbation[1]) for c in color]
		coord = tuple(np.clip(coord, coord_bounds[0], coord_bounds[1]).tolist())
		color = tuple(np.clip(color, color_bounds[0], color_bounds[1]).tolist())
		return coord, color

	@staticmethod
	def rasterize(triangle, layer):
		layer.fill(0)
		(x1, y1, x2, y2, x3, y3), (r, g, b, a) = triangle
		cv2.fillPoly(layer, [np.array([(x1, y1), (x2, y2), (x3, y3)])], [b, g, r, a])
		return layer[..., :-1].copy(), layer[..., -1:].copy() / 255

	@staticmethod
	def blend(overlay_texs, overlay_masks, new_tex, new_mask, background):
		buffers = [new_mask * new_tex + (1 - new_mask) * background]
		for tex, mask in zip(overlay_texs, overlay_masks):
			buffers.append(mask * tex + (1 - mask) * buffers[-1])
		return buffers

	@staticmethod
	def evaluate(reference, approx, method):
		if method == "mse":
			return 1 - np.mean((reference.astype(np.float32) / 255 - approx.astype(np.float32) / 255) ** 2)
		if method == "ssim":
			return min(max(ssim(reference, approx, channel_axis=2), 0), 1)
		return 0


class Thread(QThread):
	signal_reference = pyqtSignal(int)
	signal_approx = pyqtSignal(int, bytes)
	signal_log = pyqtSignal(int, str, float, tuple)
	signal_finished = pyqtSignal()

	def __init__(self):
		super().__init__()
		self.running = False
		self.references = None

	def run(self):
		self.running = True
		probs = np.random.randint(2, size=Fitter.MAX_ITERATION, dtype=np.uint8)
		tris = np.random.randint(Fitter.TRIANGLE_COUNT, size=Fitter.MAX_ITERATION, dtype=np.uint8)

		img_size = perturbation = buffers = metric = None
		triangles = [(None, None)] * Fitter.TRIANGLE_COUNT
		texs, masks = [None] * Fitter.TRIANGLE_COUNT, [None] * Fitter.TRIANGLE_COUNT

		for iteration in range(Fitter.MAX_ITERATION):
			if not self.running:
				break

			is_first_stage = img_size is None
			should_upgrade_from_16 = img_size == 16 and metric >= 0.8
			should_upgrade_from_32 = img_size == 32 and metric >= 0.75
			should_upgrade_from_64 = img_size == 64 and metric >= 0.65

			if is_first_stage or should_upgrade_from_16 or should_upgrade_from_32 or should_upgrade_from_64:
				img_size = Fitter.IMG_SIZE[0] if is_first_stage else (img_size * 2)
				for i, triangle in enumerate(triangles):
					coord, color = triangle
					triangles[i] = Fitter.initialize(img_size) if is_first_stage else (tuple(c * 2 for c in coord), color)
					texs[i], masks[i] = Fitter.rasterize(triangles[i], Fitter.LAYER[img_size])

				buffers = Fitter.blend(texs[1:], masks[1:], texs[0], masks[0], Fitter.BACKGROUND[img_size])
				approx = np.clip(buffers[-1], 0, 255).astype(np.uint8)
				metric = 0

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
			if img_size == 128 and metric >= 0.5:
				break
			if img_size == 128 and metric >= 0.6:
				perturbation = 3, 3
				break
			if img_size == 128 and metric >= 0.75:
				break
			# if img_size == 128 and metric >= 0.575:
			# 	perturbation = 3, 3
			# if img_size == 128 and metric >= 0.625:
			# 	perturbation = 2, 2
			# if img_size == 128 and metric >= 0.675:
			# 	perturbation = 1, 1

			tri = tris[iteration]
			background = Fitter.BACKGROUND[img_size] if tri == 0 else buffers[tri - 1]
			if img_size == 128:
				method = "ssim"
			else:
				method = "mse"
			method = "ssim"

			new_triangle = Fitter.perturb(triangles[tri], probs[iteration], perturbation, (0, img_size - 1))
			new_tex, new_mask = Fitter.rasterize(new_triangle, Fitter.LAYER[img_size])
			new_buffers = Fitter.blend(texs[tri + 1:], masks[tri + 1:], new_tex, new_mask, background)
			new_approx = np.clip(new_buffers[-1], 0, 255).astype(np.uint8)
			new_metric = Fitter.evaluate(self.references[img_size], new_approx, method)

			if new_metric > metric:
				triangles[tri], texs[tri], masks[tri] = new_triangle, new_tex, new_mask
				buffers[tri:], approx, metric = new_buffers, new_approx, new_metric
				util.cast(self.signal_approx).emit(img_size, approx.tobytes())
			util.cast(self.signal_log).emit(iteration, method, metric, perturbation)

		util.cast(self.signal_finished).emit()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
