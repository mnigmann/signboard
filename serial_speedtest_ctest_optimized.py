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

import signboard_ctest_multithread as signboard

import serial
#import RPi.GPIO as GPIO
import os
import sys
import math
import time
import hashlib
import base64
import web_manager
import threading
import multiprocessing
import re
import json
from PIL import Image
#import lcd_keyboard_manager as lcd_key

arg = " ".join(sys.argv)
ser = None
baud = 4000000
web_manager.root = signboard.root
running = True

# Regexes match the argument name followed by a string containing non-space characters, except when escaped with a backslash

filename = re.search(r"--file ((?:\\ |[^ \n])+)", arg)
if filename is None: 
    print("Please specify structure file using --file argument")
    exit()
else: filename = filename.group(1)

portname = re.search(r"--port ((?:\\ |[^ \n])+)", arg)
if portname is None: portname = ""
else: portname = portname.group(1)

current_file = filename
recompile = "--recompile" in sys.argv

def setPixel(r, c):
  #if r==3 and c==0: print(r, c, color)
  if (r >= signboard.ROWS or c >= signboard.COLS or r < 0 or c < 0): return -1
  #c = COLS-c-1
  #r = ROWS-r-1
  i = int((2*signboard.COLS)-2+r+(2*(signboard.COLS-1)*((r-1)//2.0))+(c*(1-2*(r%2))))
  if i >= signboard.LENGTH: return -1
  return i


def color2bytes(x):
    b = bytearray("   ", "utf-8")
    b[0] = int((x>>16)&255)
    b[1] = int((x>>8) &255)
    b[2] = x & 255
    return b


def compile_frame(frame, col, dtime):
    return bytearray([int(dtime>>8), dtime&255]) + b"".join([ bytearray([(col.index(frame[x])<<4) + (0 if len(frame)==x+1 else col.index(frame[x+1]))]) for x in range(0, len(frame), 2) ])


def compile_one(index, obj, pcol, images, begin, end):
    """
    Compiles a certain range of frames.
    
    index:  the index of the current object
    obj:    the current object
    pcol:   the colors used in the object
    images: the image data (if needed) for this object
    begin:  the frame to start with
    end:    the frame th end with
    """
    global p
#    start_time = time.time()
#    print("Starting compile for", index, begin, end)
    pfrms = []
    t = obj['type']
    #print("First LED value", obj[0][0], pcol.index(obj[0][0]))
    #print(compile_frame(obj[0][:10], pcol, 2))
    if t=='phrase':
        sWidth = signboard.settings['scale']*signboard.WIDTH
        sHeight = signboard.settings['scale']*signboard.HEIGHT
        try:
          for frm_idx in range(begin, end):
            data = bytearray([0x22]*signboard.ROWS*signboard.COLS)
            for ci, c in enumerate(obj['phrase']):
                l = signboard.letters_scaled.get(c, signboard.letters_scaled['uc'])
                offset = signboard.COLS-frm_idx+(ci*signboard.settings['scale']*(signboard.WIDTH+1))
                if -offset > sWidth or offset > signboard.COLS: continue
                for x in range(sHeight):
                    for y in range(sWidth):
                        p = setPixel(signboard.ROWS-sHeight+x, y+offset)
                        if p == -1: continue
                        data[int(p/2)] = data[int(p/2)] & (0xf0 if p%2 else 0x0f) | ((1 if l[x][y] else 2) << (0 if p%2 else 4))
            pfrms.append(bytearray([int(obj['speed']>>8), obj['speed']&255]) + data)
        except Exception as e: print(e)
    elif t=='image':
        i = images[obj['path']]
        data = bytearray([pcol.index((0,0,0))]*signboard.LENGTH)
        for rn, r in enumerate(i[0]):
            for cn, c in enumerate(r):
                p = setPixel(signboard.ROWS-i[1][1]+r, cn+obj['startoffset'])
                if p == -1: continue
                data[int(p/2)] = data[int(p/2)] & (0xf0 if p%2 else 0x0f) | (pcol.index(c) << (0 if p%2 else 4))
        pfrms.append(bytearray([int(obj['displaytime']>>8), obj['displaytime']&255]) + data)
    else:
        for x in range(obj['iterations']):
            for iy, y in enumerate(obj['frames']):
                if not begin <= (anim_frames*x+iy) < end: continue
                frm = bytearray([pcol.index((0,0,0))]*LENGTH)
                h = images[y['path']][1][1]
                for rn, r in enumerate(images[y['path']][0]):
                    for cn, c in enumerate(r):
                        p = setPixel(signboard.ROWS-h+rn, cn+obj['start']+obj['step']*x+y['offset'])
                        if p == -1: continue
                        frm[int(p/2)] = data[int(p/2)] & (0xf0 if p%2 else 0x0f) | (pcol.index(c) << (0 if p%2 else 4))
                pfrms.append(bytearray([int(y['time']>>8), y['time']&255]) + frm)

    return (index, pfrms, t, slice(begin,end))
#    p[index] = pfrms
#    print("Finishing compile for", index, begin, len(pfrms), len(pfrms[0]))


def apply_results(args):
    index, pfrms, t, s_range = args
    global p
    p[index][s_range]=pfrms


def compile_frames(objs, comp_fname, fname):
    global p
    global headers

    #check if previous data is available
    v = os.listdir()
    headers = [None if x['type']!='phrase' else [None]*sum(y['duration'] for y in x['colors']) for x in objs]; p = [[]]*len(objs)
    dont_render = []
    print(p)    


    if recompile: 
        print("Forced recompile")
    elif comp_fname in v:
        print("version found")
        with open(comp_fname) as f:
            j = json.load(f)
            if len(j) == len(objs):
                for obj_index, obj in enumerate(j):
                    h_n = hashlib.md5()
                    h_n.update(json.dumps(objs[obj_index], sort_keys=True).encode())
                    this = objs[obj_index]
                    if h_n.hexdigest() == obj['hash'].strip():
                        print("version found with matching hash for object", obj_index)
                        headers[obj_index] = (eval(base64.b64decode(obj['header'].encode()).decode()))
                        p[obj_index] = (eval(base64.b64decode(obj['frames'].encode()).decode()))
                        print(obj['header'], base64.b64decode(obj['header'].encode()).decode())
                        dont_render.append(obj_index)
                    else:
                        print("hashes do not match for {}: old={} and new={}".format(obj_index, obj['hash'].strip(), h_n.hexdigest()))
                    
             
    


#    rendered = signboard.render(objs, dont_render)
#    p_in = list(filter(lambda x: x is not None, rendered))

    slen = signboard.ROWS*signboard.COLS
    print("size of the signboard", slen)


    obj2colors = lambda obj: list(map(list, set(map(tuple, (col for frm in obj for col in frm)))))

    print("Before compiling", [bool(x) for x in p])

    load_img = lambda x: ([list(x.getdata())[i*x.size[0]:(i+1)*x.size[0]] for i in range(x.size[1])], x.size)
    
    comp_start = time.time()
   
    for index, obj in enumerate(objs):
        if bool(p[index]) and bool(p[index][0]): 
            print("Skipping compile for", index)
            continue
        t = obj['type']
        
        # "images": contains image/animation data
        images = []
        if t == 'image': images = {obj["path"]: load_img(Image.open(os.path.join(signboard.root, "images/", obj["path"])))}
        if t == 'animation': images = {p['path']: load_img(Image.open(os.path.join(signboard.root, "images/", p['path']))) for p in obj['frames']}
        
        # "pcol": contains the colors used the in the object
        if t != 'phrase': 
            pcol = [-1]
            for x in images:
                [pcol.append(c) for r in images[x][0] for c in r if c not in pcol]
        else: pcol = [-1] + [c for pattern in obj['colors'] for c in [pattern["color"], pattern["background"]]]
#        print("The colors are", pcol)

        # "nfrms": contains the exact number of frames in the final compilation
        if t == "phrase": nfrms = signboard.COLS + signboard.settings['scale']*(signboard.WIDTH+1)*len(obj['phrase'])
        elif t == "animation": nfrms = obj['iterations']*len(obj['frames'])
        else: nfrms = 1

        
        phead = bytearray([int(nfrms>>8), nfrms&255, int(slen>>8), slen&255])
        if t != "phrase": headers[index] = phead + b"".join(bytearray(col) for col in pcol[1:])
        else: headers[index] = [phead + bytearray(c["color"]) + bytearray(c["background"]) for c in obj['colors']]
#        print("Header is", headers[index])
       
        # Put in blank frames
        p[index] = [None]*nfrms


        new_threads = []

        pool = multiprocessing.Pool()
        
#        print("Starting threads for", index, t, nfrms)
        if nfrms <= 50:
            pool.apply_async(compile_one, args=(index, obj, pcol, images, 0, nfrms), callback=apply_results)
        elif nfrms <=200:
            n_proc = 0
            while n_proc < nfrms:
#                print("starting thread", nproc)
                pool.apply_async(compile_one, args=(index, obj, pcol, images, n_proc, n_proc+50), callback=apply_results)
                n_proc += 50
        else:
            nper = nfrms // 4 + 1
            for x in range(4):
                pool.apply_async(compile_one, args=(index, obj, pcol, images, nper*x, nper*x+nper), callback=apply_results)
        pool.close()
        pool.join()
        print("Finished", index)
#        if t=="phrase": print(index, len(p[index][0]), len(list(filter(lambda x:x is not None, p[index][0]))))
#        else: print(index, len(p[index]))
    print("All threads terminated in", time.time() - comp_start)

        
    with open(comp_fname, "w") as f:
        f.write("[\n")
        for i in range(len(objs)):
            object_hash = hashlib.md5()
            object_hash.update(json.dumps(objs[i], sort_keys=True).encode())
            print("Saving with hash {} for {}".format(object_hash.hexdigest(), i))

            if i != 0: f.write(",\n")
            f.write('    {\n        "hash": "%s",\n' % (object_hash.hexdigest()))
            f.write('        "header": "{}",\n'.format(base64.b64encode(str(headers[i]).encode()).decode()))
            f.write('        "frames": "{}"\n'.format(base64.b64encode(str(p[i]).encode()).decode()))
            f.write("    }")
        f.write("\n]\n")

    print("After compiling", [bool(x) for x in p], [(i, len(x)) for i, x in enumerate(p) if isinstance(x, list)]) 
    
    
        



def reload(f=current_file):
    global p, headers, objs, numObjects, currObject, numFrames, currFrame, ser, running
    running = False
    if ser is not None: ser.write(b"\xff\xff\xff\x00")
    signboard.load(f)
    objs = signboard.objects
    compile_frames(objs, "active_optimized.compiled", f)
    numObjects = len(p)
    currObject = -1
    numFrames = 1
    currFrame = 0
    current_file = f
    running = True

if __name__ == "__main__":
    reload()
    web_manager.reload = reload

    threading.Thread(target=web_manager.run).start()

    #lcd_key.reload_callback = reload    

    currCycle = 0

    numObjects = len(p)
    currObject = -1

    numFrames = 1
    currFrame = 0

    print(len(signboard.phrases_rendered))
    print("num objects: {}".format(numObjects))


    """
    def send(c):
        global ser, v, cc, hcc
        if GPIO.input(22):
            # data
            ser.write(chr(comp[cc]).encode())
            cc+=1
        else:
            # header
            ser.write(chr(hlen+hcc).encode()+header[hcc*63:(hcc+1)*63])
            hcc+=1	#TODO: finish chunk generator
    """

    if portname == "": 
        print("Please specify port name with --port argument")
        exit()

    while ser is None:
        try:
            ser = serial.Serial(portname, baudrate=baud)
        except Exception as e:
            print("Error ocurred: "+str(e))
            time.sleep(1)
    ser.flushInput()
    ser.flushOutput()

    headerSent = False

    lastHeaderSent = 0 


    try:
        print("Sending interrupt frame")
        ser.write(b'\xff\xff\xff\x00')
        while True:
            if not running: continue
            v = ser.read()
#            print(v)
            if v == b"H": 
                currObject+=1
                if currObject == numObjects: 
                    currObject = 0
                    currCycle += 1
                
                numFrames = len(p[currObject]) \
                                if objs[currObject]['type']!='phrase' \
                                else len(p[currObject][0])
                currFrame = 0                       # just to be safe
                headerSent = True
                ser.write(headers[currObject])
                print("\n LOADING", currObject)
#                print(numFrames, "num frames recvd", ser.readline())
#                print("colors", ser.readline())
#                print('time since last header', time.time() - lastHeaderSent)
                lastHeaderSent = time.time()
                
                
                
                
            if v == b"F": 
                if headerSent: 
                    if objs[currObject]['type']!='phrase': ser.write(p[currObject][currFrame])
                    else:
                        v = p[currObject]
                        ser.write(v[currCycle%len(v)][currFrame])
                        #print("writing color", currCycle%len(v))
                    print("\rServing frame "+str(currFrame)+"/"+str(numFrames), end="")
                else:
                    print("Sending interrupt frame")
                    ser.write(b"\xff\xff\xff\x00")      # interrupt frame
#                    print("received", ser.readline())
                #print("curr frame", currFrame)
                #print("curr object", currObject)
                #print(p[currObject-1][currFrame])
                #print("current frame recvd", ser.readline())
                #print("status", ser.readline())
#                if currObject == 0 and currFrame == 50: 
#                    print(len(p[0]))
#                    print(p[currObject][currCycle%len(p[currObject])][currFrame])
                currFrame = (currFrame + 1) % numFrames
            #print(v)
            #print("-----------------------------------")
    finally:
        ser.close()
    
