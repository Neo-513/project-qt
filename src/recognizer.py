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


class MyCore(QMainWindow, Ui_MainWindow):
	SIZE = {"canvas": (400, 400), "thumbnail": (28, 28)}
	MODEL = util.join_path(util.RESOURCE, "recognizer", "recognizer.pt")

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../recognizer/logo"))

		self.label_canvas.setPixmap(util.pixmap(self.SIZE["canvas"], Qt.GlobalColor.white))
		self.label_thumbnail.setPixmap(util.pixmap(self.SIZE["thumbnail"], Qt.GlobalColor.black))
		self.label_canvas.mousePressEvent = self.mouse_press
		self.label_canvas.mouseMoveEvent = self.mouse_move

		self.model = NN(NN.MNIST).to(NN.DEVICE)
		self.model.load_state_dict(torch.load(self.MODEL, map_location=NN.DEVICE))

	def process(self):
		image = self.label_canvas.pixmap().toImage()
		bits = image.bits()
		bits.setsize(image.sizeInBytes())
		threshold = 255 - np.frombuffer(bits, dtype=np.uint8).reshape((*self.SIZE["canvas"], 4))[:, :, 0]

		pixmap_canvas = self.label_canvas.pixmap()
		pixmap_canvas.fill(Qt.GlobalColor.white)
		self.label_canvas.setPixmap(pixmap_canvas)

		thumbnail = cv2.resize(threshold, self.SIZE["thumbnail"])
		pixmap_thumbnail = QPixmap().fromImage(QImage(thumbnail, *thumbnail.shape, QImage.Format.Format_Indexed8))
		self.label_thumbnail.setPixmap(pixmap_thumbnail)
		return np.array(thumbnail, np.float32)

	def recognize(self, inputs):
		with torch.no_grad():
			tensor = torch.from_numpy(inputs).reshape(-1, NN.MNIST["input"]).to(NN.DEVICE)
			outputs = self.model(tensor)
			_, result = torch.max(outputs, dim=1)
			self.label_result.setText(f"识别结果: {result.item()}")

	def keyPressEvent(self, event):
		if event.key() == Qt.Key.Key_Return:
			self.recognize(self.process())

	def mouse_press(self, event):
		self.label_canvas.pos = event.pos()

	def mouse_move(self, event):
		pixmap = self.label_canvas.pixmap()
		with QPainter(pixmap) as painter:
			painter.setPen(QPen(Qt.GlobalColor.black, 15))
			painter.drawLine(self.label_canvas.pos, event.pos())
		self.label_canvas.setPixmap(pixmap)
		self.label_canvas.pos = event.pos()


class NN(torch.nn.Module):
	DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
	MNIST = {"input": 28 * 28, "hidden": 512, "output": 10}

	def __init__(self, size):
		super().__init__()
		self.relu = torch.nn.ReLU()
		self.fc1 = torch.nn.Linear(size["input"], size["hidden"])
		self.fc2 = torch.nn.Linear(size["hidden"], size["output"])

	def forward(self, inputs):
		outputs = self.relu(self.fc1(inputs))
		outputs = self.fc2(outputs)
		return outputs


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
