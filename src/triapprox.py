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
		util.cast(self.thread.signal_display).connect(self.thread_display)
		util.cast(self.thread.signal_log).connect(self.thread_log)
		util.cast(self.thread.signal_finished).connect(self.thread_finished)

		self.plot = util.plot(self.widget, None, x=(0, Fitter.MAX_ITERATION), y=(0, 1))
		self.graph, self.values = None, []
		self.indicator = pyqtgraph.InfiniteLine(pos=0, pen="g")

		self.timer = util.timer(1000, self.clocking)
		self.preloads = {name: self.load(name) for name in ("mona_lisa", "firefox", "darwin")}
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
		self.display(self.label_reference, img_size)

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

	def display(self, canvas, img_size, img_bytes=None):
		img_data = self.references[img_size].data if img_bytes is None else img_bytes
		image = QImage(img_data, img_size, img_size, img_size * 3, QImage.Format.Format_RGB888)
		canvas.setPixmap(QPixmap(image))

	def clocking(self):
		self.timer.second += 1
		h, m, s = self.timer.second // 3600, (self.timer.second // 60) % 60, self.timer.second % 60
		self.pushButton_fit.setText(f"{h:02}:{m:02}:{s:02}")
		self.plot.addItem(pyqtgraph.InfiniteLine(pos=len(self.values), pen="m")) if self.timer.second % 60 == 0 else None

	def thread_display(self, approx_bytes, refresh_reference):
		img_size = self.thread.img_size
		self.display(self.label_reference, img_size) if refresh_reference else None
		self.display(self.label_approx, img_size, img_bytes=approx_bytes)

	def thread_log(self, iteration):
		self.plainTextEdit_log.setPlainText(
			f"iteration:\t    {iteration + 1}\n\n"
			f"metric:\t    {self.thread.metric:.4f} (ssim)\n\n"
			f"pertubation:\t    {self.thread.perturbation[0]} (coord)  {self.thread.perturbation[1]} (color)"
		)

		self.indicator.setPos(iteration)
		self.values.append(self.thread.metric)
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
	SUPPORTED_SIZES = 16, 32, 64, 128
	BACKGROUND = {img_size: np.zeros((img_size, img_size, 3), dtype=np.uint8) for img_size in SUPPORTED_SIZES}#float32

	@staticmethod
	def initialize(triangles):
		for i in range(len(triangles)):
			coord = tuple(np.random.randint(Fitter.SUPPORTED_SIZES[0], size=6).tolist())
			color = tuple(np.random.randint(256, size=4).tolist())
			triangles[i] = coord, color

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
	def blend(tri, texs, masks, composites, new_tex, new_mask, background):
		composites[tri] = new_mask * new_tex + (1 - new_mask) * background
		for i in range(tri + 1, len(composites)):
			tex, mask = texs[i], masks[i]
			composites[i] = mask * tex + (1 - mask) * composites[i - 1]


class Thread(QThread):
	signal_display = pyqtSignal(bytes, bool)
	signal_log = pyqtSignal(int)
	signal_finished = pyqtSignal()

	def __init__(self):
		super().__init__()
		self.references = None
		self.running = False

		self.img_size = self.metric = self.perturbation = None
		self.triangles = [(None, None)] * Fitter.TRIANGLE_COUNT
		self.texs = [None] * Fitter.TRIANGLE_COUNT
		self.masks = [None] * Fitter.TRIANGLE_COUNT
		self.composites = [None] * Fitter.TRIANGLE_COUNT

		self.layer_buffer = {img_size: np.zeros((img_size, img_size, 4), dtype=np.uint8) for img_size in Fitter.SUPPORTED_SIZES}
		self.composites_buffer = [None] * Fitter.TRIANGLE_COUNT

	def run(self):
		self.img_size = self.metric = 0
		self.perturbation = 0, 0
		Fitter.initialize(self.triangles)

		probs = np.random.randint(2, size=Fitter.MAX_ITERATION, dtype=np.uint8)
		tris = np.random.randint(Fitter.TRIANGLE_COUNT, size=Fitter.MAX_ITERATION, dtype=np.uint8)

		self.running = True
		for iteration in range(Fitter.MAX_ITERATION):
			if not self.running:
				break

			approx = self.advance_stage()
			if approx is not None:
				util.cast(self.signal_display).emit(approx.tobytes(), True)
				continue

			if self.img_size == 16:
				self.perturbation = 10, 35
			if self.img_size == 32:
				self.perturbation = 8, 30
			if self.img_size == 64:
				self.perturbation = 6, 25
			if self.img_size == 128:
				self.perturbation = 4, 4
			if self.img_size == 128 and self.metric >= 0.55:
				break
			if self.img_size == 128 and self.metric >= 0.6:
				self.perturbation = 3, 3
				break
			if self.img_size == 128 and self.metric >= 0.75:
				break
			# if self.img_size == 128 and self.metric >= 0.575:
			# 	self.perturbation = 3, 3
			# if self.img_size == 128 and self.metric >= 0.625:
			# 	self.perturbation = 2, 2
			# if self.img_size == 128 and self.metric >= 0.675:
			# 	self.perturbation = 1, 1

			candidate = self.propose_candidate(tris[iteration], probs[iteration])
			if candidate[-1] > self.metric:
				self.update_candidate(tris[iteration], candidate)
			util.cast(self.signal_log).emit(iteration)

		util.cast(self.signal_finished).emit()

	def advance_stage(self):
		is_first_stage = self.img_size == 0
		should_advance_stage = (
			(self.img_size == 16 and self.metric >= 0.8) or
			(self.img_size == 32 and self.metric >= 0.75) or
			(self.img_size == 64 and self.metric >= 0.65)
		)
		if not is_first_stage and not should_advance_stage:
			return

		self.img_size = (self.img_size * 2) if should_advance_stage else Fitter.SUPPORTED_SIZES[0]
		# self.metric = 0
		scale = 2 if should_advance_stage else 1

		for i, triangle in enumerate(self.triangles):
			self.triangles[i] = tuple(c * scale for c in triangle[0]), triangle[1]
			self.texs[i], self.masks[i] = Fitter.rasterize(self.triangles[i], self.layer_buffer[self.img_size])

		Fitter.blend(0, self.texs, self.masks, self.composites, self.texs[0], self.masks[0], Fitter.BACKGROUND[self.img_size])
		for i, composite in enumerate(self.composites):
			self.composites_buffer[i] = composite.copy()
		approx = np.clip(self.composites[-1], 0, 255).astype(np.uint8)
		self.metric = min(max(ssim(self.references[self.img_size], approx, channel_axis=2), 0), 1)
		return approx

	def propose_candidate(self, tri, prob):
		background = Fitter.BACKGROUND[self.img_size] if tri == 0 else self.composites[tri - 1]
		triangle = Fitter.perturb(self.triangles[tri], prob, self.perturbation, (0, self.img_size - 1))
		tex, mask = Fitter.rasterize(triangle, self.layer_buffer[self.img_size])
		Fitter.blend(tri, self.texs, self.masks, self.composites_buffer, tex, mask, background)
		approx = np.clip(self.composites_buffer[-1], 0, 255).astype(np.uint8)
		metric = min(max(ssim(self.references[self.img_size], approx, channel_axis=2), 0), 1)
		return triangle, tex, mask, approx, metric

	def update_candidate(self, tri, candidate):
		new_triangle, new_tex, new_mask, new_approx, new_metric = candidate
		self.triangles[tri] = new_triangle
		self.texs[tri] = new_tex
		self.masks[tri] = new_mask
		# self.composites[tri:] = self.composites_buffer.copy()
		for i in range(tri, len(self.composites)):
			self.composites[i] = self.composites_buffer[i].copy()
		self.metric = new_metric
		util.cast(self.signal_display).emit(new_approx.tobytes(), False)


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
