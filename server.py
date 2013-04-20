# Before editing:
#     1) View -> Uncheck "Print Layout"
#     2) Tools -> Preferences -> Uncheck "Use Smart Quotes"

from flask import Flask, request, render_template
import pickle, os

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/schedule/", methods=["POST"])
def schedule():
    print request.form
    return str(request.form)

if __name__ == "__main__":
    # Debug mode should be turned off when you are finished
    app.run(debug=True)
