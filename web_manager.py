from flask import Flask, render_template, request, abort, session, redirect, send_file
from json import loads, load, dumps
import os
from werkzeug.utils import secure_filename
import secret_key

root = ""
compiling = False

app = Flask(__name__)

app.secret_key = secret_key.FLASK_SECRET_KEY

reload = lambda: None

@app.route("/", methods=["GET", "POST"])
def main():
    file = request.form.get("file", "")
    if file:
        pw = request.form.get("password", "")
        print(file, pw)
        try:
            with open(os.path.join("structure", file)) as f:
                cpw = load(f)['settings'].get('password', None)
                if cpw is None or cpw == pw:
                    if 'authorized' not in session: session['authorized'] = "[]"
                    auth = loads(session['authorized'])
                    auth.append(file)
                    session['authorized'] = dumps(auth)
                    return redirect("/openfile?fname="+file)
        except Exception as e: print(e)
    
    files = [x for x in os.listdir(os.path.join(root, "structure")) if x.endswith(".json")]

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

    if fname.endswith(".json"):
        fname = os.path.join("structure", fname)
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

@app.route("/images", methods=["GET", "POST"])
def images():
    if len(loads(session["authorized"])) == 0: return redirect("/")
    if request.method == "POST":
        try:
            if "delid" in request.form:
                os.remove(root + "/images/" + sorted(os.listdir(root + "/images/"))[int(request.form['delid'])])
            else:
                if "file" not in request.files: return redirect("/images")
                file = request.files["file"]
                if file.filename == "" or "." not in file.filename or file.filename.split(".")[-1]!="png": return redirect("/images")
                print("File received", file.filename)
                filename = secure_filename(file.filename)
                file.save(root + "/images/" + filename)
        except Exception as e: print(e)
    return render_template("images.html", files=sorted(os.listdir(root+"/images/")))

@app.route("/images/<string:file>")
def get_image(file):
    return send_file(root+"/images/"+file)
        
    
@app.route("/getfile")
def struc():
    fname = request.args.get("fname", "")
    if fname.endswith(".json"):
        fname = os.path.join("structure", fname)
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
