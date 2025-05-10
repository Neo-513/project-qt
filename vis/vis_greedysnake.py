from vis_greedysnake_ui import Ui_MainWindow
from PyQt6.QtCore import pyqtSignal, QThread
from PyQt6.QtWidgets import QApplication, QMainWindow
from pyqtgraph import BarGraphItem
from src import util
from train.train_greedysnake import *
import pyqtgraph
import sys


class MyCore(QMainWindow, Ui_MainWindow):
	def __init__(self):
		super().__init__()
		self.setupUi(self)
		self.setWindowIcon(util.icon("../greedysnake/logo"))

		self.plot_widget1 = pyqtgraph.PlotWidget(title="Loss Value")
		self.plot_widget1.setMouseEnabled(x=False, y=False)
		self.plot_widget1.getPlotItem().hideButtons()
		self.plot_widget1.setXRange(0, HYPERPARAMETER["episode"])
		self.centralwidget.layout().addWidget(self.plot_widget1)

		self.plot_widget2 = pyqtgraph.PlotWidget(title="Reward")
		self.plot_widget2.setMouseEnabled(x=False, y=False)
		self.plot_widget2.getPlotItem().hideButtons()
		self.plot_widget2.setXRange(0, HYPERPARAMETER["episode"])
		self.centralwidget.layout().addWidget(self.plot_widget2)

		curve1 = self.plot_widget1.plot([], [], pen="r")
		curve2 = BarGraphItem(x=[], height=[], pen=None, brush="y", width=1)
		curve3 = pyqtgraph.InfiniteLine(pen="g")
		self.plot_widget1.addItem(curve3)
		self.plot_widget2.addItem(curve2)

		self.my_thread = MyThread()
		self.my_thread.curve1 = curve1
		self.my_thread.curve2 = curve2
		self.my_thread.curve3 = curve3
		self.my_thread.start()


class MyThread(QThread):
	signal_update = pyqtSignal(float, float)
	EPISODE = tuple(range(HYPERPARAMETER["episode"]))

	def __init__(self):
		super().__init__()
		util.cast(self.signal_update).connect(self.update)
		self.curve1 = self.curve2 = self.curve3 = None
		self.loss_values, self.rewards = [], []

	def run(self):
		train(self.signal_update)

	def update(self, loss_value, reward):
		self.loss_values.append(loss_value)
		self.rewards.append(reward)

		self.curve1.setData(self.loss_values)
		self.curve2.setOpts(x=self.EPISODE[:len(self.rewards)], height=self.rewards)
		self.curve3.setPos(len(self.loss_values))


if __name__ == "__main__":
	app = QApplication(sys.argv)
	my_core = MyCore()
	my_core.show()
	sys.exit(app.exec())
