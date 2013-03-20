zeitplanner
===========

CIS 192 Final Project

Proposal:
Our proposal is to improve and deploy our application from PennApps, ZeitPlanner. The purpose of ZeitPlanner is to help Penn students plan out optimal schedules given a set of classes. They can choose from a variety of criteria to indicate their preferences. We hope this application can be a time-saver as well as offer users reassurance that they have the optimal schedule.

Current State:
ZeitPlanner is currently written in JavaScript with HTML and CSS as the front end. It offers the ability to add unlimited courses (by department and code, but not section) as well as a lunch break. The available user preferences are early/late classes, minimizing gaps, minimizing spread, and minimizing class days. We currently use Alex Rattray’s scraper to obtain data and we currently host the webapp on Dylan’s SEAS server, which is vulnerable, private, and slow.

Improvements: 
First, we want to write our own scraper in Python. Alex’s solution misses a few key points. It does not handle classes which start on the quarter of the hour, groups (i.e., which recitations are tied to which lectures), classes with different times on different days, classes with different CU values, or TBA locations.
Second, we want to translate our backend from JavaScript into Python. There are a few optimizations we can make. First, we can check course conflicts using pairwise comparisons instead of filling an array like we currently do. We can also treat lectures that occur at the same time as a single unit and then break ties by instructor quality. This streamlines intro courses such as PHYS 150 with several concurrent lectures.
Third, there are additional features we would like to include. The first is to allow users to request specific sections of courses. We would also like to allow users to input a list of optional courses for ZeitPlanner to choose from, useful for fun electives that can fit anywhere. Finally, we want to add more preferences for users to choose from, including instructor quality and difficulty. We have two more low-priority features we’d like to add if we have the time, including predictive typing for course input and minimizing the walk between classes.
In terms of our webpage, we’d like to experiment with page templates in Python as opposed to our current solution, which is to use JavaScript to modify and output HTML.
We also want to add a rudimentary account system that allows users to save their schedules. There are two options we will consider, the first using MongoDB and the database space that Heroku provides for us. The second is integrating Dropbox.
Finally, we want to deploy ZeitPlanner on Heroku and make it public. Libraries we plan to use in this transition may include Django and Flask. We have many things we want to accomplish with this final project and we will do as much as we can with the time that we have.
