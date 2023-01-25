from PIL import Image
import os


class SBObject:
    def __init__(self, obj, sb):
        self.obj = obj
        self.sb = sb
        pass

    def get_n_frames(self, cycle=0):
        pass

    def get_frame(self, n, cycle=0):
        pass

    def prepare(self, level):
        pass

    def __getitem__(self, item):
        return self.obj[item]


class PhraseObject(SBObject):
    def __init__(self, obj, sb, alphabet):
        self.alphabet = alphabet
        self.color_cumsum = []
        self.full = []
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
        if level == 1:
            sWidth = self.sb.scale*(self.sb.WIDTH+1)
            self.full = [[0]*sWidth*len(self["phrase"]) for i in range(self.sb.ROWS)]
            for ci, c in enumerate(self["phrase"]):
                l = self.alphabet.get(c, self.alphabet['uc'])
                for rn, r in enumerate(l):
                    #print(rn, ci*self.sb.sWidth, (ci+1)*self.sb.sWidth, len(self.full[0]))
                    self.full[rn][ci*sWidth:(ci+1)*sWidth] = r

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


class ImageObject(SBObject):
    def __init__(self, obj, sb):
        self.img = None
        self.size = None
        super().__init__(obj, sb)

    def load_img(self, img):
        size = img.size
        data = img.getdata()
        return [list(data)[i * size[0]:(i + 1) * size[0]] for i in range(size[1])], size

    def prepare(self, level):
        if level >= 0:
            self.img, self.size = self.load_img(Image.open(os.path.join("images", self["path"])))

    def get_n_frames(self, cycle=0):
        return 1

    def get_frame(self, n, cycle=0):
        result = [[[0, 0, 0]]*self.sb.COLS for x in range(self.sb.ROWS)]
        ofs = self["startoffset"]
        if ofs >= self.sb.COLS: return result, self["time"]
        for rn, r in enumerate(self.img):
            result[rn][max(ofs, 0):min(ofs+self.size[0], self.sb.COLS)] = r[max(-ofs, 0):min(self.sb.COLS-ofs, self.size[0])]
        return result, self["time"]


class AnimationObject(SBObject):
    def __init__(self, obj, sb):
        self.img = []
        self.size = []
        super().__init__(obj, sb)

    def load_img(self, img):
        size = img.size
        data = img.getdata()
        return [list(data)[i * size[0]:(i + 1) * size[0]] for i in range(size[1])], size

    def prepare(self, level):
        if level >= 0:
            self.img = []
            self.size = []
            for x in self["frames"]:
                i, s = self.load_img(Image.open(os.path.join("images", x["path"])))
                self.img.append(i)
                self.size.append(s)

    def get_n_frames(self, cycle=0):
        return self["iterations"]*len(self["frames"])

    def get_frame(self, n, cycle=0):
        result = [[[0, 0, 0]]*self.sb.COLS for x in range(self.sb.ROWS)]
        total = len(self.img)
        ofs = self["start"] + self["step"]*(n // total) + self["frames"][n % total]["offset"]
        sz = self.size[n % total]
        if ofs >= self.sb.COLS: return result, self["frames"][n % total]["time"]
        for rn, r in enumerate(self.img[n % total]):
            result[rn][max(ofs, 0):min(ofs+sz[0], self.sb.COLS)] = r[max(-ofs, 0):min(self.sb.COLS-ofs, sz[0])]
        return result, self["frames"][n % total]["time"]


