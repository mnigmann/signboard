import signboard_main

if __name__ == "__main__":
    sign = signboard_main.SignboardNative("/dev/ws281x")
    sign.load("structure/structure_tetris.json")
    sign.init([12, 14], 160)

    try:
        while True:
            for x in sign.sb_objects: sign.run_object(x)
    finally:
        sign.close()
