from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication
from itertools import product


def resource_background():
	application = QApplication([])
	pixmap = QPixmap(540, 540)
	pixmap.fill(Qt.GlobalColor.transparent)
	with QPainter(pixmap) as painter:
		painter.setPen(QPen(Qt.GlobalColor.gray, 1))
		for pos in product(range(9), repeat=2):
			painter.drawRect(pos[1] * 60, pos[0] * 60, 60, 60)
		painter.setPen(QPen(Qt.GlobalColor.black, 2))
		for pos in product(range(3), repeat=2):
			painter.drawRect(pos[1] * 180, pos[0] * 180, 180, 180)
		painter.drawRect(1, 1, 538, 538)
	pixmap.save("background.png")
	application.quit()


if __name__ == "__main__":
	# resource_background()
	pass
