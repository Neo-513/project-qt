from itertools import product
import pickle

def compute_surrounding():
	cache = {"easy": {}, "medium": {}, "hard": {}}
	offset = tuple(pos for pos in product(range(-1, 2), repeat=2) if pos != (0, 0))
	for d, (r, c) in {"easy": (9, 9), "medium": (16, 16), "hard": (16, 30)}.items():
		for x, y in product(range(r), range(c)):
			cache[d][x, y] = tuple((x + i, y + j) for i, j in offset if 0 <= (x + i) < r and 0 <= (y + j) < c)
	with open("surrounding.pkl", mode="wb") as file:
		pickle.dump(cache, file)


def compute_platform():
	cache = {"easy": {}, "medium": {}, "hard": {}}
	with open("surrounding.pkl", mode="rb") as file:
		cache_surrounding = pickle.load(file)
	for d, (r, c) in {"easy": (9, 9), "medium": (16, 16), "hard": (16, 30)}.items():
		s = set(cache_surrounding[d])
		for x, y in product(range(r), range(c)):
			cache[d][x, y] = tuple(s - {(x + i, y + j) for i, j in product(range(-2, 3), repeat=2)})
	with open("platform.pkl", mode="wb") as file:
		pickle.dump(cache, file)


if __name__ == "__main__":
	# compute_surrounding()
	# compute_platform()
	pass
