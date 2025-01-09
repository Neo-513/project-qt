from matrix_ui import Ui_MainWindow
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from itertools import chain
import random
import sys
import util

FONT = QFont("Courier", 11, QFont.Weight.Bold)
CHARSET = tuple(chr(i) for i in chain(range(48, 58), range(65, 91)))


class MyCore(QMainWindow, Ui_MainWindow):
	drops = []

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../matrix/command"))

		self.timer = QTimer()
		self.timer.setInterval(50)
		util.cast(self.timer).timeout.connect(self.timeout)

	def showEvent(self, a0):
		self.label.setPixmap(QPixmap(self.label.size()))
		self.drops = [-random.randint(0, 100) for _ in range(self.label.width() // FONT.pointSize())]
		self.timer.start()

	def timeout(self):
		pixmap = self.label.pixmap()
		with QPainter(pixmap) as painter:
			painter.fillRect(pixmap.rect(), QColor(0, 0, 0, 20))
			painter.setPen(Qt.GlobalColor.green)
			painter.setFont(FONT)
			for i, drop in enumerate(self.drops):
				x, y = i * FONT.pointSize(), drop * FONT.pointSize()
				painter.drawText(x, y, random.choice(CHARSET))
				if y >= self.label.height():
					self.drops[i] = 0
				self.drops[i] += 1
		self.label.setPixmap(pixmap)


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
