from wallpaper_engine_ui import Ui_MainWindow
from PyQt6.QtCore import pyqtSignal, QDir, QThread, Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication, QListWidgetItem, QMainWindow
import os
import shutil
import subprocess
import sys
import util


class MyCore(QMainWindow, Ui_MainWindow):
	my_thread = None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../wallpaper_engine/wallpaper_engine"))

		util.select_folder(self.lineEdit_old, self.pushButton_old, self.scan_old)
		util.select_folder(self.lineEdit_new, self.pushButton_new, self.scan_new)
		util.button(self.pushButton_export, self.export, "save")
		util.Menu.menu(self.listWidget, select=True, folder=True)
		self.radioButton_video.clicked.connect(self.refresh)
		self.radioButton_scene.clicked.connect(self.refresh)

		if os.path.exists("config.json"):
			config = util.FileIO.read("config.json")["wallpaper_engine"]
			self.lineEdit_old.setText(config["path_old"]) if os.path.exists(config["path_old"]) else None
			self.lineEdit_new.setText(config["path_new"]) if os.path.exists(config["path_new"]) else None
		shutil.rmtree("wallpaper_engine_cache") if os.path.exists("wallpaper_engine_cache") else None
		os.mkdir("wallpaper_engine_cache")
		self.radioButton_video.click()

	def export(self):
		folder_old = self.lineEdit_old.text()
		if not os.path.exists(folder_old):
			return
		folder_new = self.lineEdit_new.text()
		if not os.path.exists(folder_new):
			return

		files = {}
		for i in range(self.listWidget.count()):
			item = self.listWidget.item(i)
			if item.checkState() != Qt.CheckState.Checked:
				continue
			file_old = item.toolTip()
			if not os.path.exists(file_old):
				continue
			file_new = util.join_path(folder_new, item.text())
			if file_new in files.values():
				return util.dialog(f"导出存在同名文件[{item.text()}]!", "error")
			files[file_old] = file_new

		if not files:
			return util.dialog("请选择文件!", "error")
		if not util.dialog(f"确认导出文件{len(files)}个?", "warning"):
			return

		if self.radioButton_video.isChecked():
			for path_old, path_new in files.items():
				path_new = f"{path_new}.mp4"
				os.rename(path_old, path_new) if not os.path.exists(path_new) else None
			self.progressBar.setValue(100)
			util.dialog(f"成功导出文件{len(files)}个!", "success")
			self.refresh()
		else:
			self.my_thread = MyThread([(path_old, path_new) for path_old, path_new in files.items()])
			self.my_thread.start()

	def scan_old(self):
		self.listWidget.clear()

		path_old = self.lineEdit_old.text()
		if not os.path.exists(path_old):
			return

		if self.radioButton_video.isChecked():
			self.listWidget.setProperty("type", "video")
		else:
			self.listWidget.setProperty("type", "scene")

		for folder in QDir(path_old).entryList(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot):
			path_jsn = util.join_path(path_old, folder, "project.json")
			if not os.path.exists(path_jsn):
				continue

			jsn = util.FileIO.read(path_jsn)
			if jsn.get("type", "").lower() != self.listWidget.property("type"):
				continue

			file = jsn["file"] if self.radioButton_video.isChecked() else "scene.pkg"
			file_path = util.join_path(path_old, folder, file)
			if not os.path.exists(file_path):
				continue

			item = QListWidgetItem(util.BANNED_CHAR.sub("_", jsn["title"]))
			item.setCheckState(Qt.CheckState.Unchecked)
			item.setIcon(util.icon("video" if self.radioButton_video.isChecked() else "image"))
			item.setToolTip(file_path)
			self.listWidget.addItem(item)

		self.listWidget.sortItems()
		self.statusbar.showMessage(f"共{self.listWidget.count()}个")

	def scan_new(self):
		util.Tree.scan(self.treeWidget, self.lineEdit_new.text())

	def refresh(self):
		self.scan_old()
		self.scan_new()
		self.progressBar.setValue(0)

	def dye(self, color):
		palette = self.plainTextEdit.palette()
		palette.setColor(QPalette.ColorRole.Text, color)
		self.plainTextEdit.setPalette(palette)


class MyThread(QThread):
	signal_starts = pyqtSignal()
	signal_update1 = pyqtSignal(str)
	signal_update2 = pyqtSignal(int)
	signal_finish = pyqtSignal(bool)

	def __init__(self, files):
		super().__init__()
		util.cast(self.signal_starts).connect(self.starts)
		util.cast(self.signal_update1).connect(self.update1)
		util.cast(self.signal_update2).connect(self.update2)
		util.cast(self.signal_finish).connect(self.finish)
		self.files = files

	def run(self):
		path_tool = util.join_path(util.RESOURCE, "wallpaper_engine", "repkg")
		path_cache = util.join_path(os.getcwd(), "wallpaper_engine_cache")
		path_material = util.join_path("wallpaper_engine_cache", "materials")
		path_folder = my_core.lineEdit_new.text()

		util.cast(self.signal_starts).emit()
		for i, file in enumerate(self.files):
			path_old, path_new = file
			cmd = f'{path_tool[0]}: & cd "{path_tool}" & RePKG.exe extract "{path_old}" -o "{path_cache}"'
			shutil.rmtree("wallpaper_engine_cache") if os.path.exists("wallpaper_engine_cache") else None

			with subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as sp:
				util.cast(self.signal_update1).emit("") if i else None
				util.cast(self.signal_update1).emit(f"> {cmd}")
				for feedback in sp.stdout:
					util.cast(self.signal_update1).emit(feedback.strip()) if feedback.strip() else None
				if sp.wait():
					return util.cast(self.signal_finish).emit(False)

			old_names = QDir(path_material).entryList(["*.png", "*.jpg", "*.jpeg", "*.gif"], QDir.Filter.Files)
			new_names, file_paths = [], {}
			for j, old_name in enumerate(old_names):
				file_no = "" if len(old_names) == 1 else f"【{j + 1:02}】"
				_, file_type = os.path.splitext(old_name)

				new_name = f"{path_new}{file_no}{file_type}"
				new_names.append(os.path.basename(new_name))

				file_old = util.join_path(path_material, old_name)
				file_new = util.join_path(path_folder, new_name)
				file_paths[file_old] = file_new

			if set(new_names) & set(os.listdir(path_folder)):
				util.cast(self.signal_update1).emit("* 同名文件已存在")
				return util.cast(self.signal_finish).emit(False)

			for file_old, file_new in file_paths.items():
				os.rename(file_old, file_new)
			util.cast(self.signal_update2).emit(i)
		util.cast(self.signal_finish).emit(True)

	@staticmethod
	def starts():
		my_core.pushButton_export.setEnabled(False)
		my_core.pushButton_export.setText("导出中")
		my_core.pushButton_export.setIcon(util.icon("loading"))

		my_core.plainTextEdit.clear()
		my_core.dye(Qt.GlobalColor.white)

	@staticmethod
	def update1(feedback):
		my_core.plainTextEdit.appendPlainText(feedback)
		my_core.plainTextEdit.verticalScrollBar().setValue(my_core.plainTextEdit.verticalScrollBar().maximum())

	def update2(self, value):
		my_core.progressBar.setValue(100 * (value + 1) // len(self.files))
		my_core.scan_new()

	def finish(self, success):
		my_core.pushButton_export.setEnabled(True)
		my_core.pushButton_export.setText("导出")
		my_core.pushButton_export.setIcon(util.icon("save"))

		if success:
			util.dialog(f"成功导出文件{len(self.files)}个!", "success")
		else:
			my_core.dye(Qt.GlobalColor.red)
			util.dialog("导出失败!", "error")
		my_core.refresh()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
