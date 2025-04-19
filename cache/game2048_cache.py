from itertools import product
import numpy as np
import pickle


def compute_sequential():
	__compute_moves("cache_sequential.pkl", slice(None, None, None))


def compute_reversed():
	__compute_moves("cache_reversed.pkl", slice(None, None, -1))


def __compute_moves(file_path, piece):
	cache = {}
	for tiles in product(range(12), repeat=4):
		t, merged = [], False
		for tile in tiles:
			if tile == 0:
				continue
			if t and t[-1] == tile and not merged:
				t[-1] += 1
				merged = True
			else:
				t.append(tile)
				merged = False
		cache[bytes(tiles[piece])] = np.array(t + [0] * (4 - len(t)), dtype=np.int8)[piece]
	with open(file_path, mode="wb") as file:
		pickle.dump(cache, file)


def compute_mono():
	cache = {}
	for tiles in product(range(12), repeat=4):
		t = np.diff(tiles)
		cache[bytes(tiles)] = np.sum(tiles) if np.all(t >= 0) or np.all(t <= 0) else 0
	with open("cache_mono.pkl", mode="wb") as file:
		pickle.dump(cache, file)


def compute_smooth():
	cache = {}
	for tiles in product(range(12), repeat=4):
		cache[bytes(tiles)] = np.sum(np.abs(np.diff(tiles)))
	with open("cache_smooth.pkl", mode="wb") as file:
		pickle.dump(cache, file)


def compute_merge():
	cache = {}
	for tiles in product(range(12), repeat=4):
		t = np.array(tiles)
		t = t[t != 0]
		cache[bytes(tiles)] = np.sum(t[:-1][np.diff(t) == 0])
	with open("cache_merge.pkl", mode="wb") as file:
		pickle.dump(cache, file)


if __name__ == "__main__":
	# compute_sequential()
	# compute_reversed()
	# compute_mono()
	# compute_smooth()
	# compute_merge()
	pass
