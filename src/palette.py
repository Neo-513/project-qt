from palette_ui import Ui_MainWindow
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QMainWindow
import re
import sys
import util

REGEX_RGB = re.compile(f'^{",".join(["(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])"] * 3)}$')
REGEX_HEX = re.compile("^#[0-9A-Fa-f]{6}$")


class MyCore(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../palette/palette"))

		self.lineEdit_rgb.textChanged.connect(self.paint)
		self.lineEdit_hex.textChanged.connect(self.paint)

	def paint(self):
		text_rgb = self.lineEdit_rgb.text()
		text_hex = self.lineEdit_hex.text()

		if self.sender() == self.lineEdit_rgb and not REGEX_RGB.fullmatch(text_rgb):
			return self.dye()
		if self.sender() == self.lineEdit_hex and not REGEX_HEX.fullmatch(text_hex):
			return self.dye()

		self.lineEdit_rgb.textChanged.disconnect(self.paint)
		self.lineEdit_hex.textChanged.disconnect(self.paint)

		if self.sender() == self.lineEdit_rgb:
			r, g, b = text_rgb.split(",")
			self.lineEdit_hex.setText(f"#{hex(int(r))[2:]:02}{hex(int(g))[2:]:02}{hex(int(b))[2:]:02}")
		elif self.sender() == self.lineEdit_hex:
			self.lineEdit_rgb.setText(f"{int(text_hex[1:3], 16)},{int(text_hex[3:5], 16)},{int(text_hex[5:7], 16)}")
		self.dye(self.lineEdit_hex.text())

		self.lineEdit_rgb.textChanged.connect(self.paint)
		self.lineEdit_hex.textChanged.connect(self.paint)

	def dye(self, color=None):
		palette = self.centralwidget.palette()
		palette.setColor(QPalette.ColorRole.Window, QColor(color) if color else QColor(0, 0, 0, 0))
		self.centralwidget.setPalette(palette)


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.setFixedSize(my_core.window().size())
	my_core.show()
	sys.exit(app.exec())
