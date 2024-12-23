from packer_ui import Ui_MainWindow
from PyQt6.QtCore import pyqtSignal, QDir, QThread, Qt
from PyQt6.QtGui import QIcon, QPalette
from PyQt6.QtWidgets import QApplication, QMainWindow
import os
import subprocess
import sys
import util


class QtCore(QMainWindow, Ui_MainWindow):
	THREAD = None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../packer/packer"))

		util.select_folder(self.lineEdit_old, self.pushButton_old, self.scan)
		util.select_folder(self.lineEdit_new, self.pushButton_new, self.command, clean=True)
		util.select_folder(self.lineEdit_res, self.pushButton_res, self.command)
		util.button(self.pushButton_pack, self.pack, "save")
		self.radioButton_exe.clicked.connect(self.command)
		self.radioButton_ui.clicked.connect(self.command)
		self.comboBox.currentTextChanged.connect(self.command)

		if os.path.exists("config.json"):
			config = util.FileIO.read("config.json")["packer"]
			self.lineEdit_old.setText(config["path_old"]) if os.path.exists(config["path_old"]) else None
			self.lineEdit_new.setText(config["path_new"]) if os.path.exists(config["path_new"]) else None
			self.lineEdit_res.setText(config["path_res"]) if os.path.exists(config["path_res"]) else None
			self.logos = config["logo"]
		self.scan()

	def command(self):
		path_old = self.lineEdit_old.text()
		path_new = self.lineEdit_new.text()
		path_res = self.lineEdit_res.text()
		if not os.path.exists(path_old):
			return self.plainTextEdit_cmd.clear()
		if not os.path.exists(path_new):
			return self.plainTextEdit_cmd.clear()
		if not os.path.exists(path_res):
			return self.plainTextEdit_cmd.clear()

		file_name = self.comboBox.currentText()
		file_path = util.join_path(path_old, f"{file_name}.py")
		if not file_name:
			return self.plainTextEdit_cmd.clear()
		if not os.path.exists(file_path):
			return self.plainTextEdit_cmd.clear()

		if self.radioButton_exe.isChecked():
			path_icon = util.join_path(path_res, self.logos.get(file_path, "*"))
			path_global = util.join_path(path_res, "global")
			path_extra = util.join_path(path_res, file_name)
			self.plainTextEdit_cmd.setPlainText(
				f'{path_old[0]}: & cd "{path_old}" &'
				f'\npyinstaller -w -F "{file_path}"'
				f'\n--distpath "{path_new}"'
				f'\n--specpath "{path_new}"'
				f'\n--workpath "{path_new}"'
			)
			if os.path.exists(path_icon):
				self.plainTextEdit_cmd.appendPlainText(f'--icon="{path_icon}"')
			if os.path.exists(path_global):
				self.plainTextEdit_cmd.appendPlainText(f'--add-data="{path_global}":"assets/global"')
			if os.path.exists(path_extra):
				self.plainTextEdit_cmd.appendPlainText(f'--add-data="{path_extra}":"assets/{file_name}"')
		elif self.radioButton_ui.isChecked():
			path_ui = util.join_path(path_old, f"{file_name}_ui.ui")
			path_py = util.join_path(path_old, f"{file_name}_ui.py")
			self.plainTextEdit_cmd.setPlainText(
				"python"
				f'\n-m PyQt6.uic.pyuic "{path_ui}"'
				f'\n-o "{path_py}"'
			)

	def scan(self):
		self.comboBox.clear()

		folder_path = self.lineEdit_old.text()
		if not os.path.exists(folder_path):
			return

		self.comboBox.addItem("")
		for file_name in QDir(folder_path).entryList(["*.py"], QDir.Filter.Files, QDir.SortFlag.Name):
			if file_name != "util.py" and not file_name.endswith("_ui.py"):
				file_path = util.join_path(folder_path, file_name)
				icon_path = self.logos.get(file_path, "")
				self.comboBox.addItem(QIcon(icon_path), file_name[:-3])

	def pack(self):
		if self.plainTextEdit_cmd.toPlainText():
			self.THREAD = QtThread()
			self.THREAD.start()

	def dye(self, color):
		palette = self.plainTextEdit_feedback.palette()
		palette.setColor(QPalette.ColorRole.Text, color)
		self.plainTextEdit_feedback.setPalette(palette)


class QtThread(QThread):
	signal_starts = pyqtSignal()
	signal_update = pyqtSignal(str)
	signal_finish = pyqtSignal(bool)

	def __init__(self):
		super().__init__()
		util.cast(self.signal_starts).connect(self.starts)
		util.cast(self.signal_update).connect(self.update)
		util.cast(self.signal_finish).connect(self.finish)

	def run(self):
		qt_core.command()
		cmd = qt_core.plainTextEdit_cmd.toPlainText().replace("\n", " ")

		util.cast(self.signal_starts).emit()
		with subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as sp:
			util.cast(self.signal_update).emit(f"> {cmd}")
			for feedback in sp.stdout:
				util.cast(self.signal_update).emit(feedback.strip())
			util.cast(self.signal_finish).emit(not bool(sp.wait()))

	@staticmethod
	def starts():
		qt_core.pushButton_pack.setEnabled(False)
		qt_core.pushButton_pack.setText("打包中")
		qt_core.pushButton_pack.setIcon(util.icon("loading"))

		qt_core.plainTextEdit_feedback.clear()
		qt_core.dye(Qt.GlobalColor.white)

	@staticmethod
	def update(feedback):
		qt_core.plainTextEdit_feedback.appendPlainText(feedback)
		qt_core.plainTextEdit_feedback.verticalScrollBar().setValue(qt_core.plainTextEdit_feedback.verticalScrollBar().maximum())

	@staticmethod
	def finish(success):
		qt_core.pushButton_pack.setEnabled(True)
		qt_core.pushButton_pack.setText("打包")
		qt_core.pushButton_pack.setIcon(util.icon("save"))

		if success:
			util.dialog("打包成功!", "success")
		else:
			qt_core.dye(Qt.GlobalColor.red)
			util.dialog("打包失败!", "error")


if __name__ == "__main__":
	app = QApplication(sys.argv)
	qt_core = QtCore()
	qt_core.show()
	sys.exit(app.exec())
