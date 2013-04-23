import colorsys, math, pickle, os, re

from flask import current_app, Flask, jsonify, request
from functools import wraps

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

# The /api/schedule/ route provides API access for computing optimal schedules
@app.route("/api/schedule/", methods=["GET"])
@support_jsonp
def schedule():
    """Verifies and computes an optimal schedule for a list of courses"""

    # Since dictionaries cannot be passed directly through the request
    # parameters, we need to recreate the map from input fields to classes
    class_dict = {}
    for class_string in request.args.getlist("classes[]"):
        key, value = class_string.split(":", 1)
        class_dict[key] = value

    # Validate the input dictionary
    validate_response = validate(class_dict)

    # If one or more of the inputs was invalid, return a response of the form
    # {"error": [key_of_invalid_input_1, key_of_invalid_input_2, ...]}
    if "error" in validate_response:
        return jsonify(validate_response)
    
    # If all of the classes were valid, compute the optimal schedule using the
    # user's preferences and return the result
    else:

        # Retrieve the course and section lists from the validation response
        course_list = validate_response["result"]["courses"]
        section_list = validate_response["result"]["sections"]
        
        # Retrieve the primary and secondary comparison functions from the
        # input fields
        primary_compare = get_comparison_function(request.args["primaryCompare"])
        secondary_compare = get_comparison_function(request.args["secondaryCompare"])
        
        # Compute the list of optimal schedules
        schedules = scheduler.find_schedules(course_list, section_list, primary_compare, secondary_compare)

        # If no valid schedules exist, return an appropriate response
        if len(schedules) == 0:
            html = "No valid schedules could be found."

        # Otherwise, return the schedule as an HTML table
        else:
            html = "Optimized Schedule:<br /><br />" + schedule_to_html(schedules[0])
            # html += "<br />Random Schedule:<br /><br />" + schedule_to_html(schedules[-1])

        # Return the response as a JSON-encoded dictionary
        return jsonify({"result": html})

def validate(class_dict):
    """Returns {"result": {"courses": [c1, c2, ...], "sections": [s1, s2, ...]}}
    for the given form data if all inputs are valid, or returns {"error":
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

    # Return the response
    return response

def get_full_day_name(day):
    """Helper method that converts single-letter day abbreviations into full day
    names"""

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

def frange(start, stop, step):
    """Range generator for floating point values"""
    while start < stop:
        yield start
        start += step

def schedule_to_html(schedule_object):
    """Returns an HTML table representation of a schedule"""

    schedule = schedule_object.schedule
    earliest_start_time = schedule_object.earliest_time
    latest_end_time = schedule_object.latest_time

    # A dictionary from days to schedule information for those days
    table = {}
    
    # Initialize the table
    for day in "MTWRF":
        table[day] = {}
        for time in frange(earliest_start_time, latest_end_time, 0.5):
            # By default, each table cell is empty, spans a single row, and has
            # a white background
            table[day][time] = ["", 1, [255, 255, 255]]

    # Variables used to compute background colors that are evenly distributed
    # over the spectrum
    hue_increment = 300 / len(schedule)
    current_hue = 0

    # For each section in the schedule
    for section in schedule:

        # For each meeting time in each section (courses such as PHYS-151 meet
        # at different times on different days, so we need to take that into
        # account)
        for meeting in section.meetings:

            # Set the cell text to DEPT-###-###
            cell_text = "%s-%s-%s" % (section.group.course.department.name,
            	                      section.group.course.code,
            	                      section.section_number)
            
            # Compute the number of rows the meeting will occupy in the table,
            # where each row occupies one 30-minute block
            num_rows = int((meeting.end_time - meeting.start_time) * 2)

            # Compute the RGB values of the current hue at full saturation and brightness
            rgb_float = colorsys.hsv_to_rgb(current_hue / 360.0, 1, 1)

            # Scale the RGB values to be in the range [0, 255] and convert them
            # into integers
            rgb = [int(255*c) for c in rgb_float]

            # For each day that the current meeting meets
            for day in meeting.days:

                # Initialize the top cell of the block of cells occupied by the
                # meeting
                table[day][meeting.start_time] = [cell_text, num_rows, rgb]

                # Set the number of rows occupied by each of the remaining cells
                # in the cell block to zero
                for time in frange(meeting.start_time + 0.5,
                                   meeting.end_time, 0.5):
                    table[day][time][1] = 0

            # Increment the current hue value
            current_hue += hue_increment

    # Template for <td> tag used by each cell in the table
    td_with_style = '<td rowspan="%d" style="border:1px solid; ' + \
                    'padding-left:10px; padding-right:10px; %s">'


    # Most cells have a rowspan of 1
    td = td_with_style % (1, "")

    # Initialize the HTML string to the opening table tag
    html_string = '<table align="center" style="width:675px; ' + \
                  'border:3px solid; border-collapse:collapse">'

    # Add a row
    html_string += "<tr>"

    # Add an empty cell in the upper-lefthand corner
    html_string += td + "</td>"

    # Fill in the cells in the first row of the table with the days of the week
    for day in "MTWRF":
        html_string += td + get_full_day_name(day) + "</td>"
    html_string += "</tr>"

    # For each 30-minute interval in the schedule
    for time in frange(earliest_start_time, latest_end_time, 0.5):

        # Add the opening row tag
        html_string += "<tr>"

        # Add a cell containing the interval's start time
        html_string += td
        html_string += str(int(math.floor(time if time <= 12.5 else time - 12)))
        html_string += (":00" if time % 1 == 0 else ":30")
        html_string += "</td>"

        # For each day, add all cells to the table in the current row that are
        # not shadowed by above cells (this occurs for classes that span
        # multiple 30-minute intervals, and therefore span multiple cells in the
        # table)
        for day in "MTWRF":
            num_rows = table[day][time][1]
            # If the current cell is not shadowed by an above cell, add it to
            # the table
            if num_rows != 0:
                rgb_string = ",".join(str(c) for c in table[day][time][2])
                background_string = "background-color:rgba(%s,0.3)" % rgb_string
                html_string += td_with_style % (num_rows, background_string)
                html_string += table[day][time][0]
                html_string += "</td>"
        
        # Add the closing row tag
        html_string += "</tr>"

    # Return the HTML table representation of the schedule
    return html_string

def get_comparison_function(name):
    """Returns the comparison function of the given name"""

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
