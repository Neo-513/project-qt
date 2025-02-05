from game2048_ui import Ui_MainWindow
from PyQt6.QtCore import QRect, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import product
import numpy as np
import random
import sys
import util

FRAME_COUNT = 10
FONT = QFont(QFont().family(), 40, QFont.Weight.Bold)

GROOVE_SIZE, GAP_SIZE = 100, 15
PIECE_SIZE = GROOVE_SIZE + GAP_SIZE
GROOVE = {(i, j): (j * PIECE_SIZE + GAP_SIZE, i * PIECE_SIZE + GAP_SIZE) for i, j in product(range(4), repeat=2)}
CANVAS_SIZE = PIECE_SIZE * 4 + GAP_SIZE
WINDOW_SIZE = CANVAS_SIZE + 18, CANVAS_SIZE + 20

COLOR_SKELETON = QColor(187, 173, 160)
COLOR_NUM = QColor(118, 110, 101)
COLOR = {
	0: QColor(205, 193, 180), 2: QColor(238, 228, 218), 4: QColor(237, 224, 200), 8: QColor(242, 177, 121),
	16: QColor(245, 149, 99), 32: QColor(246, 124, 95), 64: QColor(246, 94, 59), 128: QColor(237, 207, 114),
	256: QColor(237, 204, 97), 512: QColor(228, 192, 42), 1024: QColor(226, 186, 19), 2048: QColor(236, 196, 0)
}

ROTATE = {Qt.Key.Key_Left: 0, Qt.Key.Key_Right: 2, Qt.Key.Key_Up: 1, Qt.Key.Key_Down: -1}
TRANS = {
	Qt.Key.Key_Left: lambda x, y: (x, y), Qt.Key.Key_Right: lambda x, y: (3 - x, 3 - y),
	Qt.Key.Key_Up: lambda x, y: (y, 3 - x), Qt.Key.Key_Down: lambda x, y: (3 - y, x)
}


class MyCore(QMainWindow, Ui_MainWindow):
	field = np.zeros((4, 4), dtype=int)
	skeleton, trails = None, None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../game2048/2048"))

		self.timer = QTimer()
		self.timer.setInterval(15)
		util.cast(self.timer).timeout.connect(self.draw)

		self.skeleton = QPixmap(CANVAS_SIZE, CANVAS_SIZE)
		self.skeleton.fill(COLOR_SKELETON)
		with QPainter(self.skeleton) as painter:
			painter.setPen(Qt.PenStyle.NoPen)
			painter.setBrush(COLOR[0])
			for pos in GROOVE.values():
				painter.drawRect(QRect(*pos, GROOVE_SIZE, GROOVE_SIZE))
		self.label.setPixmap(self.skeleton)
		self.statusbar.showMessage("按 Enter 重新开始")
		self.restart()

	def restart(self):
		self.field.fill(0)
		self.add(2)
		self.add(2)
		self.display()

	def keyPressEvent(self, a0):
		if self.timer.isActive():
			return
		if a0.key() == Qt.Key.Key_Return:
			return self.restart()
		if a0.key() not in ROTATE:
			return

		previous = self.field.copy()
		rotate = ROTATE[util.cast(a0.key())]
		trans = TRANS[util.cast(a0.key())]

		self.field = np.rot90(self.field, rotate)
		self.merge(trans)
		self.field = np.rot90(self.field, -rotate)

		self.timer.setProperty("frame", 0)
		self.timer.start()

		if 2048 in self.field:
			util.dialog("You won", "success")
			return self.restart()

		if self.field.tolist() != previous.tolist():
			self.add(random.choice((2, 4)))

		if 0 not in self.field and not any(0 in np.diff(f) for f in np.concatenate((self.field, self.field.T))):
			util.dialog("You lose", "error")
			return self.restart()

	def add(self, num):
		self.field[tuple(random.choice(np.argwhere(self.field == 0)))] = num

	def merge(self, trans):
		following, merged, self.trails = [[] for _ in range(4)], [False] * 4, []
		for i, j in product(range(4), repeat=2):
			num = self.field[i][j]
			if not num:
				continue
			if following[i] and following[i][-1] == num and not merged[i]:
				following[i][-1] *= 2
				merged[i] = True
			else:
				following[i].append(num)
				merged[i] = False
			self.trails.insert(0, [trans(i, j), trans(i, len(following[i]) - 1), num])
		self.field = np.array([f + [0] * (4 - len(f)) for f in following])

	def display(self):
		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(FONT)
			for f, pos in GROOVE.items():
				self.dye(painter, self.field[f], pos)
		self.label.setPixmap(pixmap)

	def draw(self):
		self.timer.setProperty("frame", self.timer.property("frame") + 1)
		if self.timer.property("frame") > FRAME_COUNT:
			self.timer.stop()
			return self.display()

		offset = self.timer.property("frame") / FRAME_COUNT
		pixmap = self.skeleton.copy()
		with QPainter(pixmap) as painter:
			painter.setFont(FONT)
			for start, end, num in self.trails:
				(sx, sy), (ex, ey) = GROOVE[start], GROOVE[end]
				pos = int(sx + (ex - sx) * offset), int(sy + (ey - sy) * offset)
				self.dye(painter, num, pos)
		self.label.setPixmap(pixmap)

	@staticmethod
	def dye(painter, num, pos):
		rect = QRect(*pos, GROOVE_SIZE, GROOVE_SIZE)
		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(COLOR[num])
		painter.drawRect(rect)
		painter.setPen(COLOR_NUM)
		painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(num).strip("0"))


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(*WINDOW_SIZE)
	my_core.show()
	sys.exit(app.exec())
