Python-based signboard driver
=============================

This repository contains a Python-based signboard driver that drives a 
Neopixel-based signboard. The code may be used from the command line as
a standalone program or may be imported into another Python program. 
When used as a standalone program, a web interface is also available, 
from which the configuration of the signboard may be modified.

## Configuration files
The configuration files for the signboard follow a format similar to
that of `structure_example.json`. Each file consists of a settings
section, which declares the size of the signboard, the alphabet file to
use, and a password for the web interface; and an objects section, which
declares the components of the signboard cycle. Each component, or 
**object**, may represent either a phrase, an image, or an animation.
An example of each is provided in the example file.

### Settings section
| Field | Description |
|:------|:------------|
|rows   |The number of rows in the signboard|
|cols   |The number of columns in the signboard|
|scale  |The scale factor to be used for the letters|
|alphabet|A JSON file describing the letters used when displaying a phrase. `letters.json` includes all the letters and some punctuation.|
|password|When modifying the file from the web interface, the user must enter this password to modify this file. May be set to the empty string.|


### Phrase
A phrase is a string that is scrolled from right to left across the
signboard. Multiple sets of foreground and background colors may be
defined. Each color will then be used for a certain number of full
cycles before the next one is selected

| Field | Description |
|:------|:------------|
|phrase |The phrase to be displayed|
|step   |The number of pixel the phrase moves between frames|
|speed  |The number of milliseconds between frames|
|offset |The number of pixels from the rightmost edge the phrase will appear in the first frame|

For the colors:

| Field | Description |
|:------|:------------|
|color  |The foreground color as a `[R, G, B]` array with each value between 0 and 255
|background|The background color as a `[R, G, B]` array with each value between 0 and 255
|duration|The number of cycles for which this color will be displayed|
### Image

| Field | Description |
|:------|:------------|
|path   |The filename of the image this object represents|
|time   |The number of milliseconds for which the image is displayed. Maximum is 65535 ms (a little over a minute)|
|startoffset|The number of pixels from the leftmost edge the image will appear|

### Animation
An animation consists of a series of images that may be played back in
a cycle. The horizontal offset of a frame, in pixels from the left, is
`offset+n*step`, where offset is the `offset` parameter of the frame,
step is the `step` parameter of the animation, and n is the index of the
current cycle of the animation

| Field | Description |
|:------|:------------|
|start  |The position, from pixels from the left, of the first frame of the animation|
|step   |The step between complete cycles of the animation|
|iterations|The number of complete cycles of the animation|

For the frames:

| Field | Description |
|:------|:------------|
|path   |The filename of the image|
|time   |The number of milliseconds for which the frame is displayed
|offset |The offset from the "base" offset|

### Defining new object types
New object types can be defined by subclassing the `SBObject` class.
The methods needed for this are described in the source code of
`SBObject`


### Note on images
All images must have no more rows than the signboard does and should be
located in the `images` folder. When using the serial output, the total
number of colors in any object may be no more than 16.

## Output methods
This software should make it easy define new output methods or object
types. By default, the signboard pixel data can be output via a serial
buffer, output via the GPIO of a Raspberry Pi, or displayed on-screen
with `opencv`. All of these methods can be implemented by creating an
instance of `signboard_main.SignboardSerial`, 
`signboard_main.SignboardNative`, or `signboard_cv2.SignboardCV2`.
Documentation of these classes can be found in the source code of
`signboard_main.SignboardLoader`

### Serial buffer
When run `signboard_main.py` is run from the command line (see below),
the serial buffer is used to communicate with the Neopixels. The serial
buffer may be made from any microcontroller, but a source file 
`signboard.ino` has been provided for using with an Arduino or a 
similar Arduino-compatible microcontroller (Teensy, etc.). The Arduino 
source file in this repository is written for use on a Teensy 4, but 
may be easily adapted by changing the `FastLED.addLeds` statement as 
needed. It may be possible to use this code on an Arduino, however, 
this hasn't been tested and may result in poor/slower performance. See 
the information at the top of `signboard.ino` for detailed information 
regarding the operation of the serial protocol.

### Direct GPIO output
To use the direct GPIO output on a Raspberry Pi, one must first install
the `ws281x` kernel module found 
[here](https://www.github.com/mnigmann/ws281x). This kernel module will
create a character device file at `/dev/ws281x` through which this
program will control the Neopixels. The `ws281x` kernel module can
drive multiple Neopixel strings in parallel like the `FastLed` library
for the Teensy. TODO: describe how to set channels

### `opencv` output
Output via `opencv` will display the pixels on screen instead of
on the signboard. This mode can be used for debugging or testing new
object types. This mode is implemented in a separate file so it can be
removed if it is not needed. To use this output mode, one must
additionally install `opencv-python` and `numpy`.

## Command line usage
```
usage: signboard_main.py [-h] [--file FILE] [--baud BAUD] [--port PORT]
                         [--recompile]

Load signboard data from file and output to signboard via serial buffer

optional arguments:
  -h, --help   show this help message and exit
  --file FILE  File containing signboard objects
  --baud BAUD  Baud rate for serial connection. Default is 4000000.
               This is not important if a Teensy is connected, as they
               use USB rather than a serial connection
  --port PORT  Serial port of the serial buffer
  --recompile  Recompile all objects every time. Only for debugging
```


## Web interface
When the program is run from the command line, a web interface is
started on `0.0.0.0`, making it available to the entire network. The
web interface may be accessed on port 5000. To use it, select the file
from the dropdown menu, enter the password, and click "Go". All the 
parameters for the objects may be accessed. Additionally, new objects,
frames, or colors may be added or deleted.

When changing the file currently running on the signboard, the website
will ask for the password for the previous file.

The file `secret_key.py` contains a single variable `FLASK_SECRET_KEY`
that contains a binary string. At runtime, its value is stored to 
`app.secret_key`. This file is not included in the repo.

## Use in a Python program
To allow more advanced control over the sequence of objects on the
signboard, you can import `signboard_main` into your program and 
create an instance of its `SignboardSerial` or `SignboardNative`
classes. Use the class' `load` function to open a configuration file. 
Use the class' `run_object` function to display one object. The load 
function may be safely called from a different thread while an object 
is running on the signboard. If this occurs, the `run_object` function 
will return False.

## Note on files
Not all files in this repository are necessary for the operation of
this signboard. When called from the command line, 
`serial_speedtest_ctest_multithread.py`, 
`serial_speedtest_ctest_optimized.py`, and `signboard_main.py` are
identical. `serial_speedtest_ctest_multithread.py` is an earlier version
of `serial_speedtest_ctest_optimized.py`, which is an earlier version
of `signboard_main.py` The directory `lcd` and any files with `lcd` or
`ui` or `keyboard` in the title are not necessary for the operation of
the signboard.


## Sample configurations
```
    0>->->->->->->->->->->->->->->->->->->->\
    /<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-</
    \>->->->->->->->->->->->->->->->->->->->\
    /<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-</
    \>->->->->->->->->->->->->->->->->->->->\
    /<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-</
    \>->->->->->->->->->->->->->->->->->->->
    1>->->->->->->->->->->->->->->->->->->->\
    /<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-</
    \>->->->->->->->->->->->->->->->->->->->\
    /<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-</
    \>->->->->->->->->->->->->->->->->->->->\
    /<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-</
    \>->->->->->->->->->->->->->->->->->->->
    where 0 and 1 are the starts of strings 0 and 1 respectively
serialization: [1, -1, 1, -1, 1, -1, 1]


    0>->->->->->->->->->->->->->->->->->->->\
    /<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-</
    \>->->->->->->->->->->->->->->->->->->->\
    /<-<-<-<-<-<-<-<-<-<1<-<-<-<-<-<-<-<-<-</
    \>->->->->->->->->->->->->->->->->->->->\
    /<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-</
    \>->->->->->->->->->->->->->->->->->->->
    2>->->->->->->->->->->->->->->->->->->->\
    /<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-</
    \>->->->->->->->->->->->->->->->->->->->\
    /<-<-<-<-<-<-<-<-<-<3<-<-<-<-<-<-<-<-<-</
    \>->->->->->->->->->->->->->->->->->->->\
    /<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-<-</
    \>->->->->->->->->->->->->->->->->->->->
    where 0, 1, 2, and 3 are the starts of strings 1, 2, 3, and 4 respectively
serialization: [1, -1, 1, -1, 1, -1, 1]
                    
```