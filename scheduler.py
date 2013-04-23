import data_scraper

COURSE_DATA = None

cdef find_schedules(course_list, section_list):
    """Returns an ordered list of schedules, where schedules are lists of sections"""
    pass

def compute_statistics(schedule):
    earliest_time = 24
    latest_time = 0

    average_start = 0
    average_end = 0

    # Make a list of all the meetings in a schedule
    #meetings = [meeting for meeting in section.meetings for section in schedule]
    meetings = []
    for section in schedule:
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
    
    print earliest_time
    print latest_time
    print average_start
    print average_end
    print days_of_class
    print gap_count
