from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication
from itertools import product


def resource_background():
	application = QApplication([])
	pixmap = QPixmap(600, 600)
	pixmap.fill(QColor(255, 221, 80))
	with QPainter(pixmap) as painter:
		for i, j in product(range(14), repeat=2):
			painter.drawRect(i * 40 + 20, j * 40 + 20, 40, 40)
		painter.setBrush(Qt.GlobalColor.black)
		painter.drawEllipse(296, 296, 8, 8)
	pixmap.save("background.png")
	application.quit()


if __name__ == "__main__":
	# resource_background()
	pass
