# Before editing:
#     1) View -> Uncheck "Print Layout"
#     2) Tools -> Preferences -> Uncheck "Use Smart Quotes"

from flask import Flask, jsonify, request, render_template
import pickle, os, re

import data_scraper, scheduler

app = Flask(__name__)

course_data = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/schedule/", methods=["POST"])
def schedule():
    validate_response = validate(request.form)
    if "error" in validate_response:
    	return jsonify(validate_response)
    else:
    	return "Input %s was valid." % (str(request.form))

def validate(form):

    # List of parsed courses
    course_list = []

    # List of keys whose inputs are invalid
    keys_of_invalid_inputs = []

    # Response dictionary
    response = {}

    # Course pattern on which the form inputs are matched
    course_pattern = r"(?P<dept>[A-Z]+)" + \
                     r"[^A-Z0-9]*(?P<course>\d+)" + \
                     r"[^A-Z0-9]*(?P<section>\d+)?"

    # For each input field, parse it and add it to the course list if it is
    # valid, or add its key to the list of invalid input keys if not
    for key in form.keys():

    	# Retrieve the form input for the current key, then strip whitespace
    	# from either end and convert all letters to uppercase
        course_input = form[key].strip().upper()

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
            department = course_data.get_department(department_match)
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

                # If the section was valid, add it to the course list
                else:
                    course_list.append(section)

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
        response["result"] = course_list

    return response


if __name__ == "__main__":

    # Check if the data file already exists

    # If not, scrape the course data and store it locally
    if not os.path.exists("course_data.pickle"):
        course_data = data_scraper.parse_course_data()
        pickle.dump(course_data, open("course_data.pickle", "w"))

    # Otherwise, load the course data
    else:
        course_data = pickle.load(open("course_data.pickle", "r"))

    # Debug mode should be turned off when you are finished
    app.run(debug=True)
