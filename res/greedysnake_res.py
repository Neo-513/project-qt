from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication
from itertools import product


def resource_theme1():
	application = QApplication([])
	pixmap = QPixmap(600, 600)
	pixmap.fill(Qt.GlobalColor.transparent)
	with QPainter(pixmap) as painter:
		painter.fillRect(47, 47, 506, 506, Qt.GlobalColor.white)
		painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
		painter.fillRect(50, 50, 500, 500, Qt.GlobalColor.transparent)
	pixmap.save("theme1.png")
	application.quit()


def resource_theme2():
	application = QApplication([])
	pixmap = QPixmap(600, 600)
	pixmap.fill(Qt.GlobalColor.transparent)
	with QPainter(pixmap) as painter:
		painter.setPen(QColor(100, 100, 100))
		for i, j in product(range(20), repeat=2):
			painter.drawRect(j * 25 + 50, i * 25 + 50, 25, 25)
	pixmap.save("theme2.png")
	application.quit()


def resource_scoreboard():
	application = QApplication([])
	pixmap = QPixmap(600, 600)
	pixmap.fill(Qt.GlobalColor.transparent)
	with QPainter(pixmap) as painter:
		painter.setFont(QFont("", 16))
		painter.setPen(Qt.GlobalColor.white)
		painter.drawText(60, 60, 100, 50, Qt.AlignmentFlag.AlignLeft, "Score 0")
	pixmap.save("scoreboard.png")
	application.quit()


if __name__ == "__main__":
	# resource_theme1()
	# resource_theme2()
	# resource_scoreboard()
	pass
