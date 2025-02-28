from matrix_ui import Ui_MainWindow
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow
from string import ascii_letters
import random
import sys
import util


class MyCore(QMainWindow, Ui_MainWindow):
	FONT = QFont("Courier", 11, QFont.Weight.Bold)
	drops = None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../matrix/logo"))

		self.timer = QTimer()
		self.timer.setInterval(50)
		util.cast(self.timer).timeout.connect(self.display)

	def showEvent(self, a0):
		self.label.setPixmap(QPixmap(self.label.size()))
		self.drops = [-random.randint(0, 100) for _ in range(self.label.width() // self.FONT.pointSize())]
		self.timer.start()

	def display(self):
		pixmap = self.label.pixmap()
		with QPainter(pixmap) as painter:
			painter.fillRect(pixmap.rect(), QColor(0, 0, 0, 20))
			painter.setPen(Qt.GlobalColor.green)
			painter.setFont(self.FONT)
			for i, drop in enumerate(self.drops):
				x, y = i * self.FONT.pointSize(), drop * self.FONT.pointSize()
				painter.drawText(x, y, random.choice(ascii_letters + "0123456789"))
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
