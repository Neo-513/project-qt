from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication
from string import ascii_lowercase


def resource_tile():
	application = QApplication([])
	for text in ascii_lowercase:
		__tile(QColor(120, 124, 126), QColor(120, 124, 126), Qt.GlobalColor.white, text, f"0_{text}")
		__tile(QColor(198, 180, 86), QColor(198, 180, 86), Qt.GlobalColor.white, text, f"1_{text}")
		__tile(QColor(112, 169, 97), QColor(112, 169, 97), Qt.GlobalColor.white, text, f"2_{text}")
		__tile(QColor(211, 214, 218), Qt.GlobalColor.white, QColor(181, 184, 188), text, f"hint_{text}")
		__tile(QColor(200, 0, 0), Qt.GlobalColor.white, QColor(200, 0, 0), text, f"hit_{text}")
		__tile(Qt.GlobalColor.black, Qt.GlobalColor.white, Qt.GlobalColor.black, text, f"text_{text}")
	__tile(QColor(211, 214, 218), Qt.GlobalColor.white, Qt.GlobalColor.black, "", f"nontext")
	application.quit()


def __tile(border_color, background_color, color, text, name):
	pixmap = QPixmap(52, 52)
	pixmap.fill(background_color)
	with QPainter(pixmap) as painter:
		painter.setFont(QFont("nyt-franklin", 21, QFont.Weight.Bold))
		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(border_color)
		painter.drawRect(0, 0, 52, 52)
		painter.setBrush(background_color)
		painter.drawRect(2, 2, 48, 48)
		painter.setPen(color)
		painter.drawText(0, 0, 52, 52, Qt.AlignmentFlag.AlignCenter, text.upper())
	pixmap.save(f"{name}.png")


if __name__ == "__main__":
	# resource_tile()
	pass
