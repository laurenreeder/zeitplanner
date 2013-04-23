# Before editing:
#     1) View -> Uncheck "Print Layout"
#     2) Tools -> Preferences -> Uncheck "Use Smart Quotes"

from functools import wraps
from flask import current_app, Flask, jsonify, request, render_template
import colorsys, math, pickle, os, re

import sys

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

# @app.route("/")
# def index():
    # return render_template("penn_scheduler.html")

@app.route("/api/schedule/", methods=["GET"])
@support_jsonp
def schedule():

    class_dict = {}
    for class_string in request.args.getlist("classes[]"):
        key, value = class_string.split(":", 1)
        class_dict[key] = value

    sys.stderr.write("Args: " + str(request.args))
    sys.stderr.write("class_dict: " + str(class_dict))

    validate_response = validate(class_dict)

    if "error" in validate_response:
        return jsonify(validate_response)
    
    else:
        course_list = validate_response["result"]["courses"]
        section_list = validate_response["result"]["sections"]
        primary_compare = get_comparison_function(request.args["primaryCompare"])
        secondary_compare = get_comparison_function(request.args["secondaryCompare"])
        schedules = scheduler.find_schedules(course_list, section_list, primary_compare, secondary_compare)
        if len(schedules) == 0:
            html = "No valid schedules could be found."
        else:
            html = "Optimized Schedule:<br /><br />" + schedule_to_html(schedules[0])
            # html += "<br />Random Schedule:<br /><br />" + schedule_to_html(schedules[-1])
        return jsonify({"result": html})

def get_full_day_name(day):
    if day == "U":
        return "Sunday"
    elif day == "M":
        return "Monday"
    elif day == "T":
        return "Tuesday"
    elif day == "W":
        return "Wednesday"
    elif day == "R":
        return "Thursday"
    elif day == "F":
        return "Friday"
    elif day == "S":
        return "Saturday"

import sys

def schedule_to_html(schedule_object):
    # return ' '.join(["%s-%s-%s" % (section.group.course.department.name, section.group.course.code, section.section_number) for section in schedule.schedule])

    schedule = schedule_object.schedule
    earliest_start_time = schedule_object.earliest_time
    latest_end_time = schedule_object.latest_time

    table = {}
    
    for day in "MTWRF":
        table[day] = {}
        time = earliest_start_time
        while time < latest_end_time:
            table[day][time] = ["", 1, [255, 255, 255]]
            time += 0.5

    hue_increment = 300 / len(schedule)
    current_hue = 0

    for section in schedule:
        for meeting in section.meetings:
            cell_text = "%s-%s-%s" % (section.group.course.department.name, section.group.course.code, section.section_number)
            num_rows = int((meeting.end_time - meeting.start_time) * 2)
            rgb = colorsys.hsv_to_rgb(current_hue / 360.0, 1, 1)
            rgb = [255*value for value in rgb]
            # transparent_rgb = [255*c for c in rgb] # rgba_to_rgb(rgb[0], rgb[1], rgb[2], 0.3)
            for day in meeting.days:
                # table[day][meeting.start_time] = [cell_text, num_rows, transparent_rgb]
                table[day][meeting.start_time] = [cell_text, num_rows, rgb]
                time = meeting.start_time + 0.5
                while time < meeting.end_time:
                    table[day][time][1] = 0
                    time += 0.5
            current_hue += hue_increment

    html_string = ""

    td_with_style = "<td style=\"border:1px solid; padding-left:10px; padding-right:10px\">"

    html_string += "<table align=\"center\" style=\"width:675px; border:3px solid; border-collapse:collapse\">"
    html_string += "<tr>"
    html_string += td_with_style + "</td>"
    for day in "MTWRF":
        html_string += td_with_style + get_full_day_name(day) + "</td>"
    html_string += "</tr>"
    time = earliest_start_time
    while time < latest_end_time:
        html_string += "<tr>"
        html_string += td_with_style + str(int(math.floor(time if time <= 12.5 else time - 12))) + (":00" if time % 1 == 0 else ":30") + "</td>"
        for day in "MTWRF":
            num_rows = table[day][time][1]
            rgb = ",".join(str(int(e)) for e in table[day][time][2])
            if num_rows != 0:
                html_string += "<td rowspan=\"" + str(num_rows) + "\" style=\"border:1px solid; padding-left:10px; padding-right:10px; background-color:rgba(" + rgb + ",0.3)\">" + table[day][time][0] + "</td>"
        html_string += "</tr>"
        time += 0.5

    return html_string

def get_comparison_function(name):
    if name == "early":
        return scheduler.compare_early
    elif name == "late":
        return scheduler.compare_late
    elif name == "compact":
        return scheduler.compare_compact
    elif name == "minGaps":
        return scheduler.compare_gaps
    elif name == "minDays":
        return scheduler.compare_days

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

        sys.stderr.write("Course input: "+str(course_input)+"\n")

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
