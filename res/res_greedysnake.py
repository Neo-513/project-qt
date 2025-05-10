from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication
from itertools import product


def resource_theme1():
	application = QApplication([])
	pixmap = QPixmap(250, 250)
	pixmap.fill(Qt.GlobalColor.transparent)
	with QPainter(pixmap) as painter:
		painter.fillRect(23, 23, 204, 204, Qt.GlobalColor.white)
		painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
		painter.fillRect(25, 25, 200, 200, Qt.GlobalColor.transparent)
	pixmap.save("theme1.png")
	application.quit()


def resource_theme2():
	application = QApplication([])
	pixmap = QPixmap(250, 250)
	pixmap.fill(Qt.GlobalColor.transparent)
	with QPainter(pixmap) as painter:
		painter.setPen(QColor(100, 100, 100))
		for i, j in product(range(10), repeat=2):
			painter.drawRect(j * 20 + 25, i * 20 + 25, 20, 20)
	pixmap.save("theme2.png")
	application.quit()


if __name__ == "__main__":
	# resource_theme1()
	# resource_theme2()
	pass
