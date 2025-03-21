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

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../recognizer/logo"))

		self.label_canvas.setPixmap(util.pixmap(self.SIZE["canvas"], Qt.GlobalColor.white))
		self.label_thumbnail.setPixmap(util.pixmap(self.SIZE["thumbnail"], Qt.GlobalColor.black))
		self.label_canvas.mousePressEvent = self.mouse_press
		self.label_canvas.mouseMoveEvent = self.mouse_move

		self.model = NN().to(NN.DEVICE)
		self.model.path = util.join_path(util.RESOURCE, "recognizer", "recognizer.pt")
		self.model.load_state_dict(torch.load(self.model.path, map_location=NN.DEVICE))

	def recognize(self):
		image = self.label_canvas.pixmap().toImage()
		handwriting = int("FF000000", 16)

		threshold = np.zeros(self.SIZE["canvas"], dtype=np.uint8)
		for pos in product(range(threshold.shape[0]), range(threshold.shape[1])):
			if image.pixel(*pos) == handwriting:
				threshold[pos] = 255

		thumb = cv2.resize(threshold.T, self.SIZE["thumbnail"])
		pixmap_thumbnail = QPixmap().fromImage(QImage(thumb, *thumb.shape, QImage.Format.Format_Indexed8))
		self.label_thumbnail.setPixmap(pixmap_thumbnail)

		pixmap_canvas = self.label_canvas.pixmap()
		pixmap_canvas.fill(Qt.GlobalColor.white)
		self.label_canvas.setPixmap(pixmap_canvas)

		with torch.no_grad():
			array_tensor = torch.from_numpy(np.array(thumb, np.float32))
			array_reshape = array_tensor.reshape(-1, NN.SIZE["input"]).to(NN.DEVICE)
			output = self.model(array_reshape)
			result = np.argmax(output.cpu().detach().numpy(), axis=1)[0]
			self.label_result.setText(f"识别结果: {result}")

	def keyPressEvent(self, event):
		if event.key() == Qt.Key.Key_Return:
			self.recognize()

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
	SIZE = {"input": 28 * 28, "hidden": 500, "output": 10}
	DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

	def __init__(self):
		super().__init__()
		self.l1 = torch.nn.Linear(NN.SIZE["input"], NN.SIZE["hidden"])
		self.relu = torch.nn.ReLU()
		self.l2 = torch.nn.Linear(NN.SIZE["hidden"], NN.SIZE["output"])

	def forward(self, x):
		result_input = self.l1(x)
		result_hidden = self.relu(result_input)
		result_output = self.l2(result_hidden)
		return result_output


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
