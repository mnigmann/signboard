import keyboard
import threading
import time
import re
from PIL import Image

displayfunc = None
resetdisplayfunc = None

getfunc = None
getimages = None
setfunc = None

savefunc = None
onpressfunc = None

root = ""

buffer = ""
cursor = 0
limit = 5
lastkey = 0

shift = False

shifted = {
  "−": "_",       # Warning: "−" != "-"
}

def onpress(evt):
  global buffer
  global cursor
  global lastkey
  
  if evt.name == "shift" or evt.name == "ctrl" or keyboard.is_pressed("ctrl") or evt.name.startswith("page"): return
  
  lastkey = time.time()
  key = list(keyboard.get_typed_strings([evt]))[0]
  if keyboard.is_pressed("shift"):
    print("shift pressed")
    if key in shifted: 
      key = shifted[key]
    key = key.upper()
  
  print(key, evt.name)
  
  
  if evt.name == "enter":
    if buffer.startswith("p "):
      _, idx, phr = buffer.split(" ", 2)
      idx = int(idx)
      print("setting phrase")
      obj = getfunc()
      obj[idx] = {
        "type": "phrase", 
        "phrase": phr, 
        "color": obj[idx]["color"] if ("color" in obj[idx]) else [255, 255, 255], 
        "background": obj[idx]["background"] if ("background" in obj[idx]) else [0, 0, 0], 
        "step": obj[idx]["step"] if ("step" in obj[idx] and obj[idx]["type"]=="phrase") else 1,
      }
    if buffer.startswith("pa "):
      _, idx, phr = buffer.split(" ", 2)
      idx = int(idx)
      print("adding phrase")
      obj = getfunc()
      if idx == -1: obj.append({})
      if idx >= 0: obj.insert(idx, {})
      if idx < -1: obj.insert(idx + 1, {})
      obj[idx] = {
        "type": "phrase", 
        "phrase": phr, 
        "color": [255, 255, 255], 
        "background": [0, 0, 0], 
        "step": 1,
      }
    elif buffer.startswith("pc "):
      print("setting color")
      _, idx, col = buffer.split(" ", 2)
      idx = int(idx)
      obj = getfunc()
      if obj[int(idx)]["type"] != "phrase": return
      obj[int(idx)] = {
        "type": "phrase", 
        "phrase": obj[int(idx)]['phrase'], 
        "color": [int(col[x:x+2], 16) for x in range(0, 6, 2)],
        "background": obj[int(idx)]["background"],
        "step": obj[int(idx)]["step"]
      }
    elif buffer.startswith("pb "):
      print("setting background")
      _, idx, col = buffer.split(" ", 2)
      idx = int(idx)
      obj = getfunc()
      if obj[int(idx)]["type"] != "phrase": return
      obj[int(idx)] = {
        "type": "phrase", 
        "phrase": obj[int(idx)]['phrase'], 
        "background": [int(col[x:x+2], 16) for x in range(0, 6, 2)],
        "color": obj[int(idx)]["color"],
        "step": obj[int(idx)]["step"]
      }
    elif buffer.startswith("i "):
      print("setting background")
      _, idx, path, disp, off = buffer.split(" ")
      
      img = getimages()
      load_img = lambda x: ([list(x.getdata())[i*x.size[0]:(i+1)*x.size[0]] for i in range(x.size[1])], x.size)
      img[path] = load_img(Image.open(root + "/neopixel/images/"+path))
      
      obj = getfunc()
      obj[int(idx)] = {
        "type": "image", 
        "path": path, 
        "time": int(disp),
        "startoffset": int(off)
      }
    elif buffer.startswith("ia "):
      print("addimg image")
      _, idx, path, disp, off = buffer.split(" ")
      idx = int(idx)
      
      img = getimages()
      load_img = lambda x: ([list(x.getdata())[i*x.size[0]:(i+1)*x.size[0]] for i in range(x.size[1])], x.size)
      img[path] = load_img(Image.open(root + "/neopixel/images/"+path))
      
      obj = getfunc()
      if idx == -1: obj.append({})
      if idx >= 0: obj.insert(idx, {})
      if idx < -1: obj.insert(idx + 1, {})
      obj[int(idx)] = {
        "type": "image", 
        "path": path, 
        "time": int(disp),
        "startoffset": int(off)
      }
      
    reset()
    return
  
  elif evt.name == "esc":
    reset()
  
  elif evt.name == "right":
    cursor += (cursor < len(buffer))
  elif evt.name == "left":
    cursor -= (cursor > 0)
  
  elif len(key):
    print("[key]")
    buffer = buffer[:cursor]+key+buffer[cursor:]
    cursor += (cursor < len(buffer))
  elif evt.name == "backspace":
    print("[backspace]")
    buffer = buffer[:cursor-1]+buffer[cursor:]
    cursor -= (cursor > 0)
  print("displaying", buffer[:cursor]+"█"+buffer[cursor+1:])
  
  pc = re.match("pc (\d+)", buffer)
  pcc = re.match("pc (\d+) ([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})", buffer)
  if pc and int(pc.group(1)) < len(getfunc()) and getfunc()[int(pc.group(1))]["type"] == "phrase":
    idx = int(pc.group(1))
    displayfunc(buffer, cursor, (int(pcc.group(2), 16), int(pcc.group(3), 16), int(pcc.group(4), 16)) if pcc else (255, 255, 255), getfunc()[idx]["background"])
    return
  
  pb = re.match("pb (\d+)", buffer)
  pbb = re.match("pb (\d+) ([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})", buffer)
  if pb and int(pb.group(1)) < len(getfunc()) and getfunc()[int(pb.group(1))]["type"] == "phrase":
    idx = int(pb.group(1))
    fg, bg = getfunc()[idx]["color"], (int(pbb.group(2), 16), int(pbb.group(3), 16), int(pbb.group(4), 16)) if pbb else (0, 0, 0)
    print("pb: displaying with", fg, bg)
    displayfunc(buffer, cursor, fg, bg)
    return
  
  displayfunc(buffer, cursor, [255, 255, 255], [0, 0, 0])


def reset():
  global buffer
  global lastkey
  global cursorpos
  
  print("clearing")
  resetdisplayfunc()
  buffer = ""
  lastkey = 0
  cursorpos = 0
  return


def onrelease(evt):
  global shift
  if evt.name == "shift":
    print("clearing shift")
    shift = False    


def reset_display():
  global limit
  global lastkey
  global buffer
  while True:
    if lastkey > 0 and time.time() - lastkey >= limit:
      print("closing", time.time(), lastkey, limit)
      reset()
      
    else:
      time.sleep(0.1)

def start():
  if displayfunc is not None and resetdisplayfunc is not None:
    keyboard.on_press(lambda evt: (onpress(evt), onpressfunc(evt)))
    keyboard.add_hotkey("ctrl+s", lambda: (savefunc(), reset()))
    thr = threading.Thread(target=reset_display)
    thr.start()
  
def cleanup():
  keyboard.unhook_all()