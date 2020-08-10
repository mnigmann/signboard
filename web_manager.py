from flask import Flask, render_template, request, abort
from json import loads

app = Flask(__name__)

reload = lambda: None

@app.route("/", methods=["GET", "POST"])
def settings():
    fname = request.args.get("fname", "")
    if not fname: return """
<input type=text id=file>
<button onclick="window.location.href += '?fname=' + document.getElementById('file').value;">Go</button>
"""
    if fname.startswith("structure"):
        if request.form:
            print("FNAME IS", fname)
            try:
                with open(fname, "w") as f: 
                    f.write(request.form.get("json"))
                reload()
            except FileNotFoundError: return abort(404)

        if request.args:
            return render_template("settings.html")
        else: return """
<input type=text id=file>
<button onclick="window.location.href += '?fname=' + document.getElementById('file').value;">Go</button>
"""
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
def reload_signboard():
    reload()
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
