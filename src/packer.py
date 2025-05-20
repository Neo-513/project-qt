from packer_ui import Ui_MainWindow
from PyQt6.QtCore import QDir, Qt
from PyQt6.QtWidgets import QApplication, QMainWindow
import os
import sys
import util


class MyCore(QMainWindow, Ui_MainWindow):
	COMMAND = {
		"exe": (
			"pyinstaller -w -F src/%.py\n"
			"--distpath build --specpath build --workpath build\n"
			"--icon=../static/%/logo.png\n"
			"--add-data=../static/common;static/common\n"
			"--add-data=../static/%;static/%"
		),
		"ui": "python -m PyQt6.uic.pyuic src/%_ui.ui -o src/%_ui.py"
	}

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../packer/logo"))

		util.select_folder(self.lineEdit, self.pushButton_folder, self.scan)
		util.button(self.pushButton_pack, self.pack, "save")
		util.console(self.plainTextEdit_console, Qt.GlobalColor.white)
		self.radioButton_exe.clicked.connect(self.command)
		self.radioButton_ui.clicked.connect(self.command)
		self.comboBox.currentTextChanged.connect(self.command)

		self.process = util.process(self.process_log, self.process_finished)
		if os.path.exists("config.json"):
			config = util.read("config.json")["packer"]
			self.lineEdit.setText(config["path"]) if os.path.exists(config["path"]) else None
		self.scan()

	def scan(self):
		self.comboBox.clear()
		self.plainTextEdit_command.clear()
		self.plainTextEdit_console.clear()

		path_src = f"{self.lineEdit.text()}/src"
		if not os.path.exists(path_src):
			return

		self.comboBox.addItem("")
		for file_name in QDir(path_src).entryList(["*.py"], QDir.Filter.Files, QDir.SortFlag.Name):
			file = file_name[:-3]
			if os.path.exists(f"{path_src}/{file}_ui.ui"):
				self.comboBox.addItem(util.icon(f"{self.lineEdit.text()}/static/{file}/logo"), file)
		self.comboBox.setMaxVisibleItems(self.comboBox.count())

	def pack(self):
		self.command()
		if not self.plainTextEdit_command.toPlainText():
			return

		util.enable(self.pushButton_pack, "loading", "打包中")
		util.console(self.plainTextEdit_console, Qt.GlobalColor.white)
		self.plainTextEdit_console.clear()

		cmds = self.plainTextEdit_command.toPlainText().replace("\n", " ").split(" ")
		self.process.setWorkingDirectory(self.lineEdit.text())
		self.process.start("cmd.exe", ["/c"] + cmds)

	def command(self):
		file = self.comboBox.currentText()
		if not file:
			return self.plainTextEdit_command.clear()

		path = self.lineEdit.text()
		if not os.path.exists(path):
			return

		command = self.COMMAND["exe" if self.radioButton_exe.isChecked() else "ui"]
		self.plainTextEdit_command.setPlainText(command.replace("%", file))

	def process_log(self):
		log = self.process.readAllStandardError().data().decode("gbk")
		self.plainTextEdit_console.appendPlainText(log.strip())
		self.plainTextEdit_console.verticalScrollBar().setValue(self.plainTextEdit_console.verticalScrollBar().maximum())

	def process_finished(self, exit_code):
		util.enable(self.pushButton_pack, "save", "打包")
		if exit_code == 0:
			util.dialog("打包完成!", "success")
		else:
			util.console(self.plainTextEdit_console, Qt.GlobalColor.red)


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
