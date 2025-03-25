from src.recognizer import *
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import os
import torchvision

HYPERPARAMETER = {"batch_size": 64, "learning_rate": 0.001, "epoch": 10}
TRANSFORM = torchvision.transforms.ToTensor()
DATASET = {
	"train": torchvision.datasets.MNIST(train=True, root=os.getcwd(), transform=TRANSFORM, download=False),
	"test": torchvision.datasets.MNIST(train=False, root=os.getcwd(), transform=TRANSFORM, download=False)
}
LOADER = {
	"train": DataLoader(dataset=DATASET["train"], batch_size=HYPERPARAMETER["batch_size"], shuffle=True),
	"test": DataLoader(dataset=DATASET["test"], batch_size=HYPERPARAMETER["batch_size"], shuffle=True)
}


def train_model():
	model = NN(NN.MNIST).to(NN.DEVICE)
	criterion = torch.nn.CrossEntropyLoss()
	optimizer = torch.optim.Adam(model.parameters(), lr=HYPERPARAMETER["learning_rate"])

	losses, batch = [], len(LOADER["train"]) // HYPERPARAMETER["batch_size"]
	for epoch in range(HYPERPARAMETER["epoch"]):
		for i, (datas, labels) in enumerate(LOADER["train"]):
			datas = util.cast(datas).reshape(-1, NN.MNIST["input"]).to(NN.DEVICE)
			labels = labels.to(NN.DEVICE)
			outputs = model(datas)

			loss = criterion(outputs, labels)
			optimizer.zero_grad()
			loss.backward()
			optimizer.step()

			if i % batch == 0:
				losses.append(loss.item())
				print(f"EPOCH[{epoch + 1:02}] LOSS[{losses[-1]:.4f}]")
	torch.save(model.state_dict(), MODEL)

	plt.plot(losses)
	plt.show()


def test_model():
	model = NN(NN.MNIST).to(NN.DEVICE)
	model.load_state_dict(torch.load(MODEL, map_location=NN.DEVICE))

	with torch.no_grad():
		correct = total = 0
		for datas, labels in LOADER["test"]:
			datas = datas.reshape(-1, NN.MNIST["input"]).to(NN.DEVICE)
			labels = labels.to(NN.DEVICE)
			outputs = model(datas)

			_, prediction = torch.max(outputs, dim=1)
			correct += util.cast(prediction == labels).sum().item()
			total += labels.shape[0]
	print(f"ACCURACY[{100 * correct / total:.2f}%]")


if __name__ == "__main__":
	# train_model()
	# test_model()
	pass
