from toggle_case_ui import Ui_MainWindow
from PyQt6.QtWidgets import QApplication, QMainWindow
import sys
import util


class MyCore(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../toggle_case/toggle_case"))

	def wheelEvent(self, a0):
		if a0.angleDelta().y() > 0:
			self.plainTextEdit.setPlainText(self.plainTextEdit.toPlainText().upper())
		elif a0.angleDelta().y() < 0:
			self.plainTextEdit.setPlainText(self.plainTextEdit.toPlainText().lower())

		cursor = self.plainTextEdit.textCursor()
		cursor.movePosition(cursor.MoveOperation.End)
		self.plainTextEdit.setTextCursor(cursor)


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
