from packer_ui import Ui_MainWindow
from PyQt6.QtCore import pyqtSignal, QDir, QThread, Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication, QMainWindow
import os
import subprocess
import sys
import util


class MyCore(QMainWindow, Ui_MainWindow):
	my_thread = None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../packer/logo"))

		util.select_folder(self.lineEdit, self.pushButton_select, self.scan)
		util.button(self.pushButton_pack, self.pack, "save")
		self.radioButton_exe.clicked.connect(self.command)
		self.radioButton_ui.clicked.connect(self.command)
		self.comboBox.currentTextChanged.connect(self.command)

		if os.path.exists("config.json"):
			config = util.FileIO.read("config.json")["packer"]
			self.lineEdit.setText(config["path"]) if os.path.exists(config["path"]) else None
		self.scan()

	def scan(self):
		self.comboBox.clear()
		self.plainTextEdit_cmd.clear()
		self.plainTextEdit_feedback.clear()

		paths = self.paths(self.lineEdit.text())
		for path in paths.values():
			if not os.path.exists(path):
				return

		self.comboBox.addItem("")
		for file_name in QDir(paths["src"]).entryList(["*.py"], QDir.Filter.Files, QDir.SortFlag.Name):
			file = file_name[:-3]
			if os.path.exists(util.join_path(paths["src"], f"{file}_ui.ui")):
				self.comboBox.addItem(util.icon(util.join_path(paths["static"], file, "logo")), file)
		self.comboBox.setMaxVisibleItems(self.comboBox.count())

	def command(self):
		paths = self.paths(self.lineEdit.text())
		for path in paths.values():
			if not os.path.exists(path):
				return

		file = self.comboBox.currentText()
		if not file:
			return self.plainTextEdit_cmd.clear()

		if self.radioButton_exe.isChecked():
			file_path = util.join_path(paths["src"], f"{file}.py")
			if not os.path.exists(file_path):
				return self.plainTextEdit_cmd.clear()

			self.plainTextEdit_cmd.setPlainText(
				f'{paths["src"][:2]} & cd "{paths["src"]}" &'
				f'\npyinstaller -w -F "{file_path}"'
				f'\n--distpath "{paths["build"]}"'
				f'\n--specpath "{paths["build"]}"'
				f'\n--workpath "{paths["build"]}"'
			)
			self.plainTextEdit_cmd.appendPlainText(f'--icon="{util.join_path(paths["static"], file, "logo.png")}"')
			self.plainTextEdit_cmd.appendPlainText(f'--add-data="{util.join_path(paths["static"], file)}":"static/{file}"')
			self.plainTextEdit_cmd.appendPlainText(f'--add-data="{util.join_path(paths["static"], "common")}":"static/common"')
		else:
			self.plainTextEdit_cmd.setPlainText(
				"python"
				f'\n-m PyQt6.uic.pyuic "{util.join_path(paths["src"], f"{file}_ui.ui")}"'
				f'\n-o "{util.join_path(paths["src"], f"{file}_ui.py")}"'
			)

	def pack(self):
		self.command()
		if self.plainTextEdit_cmd.toPlainText():
			self.my_thread = MyThread()
			self.my_thread.start()

	@staticmethod
	def paths(path):
		return {
			"src": util.join_path(path, "src"),
			"build": util.join_path(path, "build"),
			"static": util.join_path(path, "static")
		}

	def dye(self, color):
		palette = self.plainTextEdit_feedback.palette()
		palette.setColor(QPalette.ColorRole.Text, color)
		self.plainTextEdit_feedback.setPalette(palette)


class MyThread(QThread):
	signal_starts = pyqtSignal()
	signal_update = pyqtSignal(str)
	signal_finish = pyqtSignal(bool)

	def __init__(self):
		super().__init__()
		util.cast(self.signal_starts).connect(self.starts)
		util.cast(self.signal_update).connect(self.update)
		util.cast(self.signal_finish).connect(self.finish)

	def run(self):
		cmd = my_core.plainTextEdit_cmd.toPlainText().replace("\n", " ")
		util.cast(self.signal_starts).emit()
		with subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as sp:
			util.cast(self.signal_update).emit(f"> {cmd}")
			for feedback in sp.stdout:
				util.cast(self.signal_update).emit(feedback.strip())
			util.cast(self.signal_finish).emit(not bool(sp.wait()))

	@staticmethod
	def starts():
		my_core.pushButton_pack.setEnabled(False)
		my_core.pushButton_pack.setText("打包中")
		my_core.pushButton_pack.setIcon(util.icon("loading"))

		my_core.plainTextEdit_feedback.clear()
		my_core.dye(Qt.GlobalColor.white)

	@staticmethod
	def update(feedback):
		my_core.plainTextEdit_feedback.appendPlainText(feedback)
		my_core.plainTextEdit_feedback.verticalScrollBar().setValue(my_core.plainTextEdit_feedback.verticalScrollBar().maximum())

	@staticmethod
	def finish(success):
		my_core.pushButton_pack.setEnabled(True)
		my_core.pushButton_pack.setText("打包")
		my_core.pushButton_pack.setIcon(util.icon("save"))

		if success:
			util.dialog("打包成功!", "success")
		else:
			my_core.dye(Qt.GlobalColor.red)
			util.dialog("打包失败!", "error")


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
