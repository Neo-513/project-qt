from renamer_ui import Ui_MainWindow
from PyQt6.QtCore import QDir
from PyQt6.QtWidgets import QApplication, QMainWindow
import os
import sys
import util


class MyCore(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../renamer/rename"))

		util.select_folder(self.lineEdit_folder, self.pushButton_folder, self.scan)
		util.button(self.pushButton_rename, self.rename, "edit")
		util.Sync.scroll(self, self.listWidget_old, self.listWidget_new)
		util.Sync.select(self, self.listWidget_old, self.listWidget_new)
		self.lineEdit_old.textChanged.connect(self.replace)
		self.lineEdit_new.textChanged.connect(self.replace)
		self.listWidget_old.itemDoubleClicked.connect(self.copy)

	def rename(self):
		folder_path = self.lineEdit_folder.text()
		if not folder_path:
			return
		if not util.dialog("确认进行批量重命名?", "warning"):
			return

		file_names = {}
		for i in range(self.listWidget_old.count()):
			name_old = self.listWidget_old.item(i).text()
			name_new = self.listWidget_new.item(i).text()
			path_old = util.join_path(folder_path, name_old)
			path_new = util.join_path(folder_path, name_new)

			if os.path.exists(path_new) and name_old != name_new:
				return util.dialog(f"新文件名[{name_new}]本地已存在!", "error")
			if path_new in file_names:
				return util.dialog(f"新文件名[{name_new}]重复!", "error")
			if path_old == path_new:
				continue
			if not os.path.exists(path_old):
				continue
			file_names[path_new] = path_old

		for path_new, path_old in file_names.items():
			os.rename(path_old, path_new)
		util.dialog(f"成功重命名文件{len(file_names)}个!", "success")
		self.scan()
	
	def replace(self):
		text_old = self.lineEdit_old.text()
		text_new = self.lineEdit_new.text()
		for i in range(self.listWidget_old.count()):
			item_old = self.listWidget_old.item(i)
			item_new = self.listWidget_new.item(i)
			item_new.setText(item_old.text().replace(text_old, text_new) if text_old else item_old.text())

	def copy(self, item):
		self.lineEdit_old.setText(item.text())
		self.lineEdit_new.setText(item.text())

	def scan(self):
		self.listWidget_old.clear()
		self.listWidget_new.clear()

		folder_path = self.lineEdit_folder.text()
		if not os.path.exists(folder_path):
			return

		file_names = QDir(folder_path).entryList(QDir.Filter.Files, QDir.SortFlag.Name)
		self.listWidget_old.addItems(file_names)
		self.listWidget_new.addItems(file_names)

		self.replace()
		self.statusbar.showMessage(f"共{self.listWidget_old.count()}个")


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
