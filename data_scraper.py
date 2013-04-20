import requests, re, time
from bs4 import BeautifulSoup
from collections import defaultdict

def parse_course_data():
    """Returns a CourseData object"""

    page_text = requests.get("http://www.upenn.edu/registrar/timetable/").text
    soup = BeautifulSoup(page_text)

    # Webpage structure: <table><tr><td>Spring 2013</...>
    # Webpage structure: <table><tr><td><table><tr><td>ACCT</...>

    # Get the list of departments as (DEPT, dept.html) pairs
    depts = [(row.find("td").text.strip(), re.sub(r"\s+", "", row.find("a")["href"]))
             for row in soup.find(text="ACCT").parent.parent.parent.find_all("tr")]

    # Get the contents of the cell containing the semester information
    semester_info = soup.find(text="ACCT").parent.parent.parent.parent.parent.parent \
                        .find("td").text.strip().split(" ")

    course_data = CourseData()

    course_data.semester = semester_info[0]
    course_data.year = semester_info[1]

    for department, page in depts:
        r = requests.get('http://www.upenn.edu/registrar/timetable/%s' % (page))
        if r.status_code == 200:
            print "Successfully retrieved course data for %s." % (department)
        else:
            print "Unable to retrieve course data for %s." % (department)
            continue
        soup = BeautifulSoup(r.text)
        text = soup.find("pre").find_all("p")[-1].text
        course_data.add_department(parse_department(department, text))

    return course_data

def parse_department(department_name, text):
    """Returns a Department object representing the given department"""
    
    department = Department()
    department.name = department_name

    course_blocks = re.split(r"\n\s*\n", text)

    for course_block in course_blocks:

        if len(course_block.split("\n")) == 1:
            continue

        course = Course()

        first_line, remaining_lines = course_block.split("\n", 1)

        # Extract the course code, name, and credits from the first line

        course_pattern = r"\s*(?P<department>\w+)\s*-(?P<code>\d+)" + \
                         r"\s+(?P<name>(\S+ )+)" + \
                         r"\s*(?P<credits>\d\.?\d?)" + \
                         r".*"
        match = re.match(course_pattern, first_line)
        # If the first line does not match this format, skip the entire course block
        if not match:
            continue
        course.code = match.group("code")
        course.name = match.group("name").strip()
        course.credits = match.group("credits")

        group_blocks = remaining_lines.split("GROUP")
        # Split by "GROUP", parse, and discard those with not enough information
        for group_block in group_blocks:
            group = parse_group(group_block)
            if group:
                course.add_group(group)

        department.add_course(course)

    return department

def parse_group(group_block):
    """Returns a Group object representing the group of sections in the given group block"""

    lines = group_block.splitlines()
    group = Group()

    while lines:
        section, remaining_lines = parse_section(lines)
        if section:
            group.add_section(section)
        lines = remaining_lines

    if not group.sections:
        return None

    return group

# Parsing a section:
#   1) Consume lines that don't start with 3 digits
#   2) Parse: ddd (type day time room)* (professor)
#      a) Type: www
#      b) Day: w+
#      c) Time: ((d+(:d+)?-d+(:d+)?(AM|PM|NOON)) | TBA)(,\s)?
#      d) Professor: \s\s+(.*)
#   3) Search subsequent lines for additional times and rooms
#   4) Stop when another line beginning with ddd is encountered

def parse_section(lines):
    "Parses a single section from the beginning of lines, then returns a Section object representing that section and the remainder of the lines"
    
    type_day_time_location_pattern = \
        r"(?P<type>\w+) " + \
        r"(" + \
            r"(" + \
                r"(?P<days>\w+) " + \
                r"(?P<time>\d+(:\d+)?-\d+(:\d+)?(AM|PM|NOON))" + \
                r"( (?P<location>\w+ \w+))?" + \
            r")|(" + \
                r"TBA" + \
            r")" + \
        r")" + \
        r"(, )?"

    section_pattern = \
        r"\s*(?P<section_number>\d+)" + \
        r"\s+(" + type_day_time_location_pattern + r")*" + \
        r"\s\s+(?P<instructor>.*)"

    section = Section()

    while lines and not re.match(section_pattern, lines[0]):
        lines = lines[1:]

    if not lines:
        return None, lines

    match = re.match(section_pattern, lines[0])
    section.section_number = match.group("section_number")
    section.instructor = match.group("instructor")

    while True:
        if section.meetings is not None:
            for match in re.finditer(type_day_time_location_pattern, lines[0]):
                section.type = match.group("type")
                # TBA
                if not match.group("days"):
                    section.meetings = None
                    break
                else:
                    days = match.group("days")
                    time = match.group("time")
                    location = match.group("location")
                    meeting = Meeting()
                    meeting.days = [c for c in days]
                    time_pattern = r"(?P<start_hour>\d+):?(?P<start_minute>\d+)?-(?P<end_hour>\d+):?(?P<end_minute>\d+)?(?P<period>AM|PM|NOON)"
                    time_match = re.match(time_pattern, time)
                    meeting.start_time = int(time_match.group("start_hour"))
                    if time_match.group("start_minute"):
                        meeting.start_time += int(time_match.group("start_minute")) / 60.0
                    meeting.end_time = int(time_match.group("end_hour"))
                    if time_match.group("end_minute"):
                        meeting.end_time += int(time_match.group("end_minute")) / 60.0
                    if time_match.group("period") == "PM" and meeting.end_time < 12:
                        if meeting.start_time < meeting.end_time:
                            meeting.start_time += 12
                        meeting.end_time += 12
                    section.add_meeting(meeting)
        lines = lines[1:]
        if not lines or re.match(section_pattern, lines[0]):
            break

    return section, lines

# Container classes

class CourseData:
    def __init__(self):
        self.year = None
        self.semester = None
        self.departments = {}
    def add_department(self, department):
        self.departments[department.name] = department
    def get_department(self, name):
        return self.departments.get(name, None)

class Department:
    def __init__(self):
        self.name = None
        self.courses = {}
    def add_course(self, course):
        self.courses[course.code] = course
    def get_course(self, code):
        return self.courses.get(code, None)

class Course:
    def __init__(self):
        self.code = None
        self.name = None
        self.credits = None
        self.course_quality = None
        self.groups = []
    def add_group(self, group):
        self.groups.append(group)
    def get_group(self, section_number):
        for group in self.groups:
            # Concatenate into a single list, then scan through
            for section in sum(group.sections.values(), []):
                if section.section_number == section_number:
                    return group
        return None
    def get_section(self, section_number):
        for group in self.groups:
            # Concatenate into a single list, then scan through
            for section in sum(group.sections.values(), []):
                if section.section_number == section_number:
                    return section
        return None
    def __str__(self):
        return "Code: %s, Name: %s, Credits: %s" % (self.code, self.name, self.credits)

class Group:
    def __init__(self):
        self.sections = defaultdict(list) # type -> [Section]
    def add_section(self, section):
        self.sections[section.type].append(section)
    def get_sections(self, type):
        return self.sections[type]
    def __str__(self):
        return "Group:\n\n%s\n" % ("\n\n".join("%s:\n%s" % (k, "\n".join(str(s) for s in v)) for k, v in self.sections.items()))

class Section:
    def __init__(self):
        self.section_number = None
        self.instructor = None
        self.instructor_quality = None
        self.type = None
        self.meetings = []
    def add_meeting(self, meeting):
        self.meetings.append(meeting)
    def __str__(self):
        return "Section number: %s, Type: %s, Instructor: %s, Meetings: %s" % \
            (self.section_number, self.type, self.instructor, str([str(meeting) for meeting in self.meetings]))

class Meeting:
    def __init__(self):
        self.days = []
        self.start_time = None
        self.end_time = None
        self.location = None
    def __str__(self):
        return "Days: %s, Start: %s, End: %s, Location: %s" % \
            (str(self.days), str(self.start_time), str(self.end_time), self.location)
