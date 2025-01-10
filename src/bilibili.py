from bilibili_ui import Ui_MainWindow
from PyQt6.QtCore import pyqtSignal, QDir, QThread, Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidgetItem
import json
import os
import subprocess
import sys
import util


class MyCore(QMainWindow, Ui_MainWindow):
	my_thread = None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../bilibili/bilibili"))

		util.select_folder(self.lineEdit_old, self.pushButton_old, self.scan_old)
		util.select_folder(self.lineEdit_new, self.pushButton_new, self.scan_new)
		util.button(self.pushButton_export, self.export, "save")
		util.Tree.select(self.treeWidget_old)
		util.Menu.menu(self.treeWidget_old, select=True, folder=True)
		self.radioButton_mp4.clicked.connect(self.refresh)
		self.radioButton_mp3.clicked.connect(self.refresh)

		if os.path.exists("config.json"):
			config = util.FileIO.read("config.json")["bilibili"]
			self.lineEdit_old.setText(config["path_old"]) if os.path.exists(config["path_old"]) else None
			self.lineEdit_new.setText(config["path_new"]) if os.path.exists(config["path_new"]) else None
		self.radioButton_mp4.click()

	def export(self):
		path_old = self.lineEdit_old.text()
		if not os.path.exists(path_old):
			return
		path_new = self.lineEdit_new.text()
		if not os.path.exists(path_new):
			return

		vids, groups = {}, {}
		for i in range(self.treeWidget_old.topLevelItemCount()):
			item = self.treeWidget_old.topLevelItem(i)
			if item.childCount():
				for j in range(item.childCount()):
					if item.child(j).checkState(0) == Qt.CheckState.Checked:
						vids[item.child(j).toolTip(0).split("/")[-1]] = util.BANNED_CHAR.sub("_", item.child(j).text(0))
						groups[item.child(j).toolTip(0).split("/")[-1]] = util.BANNED_CHAR.sub("_", item.text(0))
			else:
				if item.checkState(0) == Qt.CheckState.Checked:
					vids[item.toolTip(0).split("/")[-1]] = util.BANNED_CHAR.sub("_", item.text(0))
					groups[item.toolTip(0).split("/")[-1]] = ""

		files = {}
		for vid, file_name in vids.items():
			jsn_path = util.join_path(path_old, vid, ".playurl")
			if not os.path.exists(jsn_path):
				continue

			jsn = json.loads(util.FileIO.read(jsn_path))
			video = os.path.split((jsn["data"]["dash"]["video"][0]["base_url"]).split("?")[0])[-1]
			audio = os.path.split((jsn["data"]["dash"]["audio"][0]["base_url"]).split("?")[0])[-1]
			file_type = "mp4" if self.radioButton_mp4.isChecked() else "mp3"

			files[vid] = {
				"file_path": util.join_path(path_new, groups[vid], f"{file_name}.{file_type}"),
				"mp4_old": util.join_path(path_old, vid, video),
				"mp4_new": util.join_path(path_new, groups[vid], f"{vid}.mp4"),
				"mp3_old": util.join_path(path_old, vid, audio),
				"mp3_new": util.join_path(path_new, groups[vid], f"{vid}.mp3")
			}

		if not files:
			return util.dialog(f"请选择文件!", "error")
		if not util.dialog(f"确认导出文件{len(files)}个?", "warning"):
			return

		self.my_thread = MyThread(files)
		self.my_thread.start()

	def scan_old(self):
		self.treeWidget_old.clear()

		path_old = self.lineEdit_old.text()
		if not os.path.exists(path_old):
			return

		groups, titles = {}, {}
		for folder_name in QDir(path_old).entryList(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot):
			jsn_path = util.join_path(path_old, folder_name, "videoInfo.json")
			if not os.path.exists(jsn_path):
				continue
			jsn = util.FileIO.read(jsn_path)
			groups.setdefault(jsn["groupTitle"], []).append(folder_name)
			titles[folder_name] = jsn["title"]

		for group, folder_names in groups.items():
			parent = None
			if len(folder_names) != 1:
				parent = QTreeWidgetItem([f"0{group}"])
				parent.setCheckState(0, Qt.CheckState.Unchecked)
				parent.setIcon(0, util.icon("folder"))
				self.treeWidget_old.addTopLevelItem(parent)
			for folder_name in folder_names:
				child = QTreeWidgetItem([titles[folder_name]])
				child.setCheckState(0, Qt.CheckState.Unchecked)
				child.setIcon(0, util.icon("video" if self.radioButton_mp4.isChecked() else "audio"))
				child.setToolTip(0, util.join_path(path_old, folder_name))
				if parent:
					parent.addChild(child)
				else:
					self.treeWidget_old.addTopLevelItem(child)
					child.setText(0, f"1{child.text(0)}")

		self.treeWidget_old.sortItems(0, Qt.SortOrder.AscendingOrder)
		for i in range(self.treeWidget_old.topLevelItemCount()):
			item = self.treeWidget_old.topLevelItem(i)
			item.setText(0, item.text(0)[1:])

	def scan_new(self):
		util.Tree.scan(self.treeWidget_new, self.lineEdit_new.text())

	def refresh(self):
		self.scan_old()
		self.scan_new()
		self.progressBar.setValue(0)

	def dye(self, color):
		palette = self.plainTextEdit.palette()
		palette.setColor(QPalette.ColorRole.Text, color)
		self.plainTextEdit.setPalette(palette)


class MyStatic:
	@staticmethod
	def convert(path_old, path_new):
		if not os.path.exists(path_old):
			return
		if os.path.exists(path_new):
			os.remove(path_new)
		with open(path_old, "rb") as file_old:
			header = file_old.read(32).replace(b"000000000", b"")
			with open(path_new, "wb") as file_new:
				file_new.write(header)
				buffer_size = 256 * 1024 * 1024
				buffer = file_old.read(buffer_size)
				while buffer:
					file_new.write(buffer)
					buffer = file_old.read(buffer_size)

	@staticmethod
	def command(mp4_path, mp3_path, file_path):
		if not os.path.exists(mp4_path):
			return
		if not os.path.exists(mp3_path):
			return
		if os.path.exists(file_path):
			os.remove(file_path)

		tool_path = util.join_path(util.RESOURCE, "bilibili")
		return (
			f'{tool_path[0]}: & cd "{tool_path}" & ffmpeg'
			f' -i "{mp4_path}" -i "{mp3_path}"'
			f' -c:v copy -c:a aac "{file_path}"'
		)


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
		util.cast(self.signal_starts).emit()
		for i, file in enumerate(self.files.values()):
			file_path = file["file_path"]
			mp4_old, mp4_new = file["mp4_old"], file["mp4_new"]
			mp3_old, mp3_new = file["mp3_old"], file["mp3_new"]

			folder_path = os.path.split(file["mp4_new"])[0]
			if not os.path.exists(folder_path):
				os.mkdir(folder_path)

			if file_path.endswith(".mp4"):
				MyStatic.convert(mp4_old, mp4_new)
				MyStatic.convert(mp3_old, mp3_new)

				cmd = MyStatic.command(mp4_new, mp3_new, file_path)
				if cmd:
					with subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as sp:
						util.cast(self.signal_update1).emit("") if i else None
						util.cast(self.signal_update1).emit(f"> {cmd}")
						try:
							for feedback in sp.stdout:
								util.cast(self.signal_update1).emit(feedback.strip()) if feedback.strip() else None
						except:
							util.cast(self.signal_update1).emit("* 未知输出???")
						if sp.wait():
							return util.cast(self.signal_finish).emit(False)
			else:
				MyStatic.convert(mp3_old, file_path)
			os.remove(mp4_new) if os.path.exists(mp4_new) else None
			os.remove(mp3_new) if os.path.exists(mp3_new) else None
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
