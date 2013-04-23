import data_scraper, os, pickle

COURSE_DATA = None

##### TEMPORARY - FOR TESTING PURPOSES ONLY #####

if not os.path.exists("course_data.pickle"):
    COURSE_DATA = data_scraper.parse_course_data()
    pickle.dump(COURSE_DATA, open("course_data.pickle", "w"))
else:
    COURSE_DATA = pickle.load(open("course_data.pickle", "r"))

##### TEMPORARY - FOR TESTING PURPOSES ONLY #####

def compute_statistics(schedule_object):
    earliest_time = 24
    latest_time = 0

    average_start = 0
    average_end = 0

    # Make a list of all the meetings in a schedule
    #meetings = [meeting for meeting in section.meetings for section in schedule]
    meetings = []
    for section in schedule_object.schedule:
        for meeting in section.meetings:
            meetings.append(meeting)

    # Calculate start and end time statistics
    for meeting in meetings:
        earliest_time = min(earliest_time, meeting.start_time)
        latest_time = max(latest_time, meeting.end_time)
        average_start += meeting.start_time
        average_end += meeting.end_time
        
    average_start = average_start / len(meetings)
    average_end = average_end / len(meetings)

    gap_count = 0
    days_of_class = 7

    # Calculate days of class and gaps
    for day in "MTWRFSU":
        day_classes = sorted([(meeting.start_time, meeting.end_time)
                              for meeting in meetings 
                              if day in meeting.days])
        # If there are no classes on a particular day
        if not day_classes:
            days_of_class += -1
            continue
        for i in range(len(day_classes)-1):
            gap_count += day_classes[i+1][0] - day_classes[i][1]

    # Store the calculated values in the schedule object
    schedule_object.earliest_time = earliest_time
    schedule_object.latest_time = latest_time
    schedule_object.average_start = average_start
    schedule_object.average_end = average_end
    schedule_object.gap_count = gap_count
    schedule_object.days_of_class = days_of_class
    
def print_schedule(schedule):
    schedule_string = ""
    for section in schedule:
        schedule_string += "%s-%s-%s" % (section.group.course.department.name, section.group.course.code, section.section_number)
    print schedule_string

def find_schedules(course_list, section_list, primary_compare, secondary_compare):
    """Returns an ordered list of schedules, where schedules are lists of sections"""
    
    schedule_list = []

    # TODO: deal with case in which len(course_list) == 0

    for group_list in generate_group_lists(course_list):
        section_lists = []
        for group in group_list:
            for section_list in group.sections.values():
                section_lists.append(section_list)
        schedule_list.extend(find_schedules_from_section_lists(section_lists))

    schedule_list = sort_schedules(schedule_list, primary_compare, secondary_compare)

    return schedule_list

# Compares two section objects to see which one has earlier classes    
def compare_early(sec_obj1, sec_obj2):
    result = sec_obj1.latest_time - sec_obj2.latest_time
    if result == 0:
        return sec_obj1.average_end - sec_obj2.average_end
    return result

# Compares two section objects to see which one has later classes    
def compare_late(sec_obj1, sec_obj2):
    result = sec_obj2.earliest_time - sec_obj1.earliest_time
    if result == 0:
        return sec_obj2.average_start - sec_obj1.average_start
    return result

# Compares two section objects to see which one is more compact    
def compare_compact(sec_obj1, sec_obj2):
    spread1 = sec_obj1.latest_time - sec_obj1.earliest_time
    spread2 = sec_obj2.latest_time - sec_obj2.earliest_time
    return spread1 - spread2

# Compares two section objects to see which one has fewer gaps
def compare_gaps(sec_obj1, sec_obj2):
    return sec_obj1.gap_count - sec_obj2.gap_count

# Compares two section objects to see which one has fewer days of class    
def compare_days(sec_obj1, sec_obj2):
    return sec_obj1.days_of_class - sec_obj2.days_of_class

def compare_generic(s1, s2, primary_compare, secondary_compare):
    result = primary_compare(s1, s2)
    if result == 0:
        result = secondary_compare(s1, s2)
    if result < 0:
        return -1
    elif result == 0:
        return 0
    else:
        return 1

def sort_schedules(schedule_list, primary_compare, secondary_compare):
    return sorted(schedule_list, cmp=lambda s1, s2: compare_generic(s1, s2, primary_compare, secondary_compare))

class Schedule:
    def __init__(self, schedule):
        self.schedule = schedule
        self.earliest_time = 0
        self.latest_time = 0
        self.average_start = 0
        self.average_end = 0
        self.gap_count = 0
        self.days_of_class = 0

def generate_group_lists(course_list):
    group_lists = []
    generate_group_lists_helper(0, course_list, [], group_lists)
    return group_lists

def generate_group_lists_helper(current_course, course_list, current_group_list, group_lists):
    if current_course >= len(course_list):
        group_lists.append(current_group_list[:])
        return
    for group in course_list[current_course].groups:
        current_group_list.append(group)
        generate_group_lists_helper(current_course + 1, course_list, current_group_list, group_lists)
        current_group_list.pop()

def find_schedules_from_section_lists(section_lists):
    schedule_list = []
    find_schedules_from_section_lists_helper(0, section_lists, [], schedule_list)
    return schedule_list

def find_schedules_from_section_lists_helper(current_section_list, section_lists, current_schedule, schedule_list):
    if current_section_list == len(section_lists):
        schedule_object = Schedule(current_schedule[:])
        compute_statistics(schedule_object)
        schedule_list.append(schedule_object)
        return
    for section in section_lists[current_section_list]:
        if can_add_section(section, current_schedule):
            current_schedule.append(section)
            find_schedules_from_section_lists_helper(current_section_list + 1, section_lists, current_schedule, schedule_list)
            current_schedule.pop()

def has_conflict(section1, section2):
    if section1.meetings is None or section2.meetings is None:
        return False
    for meeting1 in section1.meetings:
        for meeting2 in section2.meetings:
            days1 = meeting1.days
            days2 = meeting2.days
            if len(set(days1) & set(days2)) == 0:
                continue
            start_time1 = meeting1.start_time
            end_time1 = meeting1.end_time
            start_time2 = meeting2.start_time
            end_time2 = meeting2.end_time
            if (start_time1 < end_time2 and start_time2 < end_time1) or \
               (start_time2 < end_time1 and start_time1 < end_time2):
                return True
    return False

def can_add_section(new_section, schedule):
    return not any(has_conflict(new_section, section) for section in schedule)
