from OpenGL.GL import *
from OpenGL.GLU import *
from itertools import product
import math
import numpy as np

SENSITIVITY_TRANSLATION = 0.15
SENSITIVITY_ROTATION = 0.1
SENSITIVITY_SCALING = 0.5

FORWARD = np.array([0., 0., -1.])
RIGHT = np.array([1., 0., 0.])
UP = np.array([0., 1., 0.])

EYE = np.array([0., 0., 0.])
YAW = -90
PITCH = 0

VERTICES = [[[[
	[i - 0.5, j - 0.5, k - 0.5] for i, j, k in product(range(2), repeat=3)
] for _ in range(3)] for _ in range(3)] for _ in range(3)]
FACES = [
	(1, 2, 0), (1, 2, 3), (1, 4, 0), (1, 4, 5),
	(1, 7, 3), (1, 7, 5), (2, 4, 0), (2, 4, 6),
	(2, 7, 3), (2, 7, 6), (4, 7, 5), (4, 7, 6)
]


class Model:
	'''
	@staticmethod
	def load(path):
		vertices, faces = [], []
		with open(path, mode="r") as file:
			for line in file.read().splitlines():
				if line.startswith("v "):
					vertices.append(tuple(float(v) for v in line[2:].split()))
				if line.startswith("f "):
					faces.append(tuple(int(f.split("/")[0]) - 1 for f in line[2:].split()))
		return vertices, faces
	'''

	@staticmethod
	def cube():
		points = np.array(VERTICES.copy())
		cubelets = np.array([[[Mesh() for _ in range(3)] for _ in range(3)] for _ in range(3)])
		for i, j, k in product(range(3), repeat=3):
			coordinate = i, j, k
			point = points[*coordinate]
			cubelets[*coordinate].vertices = [(point[p, 0], point[p, 1], point[p, 2]) for p in range(8)]
			cubelets[*coordinate].faces = FACES.copy()
		return cubelets

	@staticmethod
	def mirror():
		points = np.array(VERTICES.copy())
		for (i, j, k), p in product(product(range(3), repeat=3), range(8)):
			coordinate = i, j, k, p
			points[*coordinate, 0] += 0.2 if i == 0 and p < 4 else 0
			points[*coordinate, 0] += 0.4 if i == 2 and p >= 4 else 0
			points[*coordinate, 1] -= 0.5 if j == 0 and p % 4 < 2 else 0
			points[*coordinate, 1] -= 0.3 if j == 2 and p % 4 >= 2 else 0
			points[*coordinate, 2] -= 0.6 if k == 0 and p % 2 == 0 else 0
			points[*coordinate, 2] -= 0.4 if k == 2 and p % 2 != 0 else 0

		cubelets = np.array([[[Mesh() for _ in range(3)] for _ in range(3)] for _ in range(3)])
		for i, j, k in product(range(3), repeat=3):
			coordinate = i, j, k
			point = points[*coordinate]
			cubelets[*coordinate].vertices = [(round(point[p, 0], 1), round(point[p, 1], 1), round(point[p, 2], 1)) for p in range(8)]
			cubelets[*coordinate].faces = FACES.copy()
		return cubelets


class Mesh:
	def __init__(self, vertices=None, faces=None):
		self.vertices = vertices
		self.faces = faces

	def draw(self, fill=False):
		glPushMatrix()
		for f in self.faces:
			if fill and f in ((4, 7, 5), (4, 7, 6)):
				glColor(1, 0, 0)
				draw_type = GL_POLYGON
			elif fill and f in ((2, 7, 3), (2, 7, 6)):
				glColor(0, 1, 0)
				draw_type = GL_POLYGON
			elif fill and f in ((1, 7, 3), (1, 7, 5)):
				glColor(0, 0, 1)
				draw_type = GL_POLYGON
			else:
				glColor(1, 1, 1)
				draw_type = GL_LINE_LOOP
			glBegin(draw_type)
			for v in f:
				glVertex3fv(self.vertices[v])
			glEnd()
		glPopMatrix()

	@staticmethod
	def world_axes():
		for i in range(3):
			vector = np.array([i == j for j in range(3)])
			glColor(vector)

			glLineWidth(10)
			glBegin(GL_LINES)
			glVertex3d(*vector * 1000)
			glVertex3d(0, 0, 0)
			glEnd()

			glLineWidth(1)
			glBegin(GL_LINES)
			glVertex3d(*vector * -1000)
			glVertex3d(0, 0, 0)
			glEnd()


class Camera:
	def __init__(self):
		self.forward, self.right, self.up = FORWARD, RIGHT, UP
		self.eye, self.yaw, self.pitch = EYE, YAW, PITCH

	def translate(self, movement=None):
		self.eye = {
			"U": lambda: self.eye + self.up * SENSITIVITY_TRANSLATION,
			"D": lambda: self.eye - self.up * SENSITIVITY_TRANSLATION,
			"L": lambda: self.eye - self.right * SENSITIVITY_TRANSLATION,
			"R": lambda: self.eye + self.right * SENSITIVITY_TRANSLATION,
			None: lambda: self.eye
		}[movement]()
		gluLookAt(*self.eye, *(self.eye + self.forward), *self.up)

	def rotate(self, delta_yaw, delta_pitch):
		self.yaw += delta_yaw * SENSITIVITY_ROTATION
		self.pitch += delta_pitch * SENSITIVITY_ROTATION

		#self.yaw = min(max(self.yaw, YAW - 89), YAW + 89)
		self.pitch = min(max(self.pitch, PITCH - 89), PITCH + 89)

		self.forward = self.normalize(np.array([
			math.cos(math.radians(self.pitch)) * math.cos(math.radians(self.yaw)),
			math.sin(math.radians(self.pitch)),
			math.cos(math.radians(self.pitch)) * math.sin(math.radians(self.yaw))
		]))

		self.forward = self.normalize(self.forward)
		self.right = self.normalize(np.cross(self.forward, np.array([0., 1., 0.])))
		self.up = self.normalize(np.cross(self.right, self.forward))
		gluLookAt(*self.eye, *(self.eye + self.forward), *self.up)

	def scaled(self, magnification):
		self.eye += self.forward * SENSITIVITY_SCALING * magnification
		gluLookAt(*self.eye, *(self.eye + self.forward), *self.up)

	@staticmethod
	def normalize(vector):
		normalization = np.linalg.norm(vector)
		return (vector / normalization) if normalization else np.array([0.] * len(vector))
