from PIL import Image
from functools import reduce
import numpy as np
import time
import numbers
from functools import reduce


def extract(cond, x):
    if isinstance(x, numbers.Number):
        return x
    else:
        return np.extract(cond, x)

class vec3():
    def __init__(self, x, y, z):
        (self.x, self.y, self.z) = (x, y, z)
    def __mul__(self, other):
        return vec3(self.x * other, self.y * other, self.z * other)
    def __add__(self, other):
        return vec3(self.x + other.x, self.y + other.y, self.z + other.z)
    def __sub__(self, other):
        return vec3(self.x - other.x, self.y - other.y, self.z - other.z)
    def dot(self, other):
        return (self.x * other.x) + (self.y * other.y) + (self.z * other.z)
    def __abs__(self):
        return self.dot(self)
    def norm(self):
        mag = np.sqrt(abs(self))
        return self * (1.0 / np.where(mag == 0, 1, mag))
    def components(self):
        return (self.x, self.y, self.z)
    def extract(self, cond):
        return vec3(extract(cond, self.x),
                    extract(cond, self.y),
                    extract(cond, self.z))
    def place(self, cond):
        r = vec3(np.zeros(cond.shape), np.zeros(cond.shape), np.zeros(cond.shape))
        np.place(r.x, cond, self.x)
        np.place(r.y, cond, self.y)
        np.place(r.z, cond, self.z)
        return r

    def cross(self, other):
        x = self.y * other.z - self.z * other.y
        y = self.z * other.x - self.x * other.z
        z = self.x * other.y - self.y * other.x
        return vec3(x, y, z)

    def rotate(self, axis, angle):
        return self * np.cos(angle) + axis.cross(self) * np.sin(angle) + axis * axis.dot(self) * (1 - np.cos(angle))

rgb = vec3

(w, h) = (640, 480)         # Screen size
L = vec3(5, 5, -10)        # Point light position
E = vec3(0, 0.35, -1)     # Eye position
FARAWAY = 1.0e39            # an implausibly huge distance

def raytrace(O, D, scene, bounce = 0):
    # O is the ray origin, D is the normalized ray direction
    # scene is a list of Sphere objects (see below)
    # bounce is the number of the bounce, starting at zero for camera rays

    distances = [s.intersect(O, D) for s in scene]
    nearest = reduce(np.minimum, distances)
    color = rgb(0, 0, 0)
    for (s, d) in zip(scene, distances):
        hit = (nearest != FARAWAY) & (d == nearest)
        if np.any(hit):
            dc = extract(hit, d)
            Oc = O.extract(hit)
            Dc = D.extract(hit)
            cc = s.light(Oc, Dc, dc, scene, bounce)
            color += cc.place(hit)
    return color

class Sphere:
    def __init__(self, center, r, diffuse, mirror = 0.5):
        self.c = center
        self.r = r
        self.diffuse = diffuse
        self.mirror = mirror

    def intersect(self, O, D):
        b = 2 * D.dot(O - self.c)
        c = abs(self.c) + abs(O) - 2 * self.c.dot(O) - (self.r * self.r)
        disc = (b ** 2) - (4 * c)
        sq = np.sqrt(np.maximum(0, disc))
        h0 = (-b - sq) / 2
        h1 = (-b + sq) / 2
        h = np.where((h0 > 0) & (h0 < h1), h0, h1)
        pred = (disc > 0) & (h > 0)
        return np.where(pred, h, FARAWAY)

    def diffusecolor(self, M):
        return self.diffuse




    def light(self, O, D, d, scene, bounce):
        M = (O + D * d)                         # intersection point
        N = (M - self.c) * (1. / self.r)        # normal
        toL = (L - M).norm()                    # direction to light
        toO = (E - M).norm()                    # direction to ray origin
        nudged = M + N * .0001                  # M nudged to avoid itself

        # Shadow: find if the point is shadowed or not.
        # This amounts to finding out if M can see the light
        light_distances = [s.intersect(nudged, toL) for s in scene]
        light_nearest = reduce(np.minimum, light_distances)
        seelight = light_distances[scene.index(self)] == light_nearest

        # Ambient
        color = rgb(0.05, 0.05, 0.05)

        # Lambert shading (diffuse)
        lv = np.maximum(N.dot(toL), 0)
        color += self.diffusecolor(M) * lv * seelight

        # Reflection
        if bounce < 2:
            rayD = (D - N * 2 * D.dot(N)).norm()
            color += raytrace(nudged, rayD, scene, bounce + 1) * self.mirror

        # Blinn-Phong shading (specular)
        phong = N.dot((toL + toO).norm())
        color += rgb(1, 1, 1) * np.power(np.clip(phong, 0, 1), 50) * seelight
        return color

class CheckeredSphere(Sphere):
    def diffusecolor(self, M):
        checker = ((M.x * 2).astype(int) % 2) == ((M.z * 2).astype(int) % 2)
        return self.diffuse * checker

class Triangle:
    def __init__(self, a, b, c, diffuse, mirror = 0.5):
        self.a = a
        self.b = b
        self.c = c
        self.diffuse = diffuse
        self.mirror = mirror

    def intersect(self, O, D):
        u = self.b - self.a
        v = self.c - self.a
        w = O - self.a

        cross_v_u_dot = D.cross(v).dot(u)
        t = 1 / cross_v_u_dot * (w.cross(u).dot(v))
        r = 1 / cross_v_u_dot * (D.cross(v).dot(w))
        s = 1 / cross_v_u_dot * (w.cross(u).dot(D))

        pred = np.logical_and.reduce((r >= 0, r <= 1, s >= 0, s <= 1, r + s <= 1))
        return np.where(pred, t, FARAWAY)

    def diffusecolor(self, M):
        return self.diffuse

    def intersect_normal(self, a, b, c):
        return (a - b).cross(c - b).norm()


    def light(self, O, D, d, scene, bounce):
        M = (O + D * d)  # intersection point
        N = self.intersect_normal(self.a, self.b, self.c)  # normal
        toL = (L - M).norm()  # direction to light
        toO = (E - M).norm()  # direction to ray origin
        nudged = M + N * .0001  # M nudged to avoid itself

        # Shadow: find if the point is shadowed or not.
        # This amounts to finding out if M can see the light
        light_distances = [s.intersect(nudged, toL) for s in scene]
        light_nearest = reduce(np.minimum, light_distances)
        seelight = light_distances[scene.index(self)] == light_nearest

        # Ambient
        color = rgb(0.05, 0.05, 0.05)

        # Lambert shading (diffuse)
        lv = np.maximum(N.dot(toL), 0)
        color += self.diffusecolor(M) * lv * seelight

        # Reflection
        if bounce < 2:
            rayD = (D - N * 2 * D.dot(N)).norm()
            color += raytrace(nudged, rayD, scene, bounce + 1) * self.mirror

        # Blinn-Phong shading (specular)
        phong = N.dot((toL + toO).norm())
        color += rgb(1, 1, 1) * np.power(np.clip(phong, 0, 1), 50) * seelight
        return color

class Plane:
    def __init__(self, center, normal, diffuse, mirror=0.05):
        self.c = center
        self.n = normal
        self.diffuse = diffuse
        self.mirror = mirror

    def intersect(self, O, D):
        s = -self.n.dot(O - self.c) / self.n.dot(D)
        return np.where((s > 0), s, FARAWAY)

    def diffusecolor(self, M):
        checker = (np.ceil((M.x * 2)) % 2) == (np.ceil((M.z * 2)) % 2)
        return self.diffuse * checker

    def light(self, O, D, d, scene, bounce):
        M = (O + D * d)  # intersection point
        N = self.n  # normal
        toL = (L - M).norm()  # direction to light
        toO = (E - M).norm()  # direction to ray origin
        nudged = M + N * .0001  # M nudged to avoid itself

        # Shadow: find if the point is shadowed or not.
        # This amounts to finding out if M can see the light
        light_distances = [s.intersect(nudged, toL) for s in scene]
        light_nearest = reduce(np.minimum, light_distances)
        seelight = light_distances[scene.index(self)] == light_nearest

        # Ambient
        color = rgb(0.05, 0.05, 0.05)

        # Lambert shading (diffuse)
        lv = np.maximum(N.dot(toL), 0)
        color += self.diffusecolor(M) * lv * seelight

        # Reflection
        if bounce < 2:
            rayD = (D - N * 2 * D.dot(N)).norm()
            color += raytrace(nudged, rayD, scene, bounce + 1) * self.mirror

        # Blinn-Phong shading (specular)
        phong = N.dot((toL + toO).norm())
        color += rgb(1, 1, 1) * np.power(np.clip(phong, 0, 1), 50) * seelight
        return color





scene = [
        Sphere(vec3(.65, .1, 2), .6, vec3(1, .155, 0)),
        Sphere(vec3(-.65, .1, 2), .6, vec3(0, .255, .0)),
        Sphere(vec3(0, 1.2, 2), .6, vec3(0, .153, .76)),
        Plane(vec3(0, -.5, 0), vec3(0, 1, 0), vec3(1, 1, 1)),
        #CheckeredSphere(vec3(0, -99999.5, 0), 99999, vec3(1, 1, 1), .25), #is not a plane
        Triangle(vec3(-.5, .1, 2), vec3(.75, .1, 2), vec3(0, 1.25, 2.25), vec3(1, 1, 0), .25),

]
def main_scene(self, w, h, p=False, n=False):
    self.w = w
    self.h = h
    self.p = p
    self.n = n

    #TODO this needs work

    if self.p or self.n:
        for OBJECT in scene:
            if p:
              OBJECT.c.x = OBJECT.c.x + np.pi / 10
            if n:
                OBJECT.c.x = OBJECT.c.x - np.pi / 10

    r = float(w) / h
    # Screen coordinates: x0, y0, x1, y1.
    S = (-1, 1 / r + .25, 1, -1 / r + .25)
    x = np.tile(np.linspace(S[0], S[2], w), h)
    y = np.repeat(np.linspace(S[1], S[3], h), w)

    t0 = time.time()
    Q = vec3(x, y, 0)
    color = raytrace(E, (Q - E).norm(), scene)
    print("Took", time.time() - t0)

    rgb = [Image.fromarray((255 * np.clip(c, 0, 1).reshape((h, w))).astype(np.uint8), "L") for c in color.components()]
    im = Image.merge("RGB", rgb)

    return np.array(im)


