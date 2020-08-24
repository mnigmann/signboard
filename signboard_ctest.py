#!/usr/bin/python3

#TODO: add animations: list of frames and the time and step for each


OUTPUT_TYPE = "DEBUG"
KEYBOARD = False

if OUTPUT_TYPE == "NEOPIXEL":
  import board
  import neopixel
import time
if KEYBOARD: import keyboard
import json 
from PIL import Image
import os
import os.path
import subprocess
import re
import sys
import traceback
#sys.stderr = open("/home/pi/signboard_err.log", 'w')
#sys.stdout = open("/home/pi/signboard.log", 'w')


if KEYBOARD: import keyboard_manager

drive_present = False
letters = None
WIDTH = None
HEIGHT = None
ROWS = None
COLS = None
LENGTH = None
objects = None
struc = None
settings = None
strip = None
images = None


letters_scaled = None
phrases_rendered = []

scale = 0
sHeight = 0
sWidth = 0

index = 0
object = 0
frame = None
mode = 0

lastkey = 0
keys = []
cursor = 0

root = re.search("^(.+)\/.+$", os.path.abspath(__file__)).group(1)


def fill(color):
  for x in range(ROWS):
    for y in range(COLS):
      setPixel(x, y, color)
      
      
if OUTPUT_TYPE == "NEOPIXEL":
  def show():
    strip.show()
else:
    def init(): pass
  

# (0,0) is at upper left, across then down
def setPixel(r, c, color, s=None):
  #if r==3 and c==0: print(r, c, color)
  if (r >= ROWS or c >= COLS or r < 0 or c < 0): return -1
  #c = COLS-c-1
  #r = ROWS-r-1
  i = int((2*COLS)-2+r+(2*(COLS-1)*((r-1)//2.0))+(c*(1-2*(r%2))))
  if i >= LENGTH: return
  (s or strip)[i] = color

"""def callback(evt): 
  lastkey = time.time() 
  if evt.name=="enter": 
  if evt.name=="backspace":
    keys.pop(cursor-1)
  if evt.name=="left":
    cursor = max(0, cursor-1)
  if evt.name=="right": 
    cursor = min(len(keys), cursor+1)
  else: 
    char = list(keyboard.get_typed_strings([evt]))[0]
    if char:
      keys.insert(cursor, char)
      cursor+=1
    

keyboard.on_press(callback)"""



def letter(s, offset, color, bg): 
  if -offset > sWidth or offset > COLS: return
  l = letters_scaled[s] if s in letters_scaled else letters_scaled["uc"]
  #print("showing", s, l)
  """for x in range(HEIGHT):
    for y in range(WIDTH):
      for a in range(settings['scale']):
        for b in range(settings['scale']):
          #strip[getIndex(ROWS-settings['scale']*HEIGHT+settings['scale']*x+a, settings['scale']*y+offset+b)]=color if l[x][y] else bg 
          setPixel(ROWS-settings['scale']*HEIGHT+settings['scale']*x+a, settings['scale']*y+offset+b, color if l[x][y] else bg)"""
  for x in range(sHeight):
    for y in range(sWidth):
        #print(x, y)
        setPixel(ROWS-sHeight+x, y+offset, color if l[x][y] else bg)

def display_text(s, offset, color, bg): 
  for i, x in enumerate(s): 
    letter(x.lower(), offset+settings['scale']*(WIDTH+1)*i, color, bg)


def display_image(img, offset): 
  data = images[img][0] 
  size = images[img][1]
  for r in range(size[1]): 
    for c in range(size[0]): 
      setPixel(ROWS-size[1]+r, c+offset, data[r][c])
      #if data[r][c] != (0,0,0): print(data[r][c])



def render(objects):
    phrases_rendered = []
    for i, object in enumerate(objects):
        print("REndering", i, object, object['type'])
        if object['type'] != 'phrase': 
            ### IMAGE ###
            if object['type'] == 'image':
                data = [[0,0,0]]*LENGTH
                h = images[object['path']][1][1]
                print("loading image", object['path'], h)
                for rn, r in enumerate(images[object['path']][0]):
                    for cn, c in enumerate(r):
                        setPixel(ROWS-h+rn, cn+object['startoffset'], list(c), data)
                phrases_rendered.append([data])
                continue
            ### ANIMATION ###
            elif object['type'] == 'animation':
                print("rendering an animation")
                frames = []
                for x in range(object['iterations']):
                    for y in object['frames']:
                        frm = [[0, 0, 0]]*LENGTH
                        h = images[y['path']][1][1]
                        for rn, r in enumerate(images[y['path']][0]):
                            for cn, c in enumerate(r):
                                setPixel(ROWS-h+rn, cn+object['start']+object['step']*x+y['offset'], list(c), frm)
                        frames.append(frm)
                phrases_rendered.append(frames)
                continue
            
            phrases_rendered.append(None)
            continue
        
        ### PHRASE ###
        phrases_rendered.append([])         # list of colors
        for color in object['colors']:
            phrases_rendered[i].append([])  # list of frames for that color
            index = object['offset']
            while True:
                currFrame = [color['background']]*LENGTH
                for ci, c in enumerate(object['phrase']):
                    l = letters_scaled[c] if c in letters_scaled else letters_scaled['uc']
                    offset = COLS-index+(ci*scale*(WIDTH+1))
                    if -offset > sWidth or offset > COLS: continue      #go to next letter
                    for x in range(sHeight):                            #render a letter
                        for y in range(sWidth):
                            setPixel(ROWS-sHeight+x, y+offset, color['color'] if l[x][y] else color['background'], currFrame)     #Set a pixel
                phrases_rendered[i][-1].append(currFrame)
                index += object['step']
                if index >= object.get("maxsteps", len(object["phrase"])*scale*(WIDTH+1)+COLS):
                    break
    print("finished rendering phrases")
    return phrases_rendered



def load(src = None, root=root):
  global letters, objects, WIDTH, HEIGHT, settings, ROWS, COLS, LENGTH, OUTPUT_TYPE, strip, images, struc, scale, sHeight, sWidth, letters_scaled, phrases_rendered
  src = src or "structure_ctest.json"
  with open(root+ "/"+src) as struc: 
    struc = json.load(struc)
    with open(root+"/"+struc['settings']['alphabet']) as l: 
      l = json.load(l)
      letters = l["letters"]
      objects = struc["objects"]
      WIDTH = l["width"]
      HEIGHT = l["height"]
      settings = struc["settings"] 
      ROWS = settings["rows"]
      COLS = settings["cols"]
      
      load_img = lambda x: ([list(x.getdata())[i*x.size[0]:(i+1)*x.size[0]] for i in range(x.size[1])], x.size)
      images = {obj["path"]: load_img(Image.open(root+"/images/"+obj["path"])) for obj in objects if obj["type"]=="image"}
      images.update({p['path']: load_img(Image.open(root+"/images/"+p['path'])) for obj in objects if obj['type']=='animation' for p in obj['frames']})
      if len(images) == 0:
        LENGTH = COLS*settings['scale']*HEIGHT
      else:      
        LENGTH = COLS*settings['scale']*max(HEIGHT, images[max(images, key=lambda x: images[x][1][1])][1][1])
      TEXTFILLLENGTH = COLS*settings['scale']*HEIGHT
      #print(neopixel, dir(neopixel))
      if OUTPUT_TYPE == "NEOPIXEL":
        strip = neopixel.NeoPixel(board.D18, LENGTH, auto_write=False, pixel_order=neopixel.GRB)                                                          # WARNING WARNIGN WARNING WARNING WARNING   CHANGE THIS BACK TO ROWS*COLS
      else:
        strip = [[0, 0, 0]]*LENGTH
        init()
      
      letters_scaled = {letter: 
        #for each letter
        [
          # for each row
          [col for col in row for b in range(settings['scale'])]
        for row in letters[letter] for a in range(settings['scale'])]
      for letter in letters}
      
      scale = settings['scale']
      sHeight = HEIGHT*scale
      sWidth = WIDTH*scale
      
      #print(images)
      print("Successfully loaded!")
      
      
      #Render the frames in advance
      #phrases_rendered = render(objects)
      
        
      

#load(root)
if KEYBOARD: keyboard_manager.root = root

def display(string, cursorpos, color, bg): 
  global mode
  mode = 1
  fill((0, 0, 0))
  display_text(string[:cursorpos]+"█"+string[cursorpos+1:], min(0, COLS - (WIDTH+1)*settings['scale']*(cursorpos+1)), color, bg)
  show()

def reset(): 
  global mode
  global index
  mode = 0
  index = 0
  
def set(x): objects = x

def save_objects():
  global struc
  with open(root+"/neopixel/structure_ctest.json", "w") as f:
    json.dump(struc, f, indent=2)
    print("saving")
    print(json.dumps(struc, indent = 2))

def onpress(evt):
  global object
  global index
  global objects
  if evt.name == "page up":
    object = (object+1)%len(objects)
    index = 0
  if evt.name == "page down":
    object = (object-1)%len(objects)
    index = 0
    

#keyboard_manager.displayfunc = display
#keyboard_manager.resetdisplayfunc = reset
#keyboard_manager.getfunc = lambda: objects
#keyboard_manager.getimages = lambda: images
#keyboard_manager.setfunc = set
#keyboard_manager.savefunc = save_objects
#keyboard_manager.onpressfunc = onpress

"""
def shutdown(channel):
    fill([0,0,0])
    show()
    GPIO.cleanup()
    keyboard_manager.cleanup()
    time.sleep(1)
    subprocess.call(['sudo', 'shutdown', '-h', 'now'])
"""

if __name__ == "__main__":

    time.sleep(5)
    try:
        i = subprocess.check_output(['ifconfig'])
        ip = re.search(b"wlan[\w\W]+?inet ([\d\.]+)  ", i).group(1).decode()
        length = len(ip)*(WIDTH+1)*settings['scale']+COLS
        print("The ip is", ip, type(ip), length)
        for current_index in range(0, length):
            fill([0, 0, 0])
            display_text(ip, COLS-current_index, [127, 127, 127], [0, 0, 0])
            show()
            time.sleep(0.02)
    except Exception as e: 
        print("Failed to find IP", e)


    #GPIO.setmode(GPIO.BCM)
    #GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    #GPIO.add_event_detect(4, GPIO.FALLING, callback=shutdown, bouncetime=300)



    try:
      #keyboard_manager.start()
      
      
      
      while True: 
        curr = objects[object]
        frame = 0
        if curr["type"] == "phrase" and mode==0: 
        
          """#print("Index: {}, before: {}".format(index, strip[getIndex(3, 0)]))
          #strip.fill(curr["background"])
          a = time.time()
          fill(curr['background'])
          
          b = time.time()
          display_text(curr["phrase"], COLS-index, curr["color"], curr["background"])

          c = time.time()
          strip.show()
          
          d = time.time()"""
          #print(object, index, len(phrases_rendered[object]))
          for i, x in enumerate(phrases_rendered[object][index]):
            strip[i] = x
          strip.show()
          
          index += curr["step"]
          if index == len(phrases_rendered[object]):
            object=object+1 if object+1 < len(objects) else 0 
            index = 0
          if settings['speed']: time.sleep(settings["speed"]/1000)
          
          #print("fill{:.5f} set{:.5f} show{:.5f} prep{:.5f}".format(b-a, c-b, d-c, time.time() - d))
          
          #print("after:", strip[getIndex(3, 0)])


        if curr["type"]=="image" and mode==0: 
          print("Displaying image", curr["path"])
          fill((0,0,0))
          origin = curr["startoffset"]
          display_image(curr["path"], origin) 
          show()
          time.sleep(curr["time"]/1000)
          object=(object+1)%len(objects)
          
        if curr["type"]=="animation" and mode==0:
          print("Displaying animation at index", object)
          fill((0,0,0))
          n = len(curr['frames'])
          frame = index%n
          currframe = curr['frames'][frame]
          print("The current frame is", currframe)
          display_image(currframe['path'], curr['start']+curr['step']*(index//n)+currframe['offset'])
          show()
          time.sleep(currframe['time']/1000)
          index += 1
          if index >= curr['step']*curr['iterations']:
            object=(object+1)%len(objects)
            index=0

        """
        if curr["type"]=="animation" and mode==0:
          if frame is None: frame=0 
          if index==0: index = curr["start"]
          display_image(curr["frames"][frame], index) 
          frame += 1
          index += curr["step"] if frame==len(curr["frames"]) else curr["framestep"] 
          frame %= len(curr["frames"])
          if (index >= curr["start"]+curr["length"] and curr["length"]>0) or (index <= curr["start"]+curr["length"] and curr["length "]<0): 
            frame = None
            index=0
            object=(object+1)%len(objects)"""
    except Exception as e: print("".join(traceback.format_exception(*sys.exc_info())))
    finally:
      fill((0, 0, 0))
      show()
      if KEYBOARD: keyboard_manager.cleanup()

      
