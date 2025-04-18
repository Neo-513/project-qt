from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication
from itertools import product


def resource_background():
	application = QApplication([])
	pixmap = QPixmap(475, 475)
	pixmap.fill(QColor(187, 173, 160))
	with QPainter(pixmap) as painter:
		for i, j in product(range(4), repeat=2):
			painter.fillRect(j * 115 + 15, i * 115 + 15, 100, 100, QColor(205, 193, 180))
	pixmap.save("background.png")
	application.quit()


def resource_tile():
	colors = (
		QColor(205, 193, 180), QColor(238, 228, 218), QColor(237, 224, 200), QColor(242, 177, 121),
		QColor(245, 149, 99), QColor(246, 124, 95), QColor(246, 94, 59), QColor(237, 207, 114),
		QColor(237, 204, 97), QColor(228, 192, 42), QColor(226, 186, 19), QColor(236, 196, 0)
	)
	application = QApplication([])
	pixmap = QPixmap(100, 100)
	for i in range(12):
		pixmap.fill(colors[i])
		with QPainter(pixmap) as painter:
			painter.setFont(QFont("", 40, QFont.Weight.Bold))
			painter.setPen(QColor(118, 110, 101))
			painter.fillRect(0, 0, 100, 100, colors[i])
			painter.drawText(0, 0, 100, 100, Qt.AlignmentFlag.AlignCenter, str(1 << i).rstrip("1"))
		pixmap.save(f"tile{i}.png")
	application.quit()


if __name__ == "__main__":
	# resource_background()
	# resource_tile()
	pass
