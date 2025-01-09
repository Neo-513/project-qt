from recognizer_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import product
import cv2
import numpy as np
import sys
import torch
import util

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
INPUT_SIZE, HIDDEN_SIZE, OUTPUT_SIZE = 28 * 28, 500, 10
MODEL = util.join_path(util.RESOURCE, "recognizer", "recognizer.pt")


class MyCore(QMainWindow, Ui_MainWindow):
	pos = None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../recognizer/brain"))

		util.button(self.pushButton, self.recognize, "../recognizer/scan")
		util.button(self.toolButton, self.clear, "clean")

		self.model = NN().to(DEVICE)
		self.model.load_state_dict(torch.load(MODEL, map_location=DEVICE))

		self.canvas_size = self.label_canvas.minimumWidth(), self.label_canvas.minimumHeight()
		self.thumbnail_size = self.label_thumbnail.minimumWidth(), self.label_thumbnail.minimumHeight()

		self.label_canvas.setPixmap(QPixmap(*self.canvas_size))
		self.label_thumbnail.setPixmap(QPixmap(*self.thumbnail_size))
		self.clear()

	def recognize(self):
		array_thumbnail = self.thumbnail()
		with torch.no_grad():
			array_tensor = torch.from_numpy(np.array(array_thumbnail, np.float32))
			array_reshape = array_tensor.reshape(-1, INPUT_SIZE).to(DEVICE)
			output = self.model(array_reshape)
			result = np.argmax(output.cpu().detach().numpy(), axis=1)[0]
			self.label_result.setText(f"识别结果: {result}")

	def thumbnail(self):
		image = self.label_canvas.pixmap().toImage()
		array_image = np.zeros((*self.canvas_size, 4), dtype=np.uint8)
		for x, y in product(range(self.canvas_size[0]), range(self.canvas_size[1])):
			array_image[x, y] = (255, 255, 255, 255) if image.pixel(x, y) == 4294967295 else (0, 0, 0, 255)

		array_gray = cv2.cvtColor(array_image, cv2.COLOR_RGB2GRAY)
		array_threshold = cv2.threshold(array_gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
		array_thumbnail = cv2.resize(array_threshold.T, self.thumbnail_size)

		image = QImage(array_thumbnail.data, *self.thumbnail_size, self.thumbnail_size[0], QImage.Format.Format_Indexed8)
		self.label_thumbnail.setPixmap(QPixmap().fromImage(image, Qt.ImageConversionFlag.AutoColor))
		return array_thumbnail

	def mousePressEvent(self, a0):
		self.pos = a0.pos()

	def mouseMoveEvent(self, a0):
		pixmap = self.label_canvas.pixmap()
		with QPainter(pixmap) as painter:
			painter.setPen(QPen(Qt.GlobalColor.black, 15))
			painter.drawLine(self.pos, a0.pos())
		self.label_canvas.setPixmap(pixmap)
		self.pos = a0.pos()

	def clear(self):
		pixmap_canvas = self.label_canvas.pixmap()
		pixmap_canvas.fill(Qt.GlobalColor.white)
		self.label_canvas.setPixmap(pixmap_canvas)

		pixmap_thumbnail = self.label_thumbnail.pixmap()
		pixmap_thumbnail.fill(Qt.GlobalColor.black)
		self.label_thumbnail.setPixmap(pixmap_thumbnail)

		self.label_result.clear()


class NN(torch.nn.Module):
	def __init__(self):
		super().__init__()
		self.l1 = torch.nn.Linear(INPUT_SIZE, HIDDEN_SIZE)
		self.relu = torch.nn.ReLU()
		self.l2 = torch.nn.Linear(HIDDEN_SIZE, OUTPUT_SIZE)

	def forward(self, x):
		output = self.l1(x)
		output = self.relu(output)
		output = self.l2(output)
		return output


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
