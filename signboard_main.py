import struct

import serial
import os
import argparse
import time

import tetris_object
import web_manager
import threading
import re
import json
from PIL import Image

import sb_object
import fcntl


class SignboardLoader:
    def __init__(self):
        self.root = re.search("^(.+)/.+$", os.path.abspath(__file__)).group(1)
        self.file = None
        self.comp_file = None
        self.p = None
        self.headers = None
        self.objects = []
        self.sb_objects = []
        self.letters = {}
        self.WIDTH = self.HEIGHT = self.ROWS = self.COLS = self.scale = self.LENGTH = 0
        self.serialization = [1, -1]

    def load(self, src, comp_file=None, root=None, force=False, level=0):
        """
        Load a configuration file and compile its contents, if necessary.
        Subclasses of SignboardLoader should call the load function of the super class in their load functions

        :param src: The filename of the config file
        :param comp_file: The destination for the compiled frames. Defaults to the source but with ".compiled" as an
        extension
        :param root: Defaults to the current working directory
        :param force:
        :param level: Determines how much frame info should be prepared in advance.
        """
        if root is None: root = self.root
        self.file = os.path.join(root, src)
        self.comp_file = comp_file or os.path.splitext(self.file)[0] + ".compiled"
        with open(self.file) as struc:
            struc = json.load(struc)
            with open(os.path.join(root, struc['settings']['alphabet'])) as l:
                l = json.load(l)
                self.letters = l["letters"]
                self.objects = struc["objects"]
                self.WIDTH = l["width"]
                self.HEIGHT = l["height"]
                self.settings = struc["settings"]
                self.ROWS = self.settings["rows"]
                self.COLS = self.settings["cols"]

                load_img = lambda x: (
                [list(x.getdata())[i * x.size[0]:(i + 1) * x.size[0]] for i in range(x.size[1])], x.size)
                images = {obj["path"]: load_img(Image.open(root + "/images/" + obj["path"])) for obj in self.objects if
                          obj["type"] == "image"}
                images.update({p['path']: load_img(Image.open(root + "/images/" + p['path'])) for obj in self.objects if
                               obj['type'] == 'animation' for p in obj['frames']})
                if len(images) == 0:
                    self.LENGTH = self.COLS * self.settings['scale'] * self.HEIGHT
                else:
                    self.LENGTH = self.COLS * max(self.settings['scale'] * self.HEIGHT,
                                                  images[max(images, key=lambda x: images[x][1][1])][1][1])

                self.letters_scaled = {letter:
                    # for each letter
                    [
                        # for each row
                        [col for col in row for b in range(self.settings['scale'])]
                        for row in self.letters[letter] for a in range(self.settings['scale'])]
                    for letter in self.letters}

                self.scale = self.settings['scale']
                self.sHeight = self.HEIGHT * self.scale
                self.sWidth = self.WIDTH * self.scale

                self.sb_objects = []
                for x in self.objects:
                    if x["type"] == "phrase":
                        self.sb_objects.append(sb_object.PhraseObject(x, self, self.letters_scaled))
                        self.sb_objects[-1].prepare(level)
                    elif x["type"] == "image":
                        self.sb_objects.append(sb_object.ImageObject(x, self))
                        self.sb_objects[-1].prepare(level)
                    elif x["type"] == "animation":
                        self.sb_objects.append(sb_object.AnimationObject(x, self))
                        self.sb_objects[-1].prepare(level)
                    elif x["type"] == "gameoflife":
                        self.sb_objects.append(sb_object.GameOfLifeObject(x, self))
                        self.sb_objects[-1].prepare(level)
                    elif x["type"] == "tetris":
                        self.sb_objects.append(tetris_object.TetrisObject(x, self))
                        self.sb_objects[-1].prepare(level)

                # print(images)
                print("Successfully loaded!")

                # Render the frames in advance
                # phrases_rendered = render(objects)
        # self.compile_frames(force)

    def run_object(self, obj: sb_object.SBObject, cycle=0):
        """
        Display one object on the signboard

        :param obj: SBObject object to run
        :param cycle: The current cycle. This is used for selecting the colors of phrases
        :return: None
        """
        pass


class SignboardSerial(SignboardLoader):
    def __init__(self, port, baud):
        self.port = port
        self.baud = baud
        self.serial = None
        self.running = True
        self.headerSent = False
        super().__init__()

    def init(self):
        try:
            self.serial = serial.Serial(self.port, self.baud)
            return True
        except:
            return False

    def interrupt(self, data=0):
        self.serial.flushInput()
        self.serial.flushOutput()
        self.serial.write(b"\xff\xff\xff"+bytearray([data]))
        self.headerSent = False

    def load(self, src, comp_file=None, root=None, force=False):
        self.running = False
        time.sleep(0.2)         # after disabling, wait for program to reach "breakpoint"
        super().load(src, comp_file, root, force, level=2)
        self.headerSent = False
        self.running = True

    def run_object(self, obj: sb_object.SBObject, cycle=0):
        currFrame = 0
        numFrames = 0
        while True:
            v = self.serial.read()
            if not self.running:
                return False
            if v == b"H":
                numFrames = obj.get_n_frames(cycle)
                currFrame = 0  # just to be safe
                self.headerSent = True
                self.serial.write(obj.get_header(cycle))
                print()
                print("LOADING {} {}".format(obj, numFrames))
                #                print(numFrames, "num frames recvd", ser.readline())
                #                print("colors", ser.readline())
                #                print('time since last header', time.time() - lastHeaderSent)

            if v == b"F":
                if self.headerSent:
                    p, t = obj.get_frame(currFrame, cycle)
                    if p is None: return True
                    self.serial.write(p)
                    # print("writing color", currCycle%len(v))
                    print("\rServing frame " + str(currFrame) + "/" + str(numFrames), end="")
                    currFrame += 1
                    if currFrame >= numFrames: return True
                else:
                    print("Sending interrupt frame (run)")
                    self.interrupt()
        return True

    def close(self):
        self.serial.close()


class SignboardNative(SignboardLoader):
    def __init__(self, file):
        """
        :param file: Path to the ws281x device file. /dev/ws281x by default
        """
        self.running = True
        self.headerSent = False
        super().__init__()
        self.fn = file
        self.chardev = None

    def init(self, pins, stringlen):
        """
        Open the ws281x device file and initialize the driver.

        :param pins: List of output pins in order
        :param stringlen: The length of each independent string of LEDs. All strings will have the same length.
        """
        self.chardev = open(self.fn, "wb", 0)
        print("ioctl", fcntl.ioctl(self.chardev, 0xC004EE00, struct.pack("3I", 0x0000000B, sum(1<<(p-8) for p in pins), stringlen)))
        for n, p in enumerate(pins):
            if p < 8 or p >= 24: continue
            fcntl.ioctl(self.chardev, 0xC004EE01, struct.pack("2B", 1<<(p-8), n))

    def load(self, src, comp_file=None, root=None, force=False):
        self.running = False
        time.sleep(0.2)         # after disabling, wait for program to reach "breakpoint"
        super().load(src, comp_file, root, force, level=1)
        self.running = True

    def run_object(self, obj: sb_object.SBObject, cycle=0):
        last_time = time.time()
        i = 0
        n = obj.get_n_frames(cycle)
        while i < n:
            if not self.running: return False
            img, t = obj.get_frame(i, cycle)
            if img is None: return True
            data = [0]*3*self.LENGTH
            for rn, r in enumerate(img):
                d = self.serialization[rn % len(self.serialization)]
                for cn, c in enumerate(r):
                    e = 3*(rn*self.COLS + (self.COLS-1-cn if d == -1 else cn))
                    data[e:e+3] = c
            data = bytearray(data)
            self.chardev.write(data)
            t = max(t, 10)
            while (time.time() - last_time <= t/1000): pass
            last_time = time.time()
            i += 1
        return True

    def close(self):
        """
        Close the ws281x device file
        """
        self.chardev.close()


if __name__ == "__main__":
    parse = argparse.ArgumentParser(description="Load signboard data from file and output to signboard via serial buffer")
    parse.add_argument("--file", dest="file", help="File containing signboard objects")
    parse.add_argument("--baud", dest="baud", type=int, default=4000000, help="Baud rate for serial connection. Default is 4000000")
    parse.add_argument("--port", dest="port", help="Serial port of the serial buffer")
    parse.add_argument("--recompile", dest="force", action="store_const", const=True, help="Recompile all objects every time. Only for debugging")
    args = parse.parse_args()
    print(args.file, args.port, args.force)

    signboard = SignboardSerial(args.port, args.baud)
    signboard.load(args.file, force=args.force)
    print("connecting...")
    while not signboard.init():
        time.sleep(1)
        print(".", end="")
    print("number of objects is {}".format(len(signboard.objects)))
    signboard.interrupt()

    web_manager.reload = signboard.load
    web_manager.root = signboard.root
    web_manager.signboard = signboard
    threading.Thread(target=web_manager.run).start()

    try:
        while True:
            for x in signboard.sb_objects:
                if not signboard.run_object(x):
                    print("Cycle has been interrupted externally")
                    break
            while not signboard.running: pass
    finally:
        signboard.close()
