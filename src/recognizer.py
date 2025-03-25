from recognizer_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QMainWindow
import cv2
import numpy as np
import sys
import torch
import util

MODEL = util.join_path(util.RESOURCE, "recognizer", "recognizer.pt")


class MyCore(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../recognizer/logo"))

		util.pixmap(self.label_canvas, size=self.label_canvas.minimumSize(), color=Qt.GlobalColor.white)
		util.pixmap(self.label_thumbnail, size=self.label_thumbnail.minimumSize(), color=Qt.GlobalColor.black)
		self.label_canvas.mousePressEvent = self.mouse_press
		self.label_canvas.mouseMoveEvent = self.mouse_move

		self.model = NN(NN.MNIST).to(NN.DEVICE)
		self.model.load_state_dict(torch.load(MODEL, map_location=NN.DEVICE))

	def recognize(self):
		size_canvas = self.label_canvas.minimumWidth(), self.label_canvas.minimumHeight()
		size_thumbnail = self.label_thumbnail.minimumWidth(), self.label_thumbnail.minimumHeight()

		image = self.label_canvas.pixmap().toImage()
		bits = image.constBits()
		bits.setsize(image.sizeInBytes())
		threshold = 255 - np.frombuffer(bits, dtype=np.uint8).reshape((*size_canvas, 4))[:, :, 0]
		thumbnail = cv2.resize(threshold, size_thumbnail, interpolation=cv2.INTER_AREA)

		util.pixmap(self.label_canvas, color=Qt.GlobalColor.white)
		util.pixmap(self.label_thumbnail, image=QImage(thumbnail, *thumbnail.shape, QImage.Format.Format_Indexed8))

		with torch.no_grad():
			inputs = np.array(thumbnail, np.float32)
			tensor = torch.from_numpy(inputs).reshape(-1, NN.MNIST["input"]).to(NN.DEVICE)
			outputs = self.model(tensor)
			_, result = torch.max(outputs, dim=1)
			self.label_result.setText(f"识别结果: {result.item()}")

	def keyPressEvent(self, event):
		if event.key() == Qt.Key.Key_Return:
			self.recognize()

	def mouse_press(self, event):
		self.label_canvas.pos = event.pos()

	def mouse_move(self, event):
		pixmap = self.label_canvas.pixmap()
		with QPainter(pixmap) as painter:
			painter.setPen(QPen(Qt.GlobalColor.black, 24))
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
