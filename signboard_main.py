# To predict time of a phrase:
# (n*0.00003+d+(5*r*c/b))*(c+s*(w+1)*l-1)
# where:
#  n = number of LEDs per string
#  d = speed
#  r = rows
#  c = cols
#  b = serial baud rate
#  s = scale
#  w = width of a character
#  l = length of the phrase

import serial
import os
import argparse
import time
import hashlib
import base64
import web_manager
import threading
import multiprocessing
import re
import json
from PIL import Image


def compile_one(index, obj, pcol, images, begin, end, settings, letters_scaled):
    """
    Compiles a certain range of frames.

    index:  the index of the current object
    obj:    the current object
    pcol:   the colors used in the object
    images: the image data (if needed) for this object
    begin:  the frame to start with
    end:    the frame th end with
    """
    with open("/tmp/signboard.log", "a") as f: f.write("compiling...\n")
    try:
        ROWS = settings['rows']
        COLS = settings['cols']
        def setPixel(r, c):
            if r >= ROWS or c >= COLS or r < 0 or c < 0: return -1
            i = int((2 * COLS) - 2 + r + (2 * (COLS - 1) * ((r - 1) // 2.0)) + (c * (1 - 2 * (r % 2))))
            if i >= settings['length']: return -1
            return i
        pfrms = []
        t = obj['type']
        if t=='phrase':
          sWidth = settings['scale']*settings['width']
          sHeight = settings['scale']*settings['height']
          for frm_idx in range(begin, end):
            data = bytearray([0x22]*settings['rows']*settings['cols'])
            for ci, c in enumerate(obj['phrase']):
                l = letters_scaled.get(c, letters_scaled['uc'])
                offset = settings['cols']-frm_idx+(ci*settings['scale']*(settings['width']+1))
                if -offset > sWidth or offset > settings['cols']: continue
                for x in range(sHeight):
                    for y in range(sWidth):
                        p = setPixel(settings['rows'] - sHeight + x, y + offset)
                        if p == -1: continue
                        data[int(p/2)] = data[int(p/2)] & (0xf0 if p%2 else 0x0f) | ((1 if l[x][y] else 2) << (0 if p%2 else 4))
            pfrms.append(bytearray([int(obj['speed']>>8), obj['speed']&255]) + data)
        elif t=='image':
            i = images[obj['path']]
            data = bytearray([pcol.index((0,0,0))]*settings['length'])
            for rn, r in enumerate(i[0]):
                for cn, c in enumerate(r):
                    p = setPixel(ROWS-i[1][1]+rn, cn+obj['startoffset'])
                    if p == -1: continue
                    data[int(p/2)] = data[int(p/2)] & (0xf0 if p%2 else 0x0f) | (pcol.index(c) << (0 if p%2 else 4))
            pfrms.append(bytearray([int(obj['time']>>8), obj['time']&255]) + data)
        else:
            for x in range(obj['iterations']):
                for iy, y in enumerate(obj['frames']):
                    if not begin <= (len(obj['frames'])*x+iy) < end: continue
                    data = bytearray([pcol.index((0,0,0))]*int((settings['length']+1)/2))
                    h = images[y['path']][1][1]
                    for rn, r in enumerate(images[y['path']][0]):
                        for cn, c in enumerate(r):
                            p = setPixel(ROWS-h+rn, cn+obj['start']+obj['step']*x+y['offset'])
                            if p == -1: continue
                            data[int(p/2)] = data[int(p/2)] & (0xf0 if p%2 else 0x0f) | (pcol.index(c) << (0 if p%2 else 4))
                    pfrms.append(bytearray([int(y['time']>>8), y['time']&255]) + data)

        return (index, pfrms, t, begin, end)
    except Exception as e:
        with open("/tmp/signboard.log", "a") as f: 
            f.write(str(e))
            f.write("\n")


class SignboardLoader:
    def __init__(self):
        self.root = re.search("^(.+)/.+$", os.path.abspath(__file__)).group(1)
        self.file = None
        self.comp_file = None
        self.p = None
        self.headers = None

    def load(self, src, comp_file=None, root=None, force=False):
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
                TEXTFILLLENGTH = self.COLS * self.settings['scale'] * self.HEIGHT
                # print(neopixel, dir(neopixel))

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

                # print(images)
                print("Successfully loaded!")

                # Render the frames in advance
                # phrases_rendered = render(objects)
        self.compile_frames(force)


    def color2bytes(self, x):
        b = bytearray("   ", "utf-8")
        b[0] = int((x>>16)&255)
        b[1] = int((x>>8) &255)
        b[2] = x & 255
        return b

    def compile_frame(self, frame, col, dtime):
        return bytearray([int(dtime>>8), dtime&255]) + b"".join([ bytearray([(col.index(frame[x])<<4) + (0 if len(frame)==x+1 else col.index(frame[x+1]))]) for x in range(0, len(frame), 2) ])


    def apply_results(self, args):
        index, pfrms, t, begin, end = args
        self.p[index][begin:end]=pfrms

    def compile_frames(self, force=False):

        #check if previous data is available
        self.headers = [None if x['type']!='phrase' else [None]*sum(y['duration'] for y in x['colors']) for x in self.objects]
        self.p = [[]]*len(self.objects)


        if force:
            print("Forced recompile")
        elif os.path.exists(self.comp_file):
            print("version found")
            with open(self.comp_file) as f:
                j = json.load(f)
                if len(j) == len(self.objects):
                    for obj_index, obj in enumerate(j):
                        h_n = hashlib.md5()
                        h_n.update(json.dumps(self.objects[obj_index], sort_keys=True).encode())
                        this = self.objects[obj_index]
                        if h_n.hexdigest() == obj['hash'].strip():
                            print("version found with matching hash for object", obj_index)
                            self.headers[obj_index] = (eval(base64.b64decode(obj['header'].encode()).decode()))
                            self.p[obj_index] = (eval(base64.b64decode(obj['frames'].encode()).decode()))
                            print(obj['header'], base64.b64decode(obj['header'].encode()).decode())
                        else:
                            print("hashes do not match for {}: old={} and new={}".format(obj_index, obj['hash'].strip(), h_n.hexdigest()))





    #    rendered = signboard.render(objs, dont_render)
    #    p_in = list(filter(lambda x: x is not None, rendered))

        slen = self.ROWS*self.COLS
        print("size of the signboard", slen)


        obj2colors = lambda obj: list(map(list, set(map(tuple, (col for frm in obj for col in frm)))))

        print("Before compiling", [bool(x) for x in self.p])

        load_img = lambda x: ([list(x.getdata())[i*x.size[0]:(i+1)*x.size[0]] for i in range(x.size[1])], x.size)

        comp_start = time.time()

        settings = {
            "rows": self.ROWS,
            "cols": self.COLS,
            "length": self.LENGTH,
            "width": self.WIDTH,
            "height": self.HEIGHT,
            "scale": self.scale
        }

        for index, obj in enumerate(self.objects):
            if bool(self.p[index]) and bool(self.p[index][0]):
                print("Skipping compile for", index)
                continue
            t = obj['type']

            # "images": contains image/animation data
            images = []
            if t == 'image': images = {obj["path"]: load_img(Image.open(os.path.join(self.root, "images/", obj["path"])))}
            if t == 'animation': images = {f['path']: load_img(Image.open(os.path.join(self.root, "images/", f['path']))) for f in obj['frames']}

            # "pcol": contains the colors used the in the object
            if t != 'phrase':
                pcol = [-1]
                for x in images:
                    [pcol.append(c) for r in images[x][0] for c in r if c not in pcol]
            else: pcol = [-1] + [c for pattern in obj['colors'] for c in [pattern["color"], pattern["background"]]]

            # "nfrms": contains the exact number of frames in the final compilation
            if t == "phrase": nfrms = self.COLS + self.settings['scale']*(self.WIDTH+1)*len(obj['phrase'])
            elif t == "animation": nfrms = obj['iterations']*len(obj['frames'])
            else: nfrms = 1

            phead = bytearray([int(nfrms>>8), nfrms&255, int(slen>>8), slen&255])
            if t != "phrase": self.headers[index] = phead + b"".join(bytearray(col) for col in pcol[1:])
            else: self.headers[index] = [phead + bytearray(c["color"]) + bytearray(c["background"]) for c in obj['colors']]

            # Put in blank frames
            self.p[index] = [None]*nfrms


            pool = multiprocessing.Pool()

            if nfrms <= 50:
                pool.apply_async(compile_one, args=(index, obj, pcol, images, 0, nfrms, settings, self.letters_scaled), callback=self.apply_results)
            elif nfrms <=200:
                n_proc = 0
                while n_proc < nfrms:
                    pool.apply_async(compile_one, args=(index, obj, pcol, images, n_proc, min(nfrms, n_proc+50), settings, self.letters_scaled), callback=self.apply_results)
                    n_proc += 50
            else:
                nper = nfrms // 4 + 1
                for x in range(4):
                    pool.apply_async(compile_one, args=(index, obj, pcol, images, nper*x, min(nfrms, nper*x+nper), settings, self.letters_scaled), callback=self.apply_results).get()
            pool.close()
            pool.join()
            print("Finished", index)
        print("All threads terminated in", time.time() - comp_start)


        with open(self.comp_file, "w") as f:
            f.write("[\n")
            for i in range(len(self.objects)):
                object_hash = hashlib.md5()
                object_hash.update(json.dumps(self.objects[i], sort_keys=True).encode())
                print("Saving with hash {} for {}".format(object_hash.hexdigest(), i))

                if i != 0: f.write(",\n")
                f.write('    {\n        "hash": "%s",\n' % (object_hash.hexdigest()))
                f.write('        "header": "{}",\n'.format(base64.b64encode(str(self.headers[i]).encode()).decode()))
                f.write('        "frames": "{}"\n'.format(base64.b64encode(str(self.p[i]).encode()).decode()))
                f.write("    }")
            f.write("\n]\n")

        print("After compiling", [bool(x) for x in self.p], [(i, len(x)) for i, x in enumerate(self.p) if isinstance(x, list)])


class SignboardSerial(SignboardLoader):
    def __init__(self, port, baud):
        self.port = port
        self.baud = baud
        self.serial = None
        self.running = True
        self.headerSent = False
        super().__init__()

    def init_ser(self):
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
        """
        Load a configuration file and compile its contents, if necessary.
        :param src: The filename of the config file
        :param comp_file: The destination for the compiled frames. Defaults to the source but with ".compiled" as an extension
        :param root: Defaults to the current working directory
        :return:
        """
        self.running = False
        time.sleep(0.2)         # after disabling, wait for program to reach "breakpoint"
        super().load(src, comp_file, root, force)
        self.headerSent = False
        self.running = True

    def run_object(self, index, cycle=0):
        """
        Display one object on the signboard
        :param index: The index of the object to be run
        :param cycle: The current cycle. This is used for selecting the colors of phrases
        :return: None
        """
        currFrame = 0
        numFrames = 0
        while True:
            v = self.serial.read()
            if not self.running:
                return False
            if v == b"H":
                numFrames = len(self.p[index])
                currFrame = 0  # just to be safe
                self.headerSent = True
                if self.objects[index]['type'] != 'phrase':
                    self.serial.write(self.headers[index])
                else:
                    v = self.headers[index]
                    self.serial.write(v[cycle % len(v)])
                print()
                print("LOADING {} {}".format(index, numFrames))
                #                print(numFrames, "num frames recvd", ser.readline())
                #                print("colors", ser.readline())
                #                print('time since last header', time.time() - lastHeaderSent)

            if v == b"F":
                if self.headerSent:
                    self.serial.write(self.p[index][currFrame])
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
    while not signboard.init_ser():
        time.sleep(1)
        print(".", end="")
    print("number of objects is {}".format(len(signboard.objects)))
    signboard.interrupt()

    web_manager.reload = signboard.load
    web_manager.root = signboard.root
    threading.Thread(target=web_manager.run).start()

    try:
        while True:
            for x in range(len(signboard.objects)):
                if not signboard.run_object(x):
                    print("Cycle has been interrupted externally")
                    break
            while not signboard.running: pass
    finally:
        signboard.close()
