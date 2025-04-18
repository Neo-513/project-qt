from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
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


def resource_tile():
	application = QApplication([])
	pixmap = QPixmap(60, 60)
	for i, color in product(range(9), ("black", "gray")):
		pixmap.fill(Qt.GlobalColor.transparent)
		with QPainter(pixmap) as painter:
			painter.setFont(QFont("Arial", 24, QFont.Weight.Black))
			painter.setPen(QColor(color))
			painter.drawText(0, 0, 60, 60, Qt.AlignmentFlag.AlignCenter, str(i + 1))
		pixmap.save(f"{color}{i}.png")
	application.quit()


def resource_selection():
	application = QApplication([])
	pixmap = QPixmap(60, 60)
	pixmap.fill(QColor(200, 0, 0, 50))
	with QPainter(pixmap) as painter:
		painter.fillRect(0, 0, 2, 60, QColor(200, 0, 0))
		painter.fillRect(0, 0, 60, 2, QColor(200, 0, 0))
		painter.fillRect(58, 0, 2, 60, QColor(200, 0, 0))
		painter.fillRect(0, 58, 60, 2, QColor(200, 0, 0))
	pixmap.save(f"selection.png")
	application.quit()


if __name__ == "__main__":
	# resource_background()
	# resource_tile()
	# resource_selection()
	pass
