import random

import sb_object
import cv2
import time


class TetrisObject(sb_object.SBObject):
    def __init__(self, obj, sb):
        self.state = []
        self.tile_rot = 0
        self.tile_type = 6
        self.tile_pos = (5, 0)
        self.tile_done = False
        self.tiles = [
            [],
            [(-2, 0), (-1, 0), (0, 0), (1, 0)],     # I
            [(-2, 0), (-2, 1), (-1, 1), (0, 1)],     # J
            [(-2, 1), (-1, 1), (0, 1), (0, 0)],     # L
            [(-1, 0), (-1, 1), (0, 1), (0, 0)],     # O
            [(-2, 1), (-1, 1), (-1, 0), (0, 0)],    # S
            [(-2, 1), (-1, 1), (-1, 0), (0, 1)],    # T
            [(-2, 0), (-1, 0), (-1, 1), (0, 1)]     # Z
        ]
        self.centers = [
            (0, 0),
            (-0.5, 0.5),
            (-1, 1),
            (-1, 1),
            (-0.5, 0.5),
            (-1, 1),
            (-1, 1),
            (-1, 1)
        ]
        self.colors = [
            (0, 0, 0),
            (0, 0, 0),
            (0, 255, 255),
            (0, 128, 128),
            (0, 0, 255),
            (0, 0, 128),
            (255, 128, 0),
            (128, 64, 0),
            (255, 255, 0),
            (128, 128, 0),
            (0, 255, 0),
            (0, 128, 0),
            (255, 0, 255),
            (128, 0, 128),
            (255, 0, 0),
            (128, 0, 0)
        ]
        self.lasttime = 0
        self.tile = self._transform(self.tile_type, self.tile_pos, self.tile_rot)
        self.ghost = None
        self.ghost_pos = None
        self.no_lock = False
        self.lines = 0
        self.score = -1
        self.width = 10
        self.height = 20
        super().__init__(obj, sb)

    def _transform(self, t, pos, rot):
        m11, m12, m21, m22 = [(1, 0, 0, 1), (0, -1, 1, 0), (-1, 0, 0, -1), (0, 1, -1, 0)][rot]
        org = self.centers[t]
        return [(int(m11*(i[0]-org[0]) + m12*(i[1]-org[1]) + org[0] + pos[0]), int(m21*(i[0]-org[0]) + m22*(i[1]-org[1]) + org[1] + pos[1])) for i in self.tiles[t]]

    def prepare(self, level):
        self.state = [[0]*self.sb.COLS for x in range(self.sb.ROWS)]
        self.new_tile()
        self.add_ghost()
        self.lines = 0
        self.score = -1
        self.no_lock = False
        self.lasttime = 0

    def get_n_frames(self, cycle=0):
        # Game can continue indefinitely
        return float("inf")

    def set_tile(self, tile, v):
        for i in tile: self.state[i[1]][i[0]] = v

    def add_ghost(self):
        # d1 is the bottom edge of the active tile
        d1 = [-self.height]*self.width
        for i in self.tile:
            if i[1] > d1[i[0]]: d1[i[0]] = i[1]
        # d2 is the upper edge of the existing tiles
        d2 = [self.height]*self.width
        for c in range(10):
            for r in range(max(0, d1[c]+1), self.height):
                if self.state[r][c] and r < d2[c]: d2[c] = r
        d = min(v2 - v1 for v2, v1 in zip(d2, d1)) - 1
        if d > 0:
            self.ghost = [(x, y+d) for x, y in self.tile]
            self.ghost_pos = (self.tile_pos[0], self.tile_pos[1]+d)
            for i in self.ghost: self.state[i[1]][i[0]] = self.state[i[1]][i[0]] or self.tile_type+0.5
        else: self.ghost = None

    def new_tile(self):
        # Check for completed lines
        rp = wp = self.height - 1
        while rp >= 0:
            while rp >= 0 and 0 not in self.state[rp]:
                self.lines += 1
                print(self.lines, "Line cleared")
                rp -= 1
            # rp now points to a non-empty row
            if wp != rp:
                for c in range(self.width): self.state[wp][c] = self.state[rp][c]
            wp -= 1
            rp -= 1
        while wp >= 0:
            for c in range(self.width): self.state[wp][c] = 0
            wp -= 1
        # Insert the new tile
        self.tile_type = random.randint(1, 7)
        self.tile_pos = (self.width//2, 0)
        self.tile_rot = 0
        self.tile = self._transform(self.tile_type, (self.width//2, 0), 0)
        self.set_tile(self.tile, self.tile_type)

    def get_frame(self, n, cycle=0):
        if n != 0:
            if self.lasttime == 0: self.lasttime = time.time()
            key = cv2.waitKey(int(500 - 1000*(time.time() - self.lasttime)))
            if self.ghost: self.set_tile(self.ghost, 0)
            if key == -1 or key == 1 or time.time() - self.lasttime >= 0.5:
                self.lasttime = time.time()
                pnext = (self.tile_pos[0], self.tile_pos[1] + 1)
                tnext = self._transform(self.tile_type, pnext, self.tile_rot)
                for i in tnext:
                    if (i[1] >= self.height or self.state[i[1]][i[0]]) and i not in self.tile:
                        if not self.no_lock: self.new_tile()
                        break
                else:
                    self.set_tile(self.tile, 0)
                    self.tile = tnext
                    self.tile_pos = pnext
                    self.set_tile(self.tile, self.tile_type)
                self.no_lock = False
            elif key == 0:
                tnext = self._transform(self.tile_type, self.tile_pos, (self.tile_rot+1)%4)
                # Look for a possible position, as it may be necessary to move the tile
                # to avoid other tiles
                mx = my = None
                # for mxx, myy in [(0, 0), (1, 0), (1, 1), (0, 1), (-1, 1),
                #                 (-1, 0), (-1, -1), (0, -1), (1, -1), (2, 0),
                #                 (2, 1), (2, 2), (1, 2), (0, 2), (-1, 2),
                #                 (-2, 2), (-2, 1), (-2, 0), (-2, -1), (-2, -2),
                #                 (-1, -2), (0, -2), (1, -2), (2, -2), (2, -1)]:
                for mxx, myy in [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1),
                                 (1, 1), (-1, 1), (-1, -1), (1, -1), (2, 0),
                                 (0, 2), (-2, 0), (0, -2), (2, 1), (1, 2),
                                 (-1, 2), (-2, 1), (-2, -1), (-1, -2), (1, -2),
                                 (2, -1), (2, 2), (-2, 2), (-2, -2), (2, -2)]:
                    for i in tnext:
                        if i[0]+mxx >= self.width or i[0]+mxx < 0 or i[1]+myy >= self.height or i[1]+myy < 0 or (self.state[i[1]+myy][i[0]+mxx] and (i[0]+mxx, i[1]+myy) not in self.tile): break
                    else:
                        mx = mxx
                        my = myy
                        break
                #mx = min(0, min(x[0] for x in tnext)) + max(0, max(x[0] for x in tnext)-10)
                if mx is not None and my is not None:
                    self.set_tile(self.tile, 0)
                    self.tile_rot = (self.tile_rot + 1)%4
                    self.tile_pos = (self.tile_pos[0]+mx, self.tile_pos[1]+my)
                    self.tile = [(x+mx, y+my) for x, y in tnext]
                    self.set_tile(self.tile, self.tile_type)
                    self.no_lock = True
            elif key == 2:
                tnext = self._transform(self.tile_type, (self.tile_pos[0] - 1, self.tile_pos[1]), self.tile_rot)
                for i in tnext:
                    if (i[0] < 0 or self.state[i[1]][i[0]]) and i not in self.tile: break
                else:
                    self.tile_pos = (self.tile_pos[0] - 1, self.tile_pos[1])
                    self.set_tile(self.tile, 0)
                    self.tile = tnext
                    self.set_tile(self.tile, self.tile_type)
                self.no_lock = True
            elif key == 3:
                tnext = self._transform(self.tile_type, (self.tile_pos[0] + 1, self.tile_pos[1]), self.tile_rot)
                for i in tnext:
                    if (i[0] >= self.width or self.state[i[1]][i[0]]) and i not in self.tile: break
                else:
                    self.tile_pos = (self.tile_pos[0] + 1, self.tile_pos[1])
                    self.set_tile(self.tile, 0)
                    self.tile = tnext
                    self.set_tile(self.tile, self.tile_type)
                self.no_lock = True
            elif key == 32:
                self.set_tile(self.tile, 0)
                self.tile = self._transform(self.tile_type, self.ghost_pos, self.tile_rot)
                self.set_tile(self.tile, self.tile_type)
                self.new_tile()
            elif key == ord('q'):
                print("quitting")
                return None, None
            self.add_ghost()
        else: self.prepare(0)
        return [[self.colors[int(2*c)] for c in r] for r in self.state], 1
