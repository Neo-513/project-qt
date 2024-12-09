from bilibili_ui import Ui_MainWindow
from PyQt6.QtCore import QDir, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeWidgetItem
import json
import os
import subprocess
import sys
import util


class QtCore(QMainWindow, Ui_MainWindow):
	THREAD = None

	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../bilibili/bilibili"))

		util.select_folder(self.lineEdit_old, self.pushButton_old, self.scan_old)
		util.select_folder(self.lineEdit_new, self.pushButton_new, self.scan_new)
		util.button(self.pushButton_export, self.export, "save")
		util.Tree.sync_check(self.treeWidget_old)
		util.Menu.menu(self, self.treeWidget_old, QtMenu.menu)
		self.radioButton_mp4.clicked.connect(self.refresh)
		self.radioButton_mp3.clicked.connect(self.refresh)

		if os.path.exists("config.json"):
			config = util.FileIO.read("config.json")["bilibili"]
			self.lineEdit_old.setText(config["path_old"]) if os.path.exists(config["path_old"]) else None
			self.lineEdit_new.setText(config["path_new"]) if os.path.exists(config["path_new"]) else None
		self.refresh()

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
			if item.data(0, Qt.ItemDataRole.UserRole):
				for j in range(item.childCount()):
					if item.child(j).checkState(0) == Qt.CheckState.Checked:
						vids[item.child(j).toolTip(0).split("/")[-1]] = util.BANNED_CHAR.sub("_", item.child(j).text(0))
						groups[item.child(j).toolTip(0).split("/")[-1]] = util.BANNED_CHAR.sub("_", item.text(0))
			else:
				if item.checkState(0) == Qt.CheckState.Checked:
					vids[item.toolTip(0).split("/")[-1]] = util.BANNED_CHAR.sub("_", item.text(0))
					groups[item.toolTip(0).split("/")[-1]] = ""

		file_type = "mp4" if self.radioButton_mp4.isChecked() else "mp3"
		file_sort = "视频" if self.radioButton_mp4.isChecked() else "音频"

		files = {}
		for vid, file_name in vids.items():
			jsn_path = os.path.join(path_old, vid, ".playurl").replace("\\", "/")
			if not os.path.exists(jsn_path):
				continue

			jsn = json.loads(util.FileIO.read(jsn_path))
			video = os.path.split((jsn["data"]["dash"]["video"][0]["base_url"]).split("?")[0])[-1]
			audio = os.path.split((jsn["data"]["dash"]["audio"][0]["base_url"]).split("?")[0])[-1]

			files[vid] = {
				"file_path": os.path.join(path_new, groups[vid], f"{file_name}.{file_type}").replace("\\", "/"),
				"mp4_old": os.path.join(path_old, vid, video).replace("\\", "/"),
				"mp4_new": os.path.join(path_new, groups[vid], f"{vid}.mp4").replace("\\", "/"),
				"mp3_old": os.path.join(path_old, vid, audio).replace("\\", "/"),
				"mp3_new": os.path.join(path_new, groups[vid], f"{vid}.mp3").replace("\\", "/")
			}

		if not files:
			return util.dialog(f"请选择{file_sort}文件!", "error")
		if not util.dialog(f"确认导出{file_sort}文件{len(files)}个?", "warning"):
			return

		self.THREAD = QtThread()
		self.THREAD.files = files
		self.THREAD.start()

	def scan_old(self):
		self.treeWidget_old.clear()

		path_old = self.lineEdit_old.text()
		if not os.path.exists(path_old):
			return

		groups, titles = {}, {}
		for folder_name in QDir(path_old).entryList(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot):
			jsn_path = os.path.join(path_old, folder_name, "videoInfo.json").replace("\\", "/")
			if not os.path.exists(jsn_path):
				continue

			jsn = util.FileIO.read(jsn_path)
			groups.setdefault(jsn["groupTitle"], []).append(folder_name)
			titles[folder_name] = jsn["title"]

		for group, folder_names in groups.items():
			parent = None
			if len(folder_names) != 1:
				parent = QTreeWidgetItem([group])
				parent.setCheckState(0, Qt.CheckState.Unchecked)
				parent.setIcon(0, util.icon("folder"))
				parent.setData(0, Qt.ItemDataRole.UserRole, True)
				self.treeWidget_old.addTopLevelItem(parent)

			for folder_name in folder_names:
				child = QTreeWidgetItem([titles[folder_name]])
				child.setCheckState(0, Qt.CheckState.Unchecked)
				child.setIcon(0, util.icon("video" if self.radioButton_mp4.isChecked() else "audio"))
				child.setData(0, Qt.ItemDataRole.UserRole, False)
				child.setToolTip(0, os.path.join(path_old, folder_name).replace("\\", "/"))
				if len(folder_names) != 1:
					parent.addChild(child)
				else:
					self.treeWidget_old.addTopLevelItem(child)
			if len(folder_names) != 1:
				parent.sortChildren(0, Qt.SortOrder.AscendingOrder)

		for i in range(self.treeWidget_old.topLevelItemCount()):
			item = self.treeWidget_old.topLevelItem(i)
			item.setText(0, f"{int(not item.data(0, Qt.ItemDataRole.UserRole))}{item.text(0)}")
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


class QtStatic:
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
	def merge(mp4_path, mp3_path, file_path):
		if not os.path.exists(mp4_path):
			return
		if not os.path.exists(mp3_path):
			return
		if os.path.exists(file_path):
			os.remove(file_path)

		ffmpeg_path = os.path.join(util.RESOURCE, "bilibili")
		subprocess.run((
			f'{ffmpeg_path[0]}: & cd "{ffmpeg_path}" & ffmpeg'
			f' -i "{mp4_path}" -i "{mp3_path}"'
			f' -c:v copy -c:a aac "{file_path}"'
		), shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

		os.remove(mp4_path) if os.path.exists(mp4_path) else None
		os.remove(mp3_path) if os.path.exists(mp3_path) else None


class QtThread(QThread):
	signal_starts = pyqtSignal()
	signal_update = pyqtSignal(int)
	signal_finish = pyqtSignal()
	files = None

	def __init__(self):
		super().__init__()
		util.cast(self.signal_starts).connect(self.starts)
		util.cast(self.signal_update).connect(self.update)
		util.cast(self.signal_finish).connect(self.finish)

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
				QtStatic.convert(mp4_old, mp4_new)
				QtStatic.convert(mp3_old, mp3_new)
				QtStatic.merge(mp4_new, mp3_new, file_path)
			else:
				QtStatic.convert(mp3_old, file_path)
			util.cast(self.signal_update).emit(i)
		util.cast(self.signal_finish).emit()

	@staticmethod
	def starts():
		qt_core.pushButton_export.setEnabled(False)
		qt_core.pushButton_export.setText("导出中")
		qt_core.pushButton_export.setIcon(util.icon("loading"))

	def update(self, i):
		qt_core.progressBar.setValue(int((i + 1) / len(self.files) * 100))
		qt_core.scan_new()

	def finish(self):
		qt_core.pushButton_export.setEnabled(True)
		qt_core.pushButton_export.setText("导出")
		qt_core.pushButton_export.setIcon(util.icon("save"))

		file_sort = "视频" if qt_core.radioButton_mp4.isChecked() else "音频"
		util.dialog(f"成功导出{file_sort}文件{len(self.files)}个!", "success")
		qt_core.refresh()


class QtMenu:
	@staticmethod
	def menu(widget, point, qu_menu):
		util.Menu.add_menu(widget, point, qu_menu, "全选", "select_all", (
			lambda: util.Menu.select_all(widget)), rely=False)
		util.Menu.add_menu(widget, point, qu_menu, "取消全选", "unselect_all", (
			lambda: util.Menu.unselect_all(widget)), rely=False)

		item = qt_core.treeWidget_old.itemAt(point)
		if item and not item.data(0, Qt.ItemDataRole.UserRole):
			util.Menu.add_menu(widget, point, qu_menu, "打开文件夹", "folder", (
				lambda: util.Menu.open_folder(widget)))


if __name__ == "__main__":
	app = QApplication(sys.argv)
	qt_core = QtCore()
	qt_core.show()
	sys.exit(app.exec())
