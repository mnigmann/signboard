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
        self.running = True

    def run_object(self, obj: sb_object.SBObject, cycle=0):
        """
        Display one object on the signboard
        :param obj: The index of the object to be run
        :param cycle: The current cycle. This is used for selecting the colors of phrases
        :return: None
        """
        for i in range(obj.get_n_frames(cycle)):
            img, t = obj.get_frame(i, cycle)
            cv2.imshow("img", cv2.resize(numpy.uint8(img), (self.COLS*10, self.ROWS*10), interpolation=cv2.INTER_NEAREST)[:, :, ::-1])
            cv2.waitKey(t)
        return True

    def close(self):
        pass
