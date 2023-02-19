from PIL import Image
import os


class SBObject:
    def __init__(self, obj, sb):
        """
        Class representing an object that can be displayed on the signboard

        :param obj: Dictionary describing the object. This parameter uses the same format as the JSON configuration
                    files would
        :param sb: Signboard object, typically an instance of a subclass of SignboardLoader
        """
        self.obj = obj
        self.sb = sb
        pass

    def get_n_frames(self, cycle=0):
        """
        Return the number of frames in the object
        """
        pass

    def get_frame(self, n, cycle=0):
        """
        Return frame n of the object. The type of the output depends on the preparation level:
            0, 1 - Return a 2D list of colors in (R, G, B) format.
            2 - Return a bytearray that can be transmitted to a serial buffer.

        In addition to the frame data, get_frame will return the time for which the frame should be displayed.

        :param n: Frame number to return
        :param cycle: Objects that change behavior between cycles (e.g. phrases that use different colors) can use
                      this number.
        """
        pass

    def prepare(self, level):
        """
        Prepare some or all frame information in advance for faster frame generation
        The level parameter defines how much should be prepared and the behavior of get_frame:
            0 - Minimum preparation. Load images
            1 - For phrases, prepare pixel information of the whole phrase
            2 - Compile binary output for use with SignboardSerial

        :param level: The level of preparation
        """
        pass

    def get_header(self, cycle=0):
        """
        Return header information of the object. The type of the output depends on the preparation level:
            0, 1 - Return None.
            2 - Return a bytearray that can be transmitted to a serial buffer.
        """
        pass

    def __getitem__(self, item):
        return self.obj[item]


class PhraseObject(SBObject):
    def __init__(self, obj, sb, alphabet):
        self.alphabet = alphabet
        self.color_cumsum = []
        self.full = []
        self.compiled = []
        self.headers = []
        self.level = 0
        super().__init__(obj, sb)

    def prepare(self, level):
        self.level = level
        if level >= 0:
            self.color_cumsum = []
            i = 0
            for c in self["colors"]:
                i += c["duration"]
                self.color_cumsum.append(i)
        if level >= 1:
            # Make one big image containing the whole phrase
            # A subset of this image will be displayed for every frame
            sWidth = self.sb.scale*(self.sb.WIDTH+1)
            self.full = [[0]*sWidth*len(self["phrase"]) for i in range(self.sb.ROWS)]
            for ci, c in enumerate(self["phrase"]):
                l = self.alphabet.get(c, self.alphabet['uc'])
                for rn, r in enumerate(l):
                    #print(rn, ci*self.sb.sWidth, (ci+1)*self.sb.sWidth, len(self.full[0]))
                    self.full[rn][ci*sWidth:(ci+1)*sWidth] = r
        if level == 2:
            # Compile the object into a sequence of binary frames
            fw = len(self.full[0])
            nfrms = self.get_n_frames(0)
            slen = self.sb.ROWS * self.sb.COLS
            for frm_idx in range(nfrms):
                data = bytearray([0x22] * (slen // 2))
                offset = self.sb.COLS - frm_idx*self["step"] - self["offset"]
                for rn, r in enumerate(self.full):
                    d = self.sb.serialization[rn % len(self.sb.serialization)]
                    for cn in range(max(0, offset), min(fw + offset, self.sb.COLS)):
                        e = (rn * self.sb.COLS + (self.sb.COLS - 1 - cn if d == -1 else cn))
                        data[int(e / 2)] = data[int(e / 2)] & (0xf0 if e % 2 else 0x0f) | (
                                        (1 if r[cn-offset] else 2) << (0 if e % 2 else 4))
                self.compiled.append(bytearray([int(self['speed'] >> 8), self['speed'] & 255]) + data)

            phead = bytearray([int(nfrms>>8), nfrms&255, int(slen>>8), slen&255])
            self.headers = [phead + bytearray(c["color"]) + bytearray(c["background"]) for c in self['colors']]

    def get_n_frames(self, cycle=0):
        return (self.sb.COLS + len(self["phrase"])*self.sb.scale*(self.sb.WIDTH+1))//self["step"]

    def get_frame(self, n, cycle=0):
        for s, c in zip(self.color_cumsum, self["colors"]):
            if cycle % self.color_cumsum[-1] < s:
                fg = c["color"]
                bg = c["background"]
                break
        if self.level == 0:
            sWidth = self.sb.scale * self.sb.WIDTH
            sHeight = self.sb.scale * self.sb.HEIGHT
            result = [[bg]*self.sb.COLS for x in range(self.sb.ROWS)]
            for ci, c in enumerate(self['phrase']):
                l = self.alphabet.get(c, self.alphabet['uc'])
                offset = self.sb.COLS - n*self["step"] + (ci * self.sb.scale * (self.sb.WIDTH + 1)) - self['offset']
                if -offset > sWidth: continue
                if offset > self.sb.COLS: break
                for x in range(sHeight):
                    for y in range(sWidth):
                        if not 0 <= self.sb.ROWS - sHeight + x < self.sb.ROWS: continue
                        if not 0 <= y + offset < self.sb.COLS: continue
                        if l[x][y]: result[self.sb.ROWS - sHeight + x][y + offset] = fg
            return result, self["speed"]
        if self.level == 1:
            result = [[bg] * self.sb.COLS for x in range(self.sb.ROWS)]
            offset = self.sb.COLS - n*self["step"] - self['offset']
            fw = len(self.full[0])
            for rn, r in enumerate(self.full):
                for cn in range(max(0, offset), min(fw + offset, self.sb.COLS)):
                    if self.full[rn][cn-offset]: result[rn][cn] = fg
            return result, self["speed"]
        if self.level == 2:
            return self.compiled[n], self["speed"]

    def get_header(self, cycle=0):
        for s, h in zip(self.color_cumsum, self.headers):
            if cycle % self.color_cumsum[-1] < s:
                return h


class ImageObject(SBObject):
    def __init__(self, obj, sb):
        self.img = None
        self.size = None
        self.compiled = None
        self.header = None
        self.full = []
        super().__init__(obj, sb)

    def load_img(self, img):
        size = img.size
        data = img.getdata()
        return [list(data)[i * size[0]:(i + 1) * size[0]] for i in range(size[1])], size

    def prepare(self, level):
        self.level = level
        if level >= 0:
            self.img, self.size = self.load_img(Image.open(os.path.join(self.sb.root, os.path.join("images", self["path"]))))
        if level == 1:
            self.full = [[[0, 0, 0]] * self.sb.COLS for x in range(self.sb.ROWS)]
            ofs = self["startoffset"]
            if ofs < self.sb.COLS:
                for rn, r in enumerate(self.img):
                    self.full[rn][max(ofs, 0):min(ofs+self.size[0], self.sb.COLS)] = r[max(-ofs, 0):min(self.sb.COLS-ofs, self.size[0])]
        if level == 2:
            slen = self.sb.ROWS * self.sb.COLS
            # Compute header information
            pcol = set()
            for r in self.img: pcol.update(r)
            pcol = list(pcol)                               # Convert set of colors to list
            phead = bytearray([0, 1, int(slen >> 8), slen & 255])
            if (0, 0, 0) in pcol: pcol.remove((0, 0, 0))    # Remove black if present
            pcol.insert(0, (0, 0, 0))                       # Re-insert black at beginning
            self.header = phead + b"".join(bytearray(col) for col in pcol)
            pcol = {x: i+1 for i, x in enumerate(pcol)}     # Convert list of colors to dict for faster conversion
            print("colors are", pcol, self.header)
            # Compute frame information
            data = bytearray([0x11] * (slen // 2))
            offset = self["startoffset"]
            for rn, r in enumerate(self.img):
                d = self.sb.serialization[rn % len(self.sb.serialization)]
                for cn in range(max(0, offset), min(self.size[0] + offset, self.sb.COLS)):
                    e = (rn * self.sb.COLS + (self.sb.COLS - 1 - cn if d == -1 else cn))
                    data[int(e / 2)] = data[int(e / 2)] & (0xf0 if e % 2 else 0x0f) | (
                            (pcol[r[cn - offset]]) << (0 if e % 2 else 4))
            self.compiled = bytearray([int(self['time'] >> 8), self['time'] & 255]) + data

    def get_n_frames(self, cycle=0):
        return 1

    def get_frame(self, n, cycle=0):
        if self.level == 2: return self.compiled, self["time"]
        return self.full, self["time"]

    def get_header(self, cycle=0):
        return self.header


class AnimationObject(SBObject):
    def __init__(self, obj, sb):
        self.img = []
        self.size = []
        self.compiled = []
        self.header = None
        self.level = -1
        super().__init__(obj, sb)

    def load_img(self, img):
        size = img.size
        data = img.getdata()
        return [list(data)[i * size[0]:(i + 1) * size[0]] for i in range(size[1])], size

    def prepare(self, level):
        self.level = level
        if self.level >= 0:
            self.img = []
            self.size = []
            for x in self["frames"]:
                i, s = self.load_img(Image.open(os.path.join(self.sb.root, os.path.join("images", x["path"]))))
                self.img.append(i)
                self.size.append(s)
        if self.level == 2:
            nfrms = self.get_n_frames(0)
            slen = self.sb.ROWS * self.sb.COLS
            # Compute header information
            pcol = set()
            for img in self.img:
                for r in img: pcol.update(r)
            pcol = list(pcol)                               # Convert set of colors to list
            phead = bytearray([int(nfrms >> 8), nfrms & 255, int(slen >> 8), slen & 255])
            if (0, 0, 0) in pcol: pcol.remove((0, 0, 0))    # Remove black if present
            pcol.insert(0, (0, 0, 0))                       # Re-insert black at beginning
            self.header = phead + b"".join(bytearray(col) for col in pcol)
            pcol = {x: i+1 for i, x in enumerate(pcol)}     # Convert list of colors to dict for faster conversion
            print("colors are", pcol)
            # Compute frame information
            for it in range(self["iterations"]):
                for f, fr in enumerate(self["frames"]):
                    data = bytearray([0x11] * (slen // 2))
                    offset = self["start"] + it*self["step"] + fr["offset"]
                    sz = self.size[f][0]
                    for rn, r in enumerate(self.img[f]):
                        d = self.sb.serialization[rn % len(self.sb.serialization)]
                        for cn in range(max(0, offset), min(sz + offset, self.sb.COLS)):
                            e = (rn * self.sb.COLS + (self.sb.COLS - 1 - cn if d == -1 else cn))
                            data[int(e / 2)] = data[int(e / 2)] & (0xf0 if e % 2 else 0x0f) | (
                                    (pcol[r[cn - offset]]) << (0 if e % 2 else 4))
                    self.compiled.append(bytearray([int(fr['time'] >> 8), fr['time'] & 255]) + data)

    def get_n_frames(self, cycle=0):
        return self["iterations"]*len(self["frames"])

    def get_frame(self, n, cycle=0):
        if self.level == 2: return self.compiled[n], self["frames"][n % len(self.img)]["time"]
        result = [[[0, 0, 0]]*self.sb.COLS for x in range(self.sb.ROWS)]
        total = len(self.img)
        ofs = self["start"] + self["step"]*(n // total) + self["frames"][n % total]["offset"]
        sz = self.size[n % total]
        if ofs >= self.sb.COLS: return result, self["frames"][n % total]["time"]
        for rn, r in enumerate(self.img[n % total]):
            result[rn][max(ofs, 0):min(ofs+sz[0], self.sb.COLS)] = r[max(-ofs, 0):min(self.sb.COLS-ofs, sz[0])]
        return result, self["frames"][n % total]["time"]

    def get_header(self, cycle=0):
        return self.header


