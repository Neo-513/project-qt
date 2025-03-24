from src.recognizer import *
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import os
import torchvision

BATCH_SIZE, LEARNING_RATE, EPOCH = 64, 0.001, 10
TRANSFORM = torchvision.transforms.ToTensor()
PATH = {
	"root": os.getcwd(),
	"model": os.path.join(os.getcwd(), "recognizer.pt")
}
DATASET = {
	"train": torchvision.datasets.MNIST(train=True, root=PATH["root"], transform=TRANSFORM, download=True),
	"test": torchvision.datasets.MNIST(train=False, root=PATH["root"], transform=TRANSFORM, download=True)
}
LOADER = {
	"train": DataLoader(dataset=DATASET["train"], batch_size=BATCH_SIZE, shuffle=True),
	"test": DataLoader(dataset=DATASET["test"], batch_size=BATCH_SIZE, shuffle=True)
}


def train_model():
	model = NN(NN.MNIST).to(NN.DEVICE)
	criterion = torch.nn.CrossEntropyLoss()
	optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

	losses, batch = [], len(LOADER["train"]) // BATCH_SIZE
	for epoch in range(EPOCH):
		for i, (datas, labels) in enumerate(LOADER["train"]):
			datas = datas.reshape(-1, NN.MNIST["input"]).to(NN.DEVICE)
			labels = labels.to(NN.DEVICE)
			outputs = model(datas)

			loss = criterion(outputs, labels)
			optimizer.zero_grad()
			loss.backward()
			optimizer.step()

			if i % batch == 0:
				losses.append(loss.item())
				print(f"EPOCH[{epoch + 1:02}] LOSS[{losses[-1]:.4f}]")
	torch.save(model.state_dict(), PATH["model"])

	plt.plot(losses)
	plt.show()


def test_model():
	model = NN(NN.MNIST).to(NN.DEVICE)
	model.load_state_dict(torch.load(PATH["model"], map_location=NN.DEVICE))

	with torch.no_grad():
		correct = total = 0
		for datas, labels in LOADER["test"]:
			datas = datas.reshape(-1, NN.MNIST["input"]).to(NN.DEVICE)
			labels = labels.to(NN.DEVICE)
			outputs = model(datas)

			_, prediction = torch.max(outputs, dim=1)
			correct += (prediction == labels).sum().item()
			total += labels.shape[0]
	print(f"ACCURACY[{100 * correct / total:.2f}%]")


if __name__ == "__main__":
	# train_model()
	# test_model()
	pass
