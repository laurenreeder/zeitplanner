import requests, re
from bs4 import BeautifulSoup
from collections import defaultdict

def parse_course_data():
    """Returns a CourseData object"""

    # Get the contents of the registrar page
    page_text = requests.get("http://www.upenn.edu/registrar/timetable/").text
    soup = BeautifulSoup(page_text)

    # Webpage structure:
    #   Full Table
    #     -> <table><tr><td>Semester Year</...>
    #     -> <table><tr><td><table><tr><td>DEPT</...>
    dept_table = soup.find(text="ACCT").parent.parent.parent
    full_table = dept_table.parent.parent.parent

    # Initialize a new CourseData object
    course_data = CourseData()

    # Get the contents of the first cell in the full table, which contains the
    # semester information
    semester_info = full_table.find("td").text.strip().split(" ")

    # Extract the semester and year from the semester information
    course_data.semester = semester_info[0]
    course_data.year = semester_info[1]

    # Get the list of departments as (DEPT, dept.html) pairs
    departments = [(row.find("td").text.strip(),
                    re.sub(r"\s+", "", row.find("a")["href"]))
                   for row in dept_table.find_all("tr")]

    # Parse the data from each department webpage (which is stored in the final
    # <p> section of the <pre> section), and add it to the CourseData object
    for department, page in departments:
        r = requests.get('http://www.upenn.edu/registrar/timetable/%s' % (page))
        if r.status_code == 200:
            print "Successfully retrieved course data for %s." % (department)
        else:
            print "Unable to retrieve course data for %s." % (department)
            continue
        department_soup = BeautifulSoup(r.text)
        text = department_soup.find("pre").find_all("p")[-1].text
        course_data.add_department(parse_department(department, text))

    return course_data

def parse_department(department_name, text):
    """Returns a Department object representing the given department"""
    
    # Create a new Department object and set its name
    department = Department()
    department.name = department_name

    # Separate the department page data into course blocks (one per course)
    course_blocks = re.split(r"\n\s*\n", text)

    # Parse each course block, and add the resulting Course object to the
    # department data
    for course_block in course_blocks:

        # If there is only a single line in the course block (most likely
        # blank), skip it
        if len(course_block.split("\n")) == 1:
            continue

        # Create a new Course object
        course = Course()

        # Separate the first line from the remaining lines of the course block
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
        # Otherwise, store the extracted information into the Course object
        course.code = match.group("code")
        course.name = match.group("name").strip()
        course.credits = match.group("credits")

        # Split the remaining lines into section groups (courses without groups
        # of sections will have just one group)
        group_blocks = remaining_lines.split("GROUP")

        # Parse each group block, discarding those with too little information,
        # and add each resulting Group object to the course
        for group_block in group_blocks:
            group = parse_group(group_block)
            if group:
                course.add_group(group)

        # Add the course to the department
        department.add_course(course)

    # Return the parsed Department object
    return department

def parse_group(group_block):
    """Returns a Group object representing the group of sections in the given group block"""

    # Split the group block into individual lines
    lines = group_block.splitlines()

    # Create a Group object
    group = Group()

    # While additional lines remain
    while lines:

        # Parse a single section, and store the remainder of the lines in the
        # group block
        section, remaining_lines = parse_section(lines)

        # If a section was successfully parsed, add it to the group
        if section:
            group.add_section(section)

        # Update the lines variable to contain only the remaining lines
        lines = remaining_lines

    # If no sections were extracted from the group block, return None
    if not group.sections:
        return None

    # Otherwise, return the parsed Group object
    return group

def parse_section(lines):
    "Parses a single section from the beginning of lines, then returns a Section object representing that section and the remaining lines"
    
    time_pattern = \
        r"(?P<start_hour>\d+)(:(?P<start_minute>\d+))?" + \
        r"-(?P<end_hour>\d+)(:(?P<end_minute>\d+))?" + \
        r"(?P<period>AM|PM|NOON)"

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

    # Create a Section object
    section = Section()

    # Consume lines while additional lines remain and the first remaining line
    # is not a section line
    while lines and not re.match(section_pattern, lines[0]):
        lines = lines[1:]

    # If no additional lines remain, no section could be parsed
    if not lines:
        # Return the parsed section (None) and the remaining lines ([])
        return None, lines

    # At this point, the first remaining line is a valid section line
    match = re.match(section_pattern, lines[0])

    # Extract the section number and instructor from the first remaining line
    section.section_number = match.group("section_number")
    section.instructor = match.group("instructor")

    # Loop until no lines remain, or until the next section line is encountered
    while True:

        # If the list of section meetings has not been set to None (indicating
        # that the section's meeting information is TBA)
        if section.meetings is not None:

            # For each block of meeting information in the current line
            for match in re.finditer(type_day_time_location_pattern, lines[0]):

                # Set the section type to the meeting type (LEC, REC, LAB, SEM,
                # etc.)
                section.type = match.group("type")

                # If the block does not contain day information, then the
                # section's meeting information is TBA, meaning it can be set to
                # None, and any other meeting information in the current line
                # can be ignored
                if not match.group("days"):
                    section.meetings = None
                    break

                # Otherwise, extract the day, time, and location information
                # from the meeting block
                else:

                    # Extract the days, time, and location information
                    days = match.group("days")
                    time = match.group("time")
                    location = match.group("location")

                    # Create a Meeting object
                    meeting = Meeting()

                    # Set the meeting's days to a list of individual days
                    meeting.days = [day for day in days]

                    # Extract the meeting's time information
                    time_match = re.match(time_pattern, time)

                    # Extract the meeting's start time
                    meeting.start_time = int(time_match.group("start_hour"))
                    if time_match.group("start_minute"):
                        meeting.start_time += int(time_match.group("start_minute")) / 60.0

                    # Extract the meeting's end time
                    meeting.end_time = int(time_match.group("end_hour"))
                    if time_match.group("end_minute"):
                        meeting.end_time += int(time_match.group("end_minute")) / 60.0

                    # Convert the meeting's time information into 24-hour time
                    if time_match.group("period") == "PM" and meeting.end_time < 12:
                        if meeting.start_time < meeting.end_time:
                            meeting.start_time += 12
                        meeting.end_time += 12

                    # Add the meeting to the section
                    section.add_meeting(meeting)

        # Move on to the next line to look for additional meeting information
        lines = lines[1:]

        # Break if no lines remain, or if the next section line is encountered
        if not lines or re.match(section_pattern, lines[0]):
            break

    # Return the parsed Section object and the remaining lines in the group block
    return section, lines

# Container classes

class CourseData:

    def __init__(self):
        self.year = None
        self.semester = None
        self.departments = {}
    
    def add_department(self, department):
        """Adds the given department to the course data"""
        self.departments[department.name] = department
    
    def get_department(self, name):
        """Gets a department by abbreviated name"""
        return self.departments.get(name, None)

class Department:
    
    def __init__(self):
        self.name = None
        self.courses = {}
    
    def add_course(self, course):
        """Adds the given course to the department"""
        self.courses[course.code] = course
    
    def get_course(self, code):
        """Gets a course by course code"""
        return self.courses.get(code, None)

class Course:
    
    def __init__(self):
        self.code = None
        self.name = None
        self.credits = None
        self.course_quality = None
        self.groups = []
    
    def add_group(self, group):
        """Adds the given group to the course"""
        self.groups.append(group)
    
    def get_group(self, section_number):
        """Returns the group containing the section with the given section number"""
        for group in self.groups:
            # Concatenate into a single list, then scan through
            for section in sum(group.sections.values(), []):
                if section.section_number == section_number:
                    return group
        return None
    
    def get_section(self, section_number):
        """Gets a section by section number"""
        for group in self.groups:
            # Concatenate into a single list, then scan through
            for section in sum(group.sections.values(), []):
                if section.section_number == section_number:
                    return section
        return None
    
    def __str__(self):
        return "Code: %s, Name: %s, Credits: %s" % \
               (self.code, self.name, self.credits)

class Group:
    
    def __init__(self):
        # sections is a dictionary with entries of the form
        # {type : [section1, section2, ...]}
        self.sections = defaultdict(list)
    
    def add_section(self, section):
        """Adds the given section to the group"""
        self.sections[section.type].append(section)
    
    def get_sections(self, type):
        """Gets sections by type"""
        return self.sections[type]
    
    def __str__(self):
        return "Group:\n\n%s" % \
               ("\n\n".join("%s:\n%s" % (k, "\n".join(str(s) for s in v))
                            for k, v in self.sections.items()))

class Section:
    
    def __init__(self):
        self.section_number = None
        self.instructor = None
        self.instructor_quality = None
        self.type = None
        self.meetings = []
    
    def add_meeting(self, meeting):
        """Adds the given meeting to the section"""
        self.meetings.append(meeting)
    
    def __str__(self):
        return "Section number: %s, Type: %s, Instructor: %s, Meetings: %s" % \
               (self.section_number, self.type, self.instructor,
                str([str(meeting) for meeting in self.meetings]))

class Meeting:
    
    def __init__(self):
        self.days = []
        self.start_time = None
        self.end_time = None
        self.location = None
    
    def __str__(self):
        return "Days: %s, Start: %s, End: %s, Location: %s" % \
            (str(self.days), str(self.start_time), str(self.end_time), self.location)
