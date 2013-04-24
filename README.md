ZeitPlanner
===========

CIS 192 Final Project

**Project Overview:**

The purpose of ZeitPlanner is to help Penn students plan out optimal schedules given a set of classes. They can choose from a variety of criteria to indicate their preferences. We hope this application can be a time-saver as well as offer users reassurance that they have the optimal schedule.

**Terminology:**

* **Department:** An academic department at UPenn, e.g. CIS.
* **Course:** A course within a department, e.g. CIS-192.
* **Section:** One specific section of a course, e.g. CIS-192-001.
* **Group:** A collection of course sections. If a course has more than one group, students must pick all sections for that course (e.g. the lecture, recitation, etc.) from the same group.
* **Meeting:** The meeting time, day(s), and location of a single class within a section. Courses that meet at different times on different days of the week have more than one meeting.

**Project Features:**

One core component of our project is the web scraper. Starting from http://www.upenn.edu/registrar/timetable/, our web scraper extracts a list of departments and their corresponding registrar pages, visits each department page and extracts the relevant course data, and finally parses the data and adds it to a single hierarchical structure. The resulting data is stored with the following class structure: CourseData -> Department -> Course -> Group -> Section -> Meeting. By using Python's dictionary data type, we provide O(1) retrieval time for all pertinent data in the data set. In addition, we used Python's built-in pickle module for persistent storage of course data.

Another core component of our project is the scheduler, which enumerates all potential schedules for a given set of courses using a depth first search (with backtracking), then ranks schedules based on user preferences and returns the top-scoring result. Though the searching itself was relatively straightforward, We made use of Python's support for higher order functions in order to combine multiple ranking functions into an aggregate comparator for the sorting step.

The third core component of our project was the server, which was built on top of the Flask framework for web applications. The server provides our webpage with API access to the verification of user input and to the computation of optimal schedules. Data is transferred between the main webpage and our server via JSON-encoded messages.

**Running Instructions:**

1.  Run "python server.py" in the command line. Ensure that the server is running on localhost on port 5000. If this is the first time the server is being run, it will automatically scrape Penn's course data and store it to disk for future use.

2.  Open penn_scheduler.html, the main webpage of the application.

3.  Enter the desired courses, adjust optimization preferences, and submit the form. Courses can be entered in a number of different formats, such as "CIS-192", "CIS 192", "CIS192", or even "cis192".
