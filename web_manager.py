from flask import Flask, render_template, request, abort, session, redirect
from json import loads, load, dumps
import os

root = ""
compiling = False

app = Flask(__name__)

app.secret_key = b'+\x07\x1a\xe8\xc8\x14;\x13\x8fl(\x04\x7f\xe0P}\xb7\xbb9y'

reload = lambda: None

@app.route("/", methods=["GET", "POST"])
def main():
    file = request.form.get("file", "")
    if file:
        pw = request.form.get("password", "")
        print(file, pw)
        with open(file) as f:
            cpw = load(f)['settings'].get('password', None)
            if cpw is None or cpw == pw:
                if 'authorized' not in session: session['authorized'] = "[]"
                auth = loads(session['authorized'])
                auth.append(file)
                session['authorized'] = dumps(auth)
                return redirect("/openfile?fname="+file)
    
    files = list(filter(lambda f: f.startswith("structure") and f.endswith(".json"), os.listdir(root)))

    return render_template("index.html", files=files)
    return """
<form method=post>
    <input type=text id=file name=file></br>
    <input type=password id=pw name=password></br>
    <button>Go</button>
</form>
"""



@app.route("/openfile", methods=["GET", "POST"])
def openfile():
    global compiling
    fname = request.args.get("fname", "")
    if not fname: return redirect("/")
    if fname not in loads(session['authorized']): return redirect("/")

    if fname.startswith("structure"):
        if request.form:
            use_reload = request.form.get("reload", "0")=="1"
            print("FNAME IS", fname)
            try:
                with open(fname, "w") as f: 
                    f.write(request.form.get("json"))
                if use_reload and not compiling:
                    compiling = True
                    reload(fname)
                    compiling = False
            except FileNotFoundError: return abort(404)

        if request.args:
            return render_template("settings.html")
        else: return redirect("/")
    else: 
        print("Unauthorized")
        return abort(403)
    
@app.route("/getfile")
def struc():
    fname = request.args.get("fname", "")
    if fname.startswith("structure"):
        try:
            with open(fname) as f:
                return f.read()
        except FileNotFoundError:
            return abort(404)
    else: return abort(403)

@app.route("/reload")
@app.route("/reload/<url>")
def reload_signboard(url=None):
    if url is not None: reload(url)
    else: reload()
    print("Reload request received")

@app.route("/jscolor.js")
def jscolor():
    return render_template("jscolor.js")

@app.route("/jquery.js")
def jquery():
    return render_template("jquery.js")
        

def run():
    app.run(host="0.0.0.0", port=5000)
    
if __name__ == "__main__":
    run()
