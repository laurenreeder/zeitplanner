# Before editing:
#     1) View -> Uncheck "Print Layout"
#     2) Tools -> Preferences -> Uncheck "Use Smart Quotes"

from functools import wraps
from flask import current_app, Flask, jsonify, request, render_template
import pickle, os, re

import data_scraper, scheduler

app = Flask(__name__)

COURSE_DATA = None

# JSONP wrapper from https://gist.github.com/farazdagi/1089923
def support_jsonp(f):
    """Wraps JSONified output for JSONP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            content = str(callback) + '(' + str(f().data) + ')'
            return current_app.response_class(content, mimetype='application/json')
        else:
            return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/schedule/", methods=["GET"])
@support_jsonp
def schedule():
    import sys
    sys.stderr.write("%s\n" % str(request.args))
    sys.stderr.write("Classes: %s\n" % str(request.args["classes"]))
    class_dict = {}
    for class_string in request.args.getlist("classes"):
    	sys.stderr.write("Class string is: %s\n" % class_string)
    	key, value = class_string.split(":")
    	class_dict[key] = value
    validate_response = validate(class_dict)
    if "error" in validate_response:
        return jsonify(validate_response)
    else:
        course_list = validate_response["result"]["courses"]
        section_list = validate_response["result"]["sections"]
        schedules = scheduler.find_schedules(course_list, section_list)
        # Return rendered template
        return jsonify({"result": "Classes are valid."})

def validate(class_dict):
    """Returns {result: {courses : [c1, c2, ...], sections: [s1, s2, ...]}} for
       the given form data if all inputs are valid, or returns {error:
       [key_of_invalid_input_1, key_of_invalid_input_2, ...]} if not."""

    # List of parsed courses
    course_list = []

    # List of parsed sections
    section_list = []

    # List of keys whose inputs are invalid
    keys_of_invalid_inputs = []

    # Response dictionary
    response = {}

    # Course pattern on which the form inputs are matched
    course_pattern = r"(?P<dept>[A-Z]+)" + \
                     r"[^A-Z\d]*(?P<course>\d+)" + \
                     r"[^A-Z\d]*(?P<section>\d+)?"

    # For each input field, parse it and add it to the course list if it is
    # valid, or add its key to the list of invalid input keys if not
    for key in class_dict:

        # Retrieve the form input for the current key, then strip whitespace
        # from either end and convert all letters to uppercase
        course_input = class_dict[key].strip().upper()

        # Match the input field against the course_pattern
        match = re.match(course_pattern, course_input)

        # If the input field matches the course_pattern
        if match:

            # Extract department, course, and section information from the input
            department_match = match.group("dept")
            course_match = match.group("course")
            section_match = None
            if match.group("section"):
                section_match = match.group("section")

            # Check if the specified course or section is in the course data

            # Check the validity of the department
            department = COURSE_DATA.get_department(department_match)
            if not department:
                keys_of_invalid_inputs.append(key)
                continue

            # Check the validity of the course code
            course = department.get_course(course_match)
            if not course:
                keys_of_invalid_inputs.append(key)
                continue
            
            # If a section was specified, check the validity of the section
            if section_match:
                section = course.get_section(section_match)
                if not section:
                    keys_of_invalid_inputs.append(key)
                    continue

                # If the section was valid, add it to the section list
                else:
                    section_list.append(section)

            # If no section was specified, add the course to the course list
            else:
                course_list.append(course)

        # If the input field does not match the course_pattern, add the current
        # key to the list of invalid input keys
        else:
            keys_of_invalid_inputs.append(key)

    # If any inputs were invalid, return a response containing the keys of the
    # invalid inputs
    if keys_of_invalid_inputs:
        response["error"] = keys_of_invalid_inputs

    # Otherwise, return the course list
    else:
        response["result"] = {"courses": course_list, "sections": section_list}

    return response


if __name__ == "__main__":

     # Check if the data file already exists
    # If not, scrape the course data and store it locally
    if not os.path.exists("course_data.pickle"):
        COURSE_DATA = data_scraper.parse_course_data()
        pickle.dump(COURSE_DATA, open("course_data.pickle", "w"))

    # Otherwise, load the course data
    else:
        COURSE_DATA = pickle.load(open("course_data.pickle", "r"))

    # Set the global COURSE_DATA object in the scheduler module to the
    # server's COURSE_DATA object
    scheduler.COURSE_DATA = COURSE_DATA

    # Debug mode should be turned off when you are finished
    app.run(debug=True)
