import enum
import requests
import re
from bs4 import BeautifulSoup as bs
import json
import time

#Gets the links for all the courses offered
def get_all_courses_links():
    request = requests.get('https://catalog.ucsd.edu/front/courses.html').text
    soup = bs(request, 'lxml')
    all_courses_element = soup.find_all('a', string='courses')
    all_courses_links = ["https://catalog.ucsd.edu" + x.get('href')[2:] for x in all_courses_element]
    outfile = open('links.json', 'w')
    outfile.write(str(all_courses_links).replace("'",'"'))

#Scrapes the prerequisite requirements and course name from course website
def get_info_from_links(link):
    request = requests.get(link).text
    soup = bs(request, 'lxml')
    course_id = [x.text for x in soup.find_all('p', class_="course-name")]
    #course_name = [x.text.split('. ')[1] for x in soup.find_all('p', class_="course-name")]
    course_descriptions = [x.text[x.text.find('Prerequisites:'):].split('.')[0].replace(u'\xa0', u'') if x.text.find("Prerequisites:") > 0 else "" for x in soup.find_all('p', class_="course-descriptions") ]
    #name_and_prereqs = dict(zip(course_name, course_descriptions))
    id_name_prereqs = dict(zip(course_id, course_descriptions))
    return id_name_prereqs

#Gets the majors list, to be used with another scraper
def get_majors():
    request = requests.get('https://blink.ucsd.edu/instructors/academic-info/majors/major-codes.html').text
    soup = bs(request, 'lxml')
    major_rows = soup.find_all('tr')
    major_codes = dict()
    for row in major_rows:
        data = row.find_all('td')
        try:
            major_codes[data[-1].text] = data[-2].text
        except:
            continue
    return major_codes

#returns prerequisites for a course
def get_prerequisites(course):
    course_list = json.load(open("course_info.json", "r"))
    return course_list[course]

#Supposed to show progression of courses in a tree like manner
def get_class_tree(course, course_list):
    prerequisites = get_prerequisites(course, course_list)
    if prerequisites[0] == "none":
        return "none"
    else:
        return {prerequisite: get_prerequisites(prerequisite, course_list) for prerequisite in prerequisites}

#Reworked version of get_info_from_links to simplify for first version
def get_course_info():
    links = json.load(open("links.json"))
    all_data = {}
    for link in links["links"]: 
        course_info = get_info_from_links(link)
        all_data.update(course_info)
    outfile = open('course_info.json', 'w')
    outfile.write(json.dumps(all_data, indent=4))

#Scrapes 4 year plans and cross compares them
def scrape_major_requirements(major):
    links = [f"https://plans.ucsd.edu/controller.php?action=LoadPlans&college={college}&year=2022&major={major}" for college in ["WA", "RE", "SI", "MU"]]
    classes = []
    for link in links:
        request = requests.get(link)
        response_data = request.json()
        try:
            courses = response_data[0]["courses"]
        except:
            break
        temp_classes = []
        for years in courses:
            for year in years:
                for course in year:
                    temp_classes.append(course["course_name"])
        if classes == []:
            classes = temp_classes
        else:
            classes = [value for value in classes if value in temp_classes]
        
    return sort_classes(classes)

#converts every course into a numerical value
def sort_classes(classes):
    letter_values = {"A": .1, "B": .2, "C": .3, "D": .4, "E": .5, "F": .6, "G": .7, "H": .001}
    course_codes = json.load(open("course_codes.json", "r"))
    class_values = dict()
    letters = []
    for course in classes:
        parts = course.split()
        try:
            part_one = course_codes[parts[0]] * 100000
        except:
            part_one = 0
        try:
            part_two = int(parts[1].replace("*", ''))
        except:
            try:
                values = list(parts[1])
                counter = 0
                for value in values:
                    try:
                        int(value)
                        counter = counter + 1
                    except:
                        break
                h1 = int(parts[1][:counter+1])
                h2 = parts[1][counter+1:]
                parts_h2 = list(h2)
                h2 = sum([letter_values[x] for x in parts_h2])
                part_two = h1+h2
            except:
                part_two = 0
        class_values[course] = part_one + part_two
    sorted_courses = sorted(class_values, key = lambda x: class_values[x])
    course_values = [class_values[i] for i in sorted_courses]
    division = [2 if int(str(i)[-3:]) > 99 else 0 if int(str(i)[-3:]) < 99 else 1 for i in course_values]
    sorted_courses = dict(zip(sorted_courses, division))
    upper = []
    lower = []
    electives = []
    for k,v in sorted_courses.items():
        if v == 2:
            upper.append(k)
        elif v == 1:
            lower.append(k)
        else:
            electives.append(k)
    return {"lower": lower, "upper": upper, "electives": electives}




#Gets list of course codes and alphabetizes them, to be used to show properly sorted courses   
def get_course_sorter():
    courses_list = json.load(open("course_info.json", "r"))
    course_codes = list(set([course.split()[0] for course in list(courses_list.keys())]))
    course_codes = sorted(course_codes)
    course_codes = {i:j+1 for j,i in enumerate(course_codes)}
    outfile = open("course_codes.json", "w")
    outfile.write(json.dumps(course_codes, indent=4))

#Gets the course thingy ie."dsc 10" or "cse 8A"
def get_course_thingy():
    course_prereqs = json.load(open("course_prereqs.json"))
    course_titles = list(course_prereqs.keys())
    course_thingys = [i.split(".")[0] for i in course_titles]
    outfile = open("course_ids.json", "w")
    outfile.write(json.dumps(course_thingys, indent = 4))

from datetime import datetime
import csv
#Gets the pass value
def get_pass(course):
    rows = []
    with open (f'{course}.json') as infile:

        csvreader = csv.DictReader(infile)

        for row in csvreader:
            rows.append(row)
    
infile = json.load(open("major_requirements.json", "r"))
data = {}
for k,v in infile.items():
    data[k] = sorted(v["lower"] + v["upper"] + v["electives"])

outfile = open("temp.json", "w")
outfile.write(json.dumps(data, indent = 4))