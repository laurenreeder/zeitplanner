import data_scraper, os, pickle

COURSE_DATA = None

class Schedule:
    """This class holds a schedule, which is a list of sections, as well as a
    number of statistics about the schedule. It takes in a schedule as it is
    initialized and then compute_statistics is called on it."""
    def __init__(self, schedule):
        self.schedule = schedule
        self.earliest_time = 0
        self.latest_time = 0
        self.average_start = 0
        self.average_end = 0
        self.gap_count = 0
        self.days_of_class = 0

def compute_statistics(schedule_object):
    """This method takes in a schedule object that already has a list of sections 
    and calculates statistics that will be used to rank schedules later on."""

    # The earliest and latest times any section in a schedule will start or end
    earliest_time, latest_time = 24, 0

    # Average start and end times for the entire schedule
    average_start = average_end = 0

    # Make a list of all the meetings in a schedule
    meetings = [meeting for section in schedule_object.schedule
                for meeting in section.meetings]

    # Calculate start and end time statistics
    for meeting in meetings:
        earliest_time = min(earliest_time, meeting.start_time)
        latest_time = max(latest_time, meeting.end_time)
        average_start += meeting.start_time
        average_end += meeting.end_time
        
    average_start = average_start / len(meetings)
    average_end = average_end / len(meetings)

    # How many hours are empty between classes in the same day
    gap_count = 0

    # How many total days of class there are
    days_of_class = 7

    # Calculate days of class and gaps
    # Iterate through every day of the week
    for day in "MTWRFSU":
        # A list comprehension that compiles all the classes for the day
        day_classes = sorted([(meeting.start_time, meeting.end_time)
                              for meeting in meetings 
                              if day in meeting.days])
        # If there are no classes on a particular day
        if not day_classes:
            days_of_class += -1
            continue
        # Add in each time gap between two classes in a day
        for i in range(len(day_classes)-1):
            gap_count += day_classes[i+1][0] - day_classes[i][1]

    # Store the calculated values in the schedule object
    schedule_object.earliest_time = earliest_time
    schedule_object.latest_time = latest_time
    schedule_object.average_start = average_start
    schedule_object.average_end = average_end
    schedule_object.gap_count = gap_count
    schedule_object.days_of_class = days_of_class

def find_schedules(course_list, section_list, primary_compare, secondary_compare):
    """Returns an ordered list of schedules, where schedules are lists of sections
    given two ordering preferences"""
    
    schedule_list = []

    # TODO: deal with case in which len(course_list) == 0
    # This will become necessary when we allow users to request specific sections

    # Recursively generates all possible schedules given the input courses
    for group_list in generate_group_lists(course_list):
        section_lists = []
        for group in group_list:
            for section_list in group.sections.values():
                section_lists.append(section_list)
        schedule_list.extend(find_schedules_from_section_lists(section_lists))

    schedule_list = sort_schedules(schedule_list, primary_compare, secondary_compare)

    # Return a sorted list of schedule objects
    return schedule_list

def generate_group_lists(course_list):
    """Picks a group from each class from which to pick sections."""
    group_lists = []
    generate_group_lists_helper(0, course_list, [], group_lists)
    return group_lists

def generate_group_lists_helper(current_course, course_list, current_group_list, group_lists):
    """Recursive helper function for list generation."""
    if current_course >= len(course_list):
        group_lists.append(current_group_list[:])
        return
    for group in course_list[current_course].groups:
        current_group_list.append(group)
        generate_group_lists_helper(current_course + 1, course_list, current_group_list, group_lists)
        current_group_list.pop()

def find_schedules_from_section_lists(section_lists):
    """Finds schedules from lists of sections."""
    schedule_list = []
    find_schedules_from_section_lists_helper(0, section_lists, [], schedule_list)
    return schedule_list

def find_schedules_from_section_lists_helper(current_section_list, section_lists, current_schedule, schedule_list):
    """Recursive helper function for scheduler generation."""
    if current_section_list == len(section_lists):
        schedule_object = Schedule(current_schedule[:])
        compute_statistics(schedule_object)
        schedule_list.append(schedule_object)
        return
    for section in section_lists[current_section_list]:
        if can_add_section(section, current_schedule):
            current_schedule.append(section)
            find_schedules_from_section_lists_helper(current_section_list + 1, 
                                                     section_lists, 
                                                     current_schedule, 
                                                     schedule_list)
            current_schedule.pop()

def has_conflict(section1, section2):
    """Checks for a time overlap between two sections."""
    if section1.meetings is None or section2.meetings is None:
        return False
    for meeting1 in section1.meetings:
        for meeting2 in section2.meetings:
            days1, days2 = meeting1.days, meeting2.days
            if len(set(days1) & set(days2)) == 0:
                continue
            start_time1, end_time1  = meeting1.start_time, meeting1.end_time
            start_time2, end_time2  = meeting2.start_time, meeting2.end_time
            if (start_time1 < end_time2 and start_time2 < end_time1) or \
               (start_time2 < end_time1 and start_time1 < end_time2):
                return True
    return False

def can_add_section(new_section, schedule):
    """Determines if new_section can be added to the schedule."""
    return not any(has_conflict(new_section, section) for section in schedule)
    
def compare_early(sec_obj1, sec_obj2):
    """Compares two section objects to see which one has earlier classes."""
    result = sec_obj1.latest_time - sec_obj2.latest_time
    if result == 0:
        return sec_obj1.average_end - sec_obj2.average_end
    return result

def compare_late(sec_obj1, sec_obj2):
    """Compares two section objects to see which one has later classes."""
    result = sec_obj2.earliest_time - sec_obj1.earliest_time
    if result == 0:
        return sec_obj2.average_start - sec_obj1.average_start
    return result

def compare_compact(sec_obj1, sec_obj2):
    """Compares two section objects to see which one is more compact."""
    spread1 = sec_obj1.latest_time - sec_obj1.earliest_time
    spread2 = sec_obj2.latest_time - sec_obj2.earliest_time
    return spread1 - spread2

def compare_gaps(sec_obj1, sec_obj2):
    """Compares two section objects to see which one has fewer gaps."""
    return sec_obj1.gap_count - sec_obj2.gap_count
    
def compare_days(sec_obj1, sec_obj2):
    """Compares two section objects to see which one has fewer days of class."""
    return sec_obj1.days_of_class - sec_obj2.days_of_class

def compare_generic(s1, s2, primary_compare, secondary_compare):
    """Takes in two comparator functions. Makes decisions based on primary_compare
    first and then uses secondary_compare to break ties."""
    result = primary_compare(s1, s2)
    # If the primary comparison is zero, use the secondary comparison as a tiebreaker
    if result == 0:
        result = secondary_compare(s1, s2)
    if result < 0:
        return -1
    elif result == 0:
        return 0
    else:
        return 1

def sort_schedules(schedule_list, primary_compare, secondary_compare):
    """Compares two sections using the commpare_generic() helper method."""
    return sorted(schedule_list, cmp=lambda s1, s2: 
                  compare_generic(s1, s2, primary_compare, secondary_compare))
