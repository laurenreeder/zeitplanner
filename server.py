# Before editing:
#     1) View -> Uncheck "Print Layout"
#     2) Tools -> Preferences -> Uncheck "Use Smart Quotes"

from flask import Flask, request, render_template
import pickle, os, data_scraper, scheduler

app = Flask(__name__)

course_data = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/schedule/", methods=["POST"])
def schedule():
    print course_list
    return str(request.form)

def validate(form):
    # List for the courses once they've been parsed
    course_list = []
    keys_of_invalid_inputs = []
    response = {}
    # Regex to match the data input from the form
    course_regex = r"(?P<dept>[A-Z]+)[^A-Z0-9]*(?P<course>\d+)[^A-Z0-9]*(?P<section>\d+)?"
    # Match the regex to every class in the input form
    for key in form.keys():
        course_input = form[key].upper().strip()
        match = re.match(course_regex, course_input)
        if match:
            # Retrieve department, course, and section information
            department_match = match.group("dept")
            course_match = match.group("course")
            if match.group("section"):
                section_match = match.group("section")
            # Validate
            department = course_data.get_department(department_match)
            if not department:
                keys_of_invalid_inputs.append(key)
                continue
            course = department.get_course(course_match)
            if not course:
                keys_of_invalid_inputs.append(key)
                continue
            if section_match:
                section = course.get_section(section_match)
                if not section:
                    keys_of_invalid_inputs.append(key)
                    continue
                else:
                    course_list.append(section)
            else:
                course_list.append(course)                
        else:
            keys_of_invalid_inputs.append(key)
    if keys_of_invalid_inputs:
        response["error"] = keys_of_invalid_inputs
        return response
    else:
        return course_list


if __name__ == "__main__":
    # Checks if the data file exists. If not, parses the data
    if not os.path.exists("course_data.pickle"):
        course_data = data_scraper.parse_course_data()
        pickle.dump(course_data, open("data.pickle", "w"))
    else:
        course_data = pickle.load(open("data.pickle", "r"))
    # Debug mode should be turned off when you are finished
    app.run(debug=True)
