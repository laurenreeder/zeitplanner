COURSE_DATA = None

##### TEMPORARY - FOR TESTING PURPOSES ONLY #####

import data_scraper, os, pickle

if not os.path.exists("course_data.pickle"):
    COURSE_DATA = data_scraper.parse_course_data()
    pickle.dump(COURSE_DATA, open("course_data.pickle", "w"))
else:
    COURSE_DATA = pickle.load(open("course_data.pickle", "r"))

##### TEMPORARY - FOR TESTING PURPOSES ONLY #####

def print_schedule(schedule):
	schedule_string = ""
	for section in schedule:
		schedule_string += "%s-%s-%s" % (section.group.course.department.name, section.group.course.code, section.section_number)
	print schedule_string

def find_schedules(course_list, section_list):
    """Returns an ordered list of schedules, where schedules are lists of sections"""
    
    schedule_list = []

    # TODO: deal with case in which len(course_list) == 0

    for group_list in generate_group_lists(course_list):
        section_lists = []
        for group in group_list:
            for section_list in group.sections.values():
                section_lists.append(section_list)
        schedule_list.extend(find_schedules_from_section_lists(section_lists))

    return schedule_list

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
        schedule_list.append(current_schedule[:])
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
