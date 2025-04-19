from itertools import product
import pickle


def compute_surrounding():
	cache = {"easy": {}, "medium": {}, "hard": {}}
	difficulty = {"easy": (9, 9), "medium": (16, 16), "hard": (16, 30)}
	offset = tuple(pos for pos in product(range(-1, 2), repeat=2) if pos != (0, 0))
	for d, (r, c) in difficulty.items():
		for x, y in product(range(r), range(c)):
			cache[d][x, y] = tuple((x + i, y + j) for i, j in offset if 0 <= (x + i) < r and 0 <= (y + j) < c)
	with open("surrounding.pkl", mode="wb") as file:
		pickle.dump(cache, file)


if __name__ == "__main__":
	compute_surrounding()
