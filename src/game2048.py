from game2048_ui import Ui_MainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import product
import numpy as np
import random
import sys
import util

QSS = (
	"font-size: 40px;"
	"font-weight: bold;"
	"background-color: %s;"
	"color: rgb(118,110,101);"
)
COLOR = {
	0: "rgb(205,193,180)", 2: "rgb(238,228,218)", 4: "rgb(237,224,200)", 8: "rgb(242,177,121)",
	16: "rgb(245,149,99)", 32: "rgb(246,124,95)", 64: "rgb(246,94,59)", 128: "rgb(237,207,114)",
	256: "rgb(237,204,97)", 512: "rgb(228,192,42)", 1024: "rgb(226,186,19)", 2048: "rgb(236,196,0)"
}
ROTATE = {
	Qt.Key.Key_Up: 1,
	Qt.Key.Key_Down: -1,
	Qt.Key.Key_Left: 0,
	Qt.Key.Key_Right: 2
}


class QtCore(QMainWindow, Ui_MainWindow):
	field = np.zeros((4, 4), dtype=int)

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../game2048/2048"))

		self.statusbar.showMessage("按 ↑ ↓ ← → 操作, 按 Enter 重新开始")
		self.restart()

	def restart(self):
		self.field.fill(0)
		self.add_num(2)
		self.add_num(2)

	def keyPressEvent(self, a0):
		if a0.key() == Qt.Key.Key_Return:
			return self.restart()
		if a0.key() not in ROTATE:
			return

		previous = self.field.copy()
		self.field = np.rot90(self.field, ROTATE[util.cast(a0.key())])
		self.merge_towards_left()
		self.field = np.rot90(self.field, -ROTATE[util.cast(a0.key())])

		if self.field.tolist() != previous.tolist():
			self.add_num(random.choice([2, 4]))
		if np.isin(self.field, 2048).any():
			util.dialog("You won", "success")
			return self.restart()

		horizontal_filed, vertical_field = self.field, np.rot90(self.field)
		horizontally = np.equal(horizontal_filed[1:], np.roll(horizontal_filed, 1, axis=0)[1:])
		vertically = np.equal(vertical_field[1:], np.roll(vertical_field, 1, axis=0)[1:])

		if np.any(horizontally) or np.any(vertically):
			return
		if not np.isin(self.field, 0).any():
			util.dialog("You lose", "error")
			return self.restart()

	def merge_towards_left(self):
		for i in range(4):
			row = self.field[i][self.field[i] != 0]
			for j in range(len(row) - 1):
				if row[j] == row[j + 1]:
					row[j], row[j + 1] = row[j] + row[j + 1], 0
			row = row[row != 0]
			self.field[i] = np.pad(row, (0, 4 - len(row)), constant_values=0)

	def add_num(self, num):
		x, y = random.choice([(i, j) for i, j in product(range(4), range(4)) if not self.field[i][j]])
		self.field[x][y] = num

		for i, j in product(range(4), range(4)):
			widget = getattr(self, f"label_{i}{j}")
			widget.setText(str(self.field[i][j]).strip("0"))
			widget.setStyleSheet(QSS % COLOR[self.field[i][j]])


if __name__ == "__main__":
	app = QApplication(sys.argv)
	qt_core = QtCore()
	qt_core.setFixedSize(qt_core.width(), qt_core.height())
	qt_core.show()
	sys.exit(app.exec())
