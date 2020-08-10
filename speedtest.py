import board
import neopixel

import time
import sys

p = int(sys.argv[1])
mode = sys.argv[2]

ROWS = 15
COLS = 20

show = []

LENGTH = ROWS*COLS

strip = neopixel.NeoPixel(board.D18, LENGTH, auto_write=False, pixel_order=neopixel.GRB)

try:
    with open("/dev/urandom", "rb") as f:
        if mode == "random":
            while True:
                a = time.time()
                for x in range(LENGTH):
                    #strip[x] = [255*((x//p)%2)]*3
                    strip[x] = list(f.read(3))
                b = time.time()
                strip.show()
                c = time.time()
                for x in range(LENGTH):
                    #strip[x] = [255*(1-(x//p)%2)]*3
                    strip[x] = list(f.read(3))
                d = time.time()
                strip.show()
                e = time.time()
                
                print("set{:.5f} fill{:.5f} set{:.5f} fill{:.5f}".format(b-a, c-b, d-c, e-d))
                show.append(c-b)
                show.append(e-d)
        elif mode == "rows":
            while True:
                a = time.time()
                for x in range(LENGTH):
                    strip[x] = [255*((x//p)%2)]*3
                b = time.time()
                strip.show()
                c = time.time()
                for x in range(LENGTH):
                    strip[x] = [255*(1-(x//p)%2)]*3
                d = time.time()
                strip.show()
                e = time.time()
                
                print("set{:.5f} fill{:.5f} set{:.5f} fill{:.5f}".format(b-a, c-b, d-c, e-d))
                show.append(c-b)
                show.append(e-d)
except:
                print("      average{:.5f}".format(sum(show)/len(show)))