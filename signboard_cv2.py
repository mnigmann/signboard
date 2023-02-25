import sb_object
from signboard_main import SignboardLoader
import cv2
import time
import numpy


class SignboardCV2(SignboardLoader):
    def __init__(self):
        self.running = True
        self.headerSent = False
        super().__init__()

    def load(self, src, comp_file=None, root=None, force=False):
        self.running = False
        time.sleep(0.2)         # after disabling, wait for program to reach "breakpoint"
        super().load(src, comp_file, root, force, level=1)
        self.running = True

    def run_object(self, obj: sb_object.SBObject, cycle=0):
        i = 0
        n = obj.get_n_frames(cycle)
        while i < n:
            if not self.running: return False
            img, t = obj.get_frame(i, cycle)
            if img is None:
                print("get_frame returned None")
                return True
            cv2.imshow("img", cv2.resize(numpy.uint8(img), (self.COLS*10, self.ROWS*10), interpolation=cv2.INTER_NEAREST)[:, :, ::-1])
            cv2.waitKey(t)
            i += 1
        return True

    def close(self):
        pass
