# Tasksly Productivity Website

## Overview
Tasksly is a web application designed to streamline task management, facilitate focus session logging, and encourage productivity streaks. This project is implemented using Flask, a Python web framework, and SQLite for secure data storage. It incorporates features such as user authentication with password hashing to ensure data integrity and user security.

## Requirements
- Python
- Flask
- SQLite



#### Video Demo:  https://youtu.be/I8jnLB6InSI
#### Description:
It is a website that allows users to register and log in to access the productivity website. 

In this website, users can aim to improve and track their productivity day by day through setting their own goals and working towards the goals. To do this, users can add tasks on the tasks page and which allows them to start focus sessions with the tasks they have added. 

On the register page, the website will ask the user for their desired username, password and a password confirmation. If the user chooses a username that is too short, the website will prompt them to choose a longer one. If the user registers with a username that is already taken, the website will prompt them to choose an alternate username while giving them 3 suggestions that either have numbers added at the back or changing the upper or lower casing of the letters. The password also has a minumum character requirement as well as needed at least a number in the password. Once the user enters eligible username and password, the password will be encrypted with a unique key to the user and stored in the database. This allows for extra security since each user has a different key that encrypts their password. 

On the tasks page, users can also edit the tasks goal duration if they ever wish to change their desired goals for the task or even delete the tasks if they wish to. 

On the homepage, the website greets the user and displays a real time clock, as I believe that having the time displayed clearly on the screen will urge the user to focus better, leading to better productivity. Apart from those, the homepage also displays the tasks that the user has added and its remaining durations for the day along with the user's three most recent focus sessions. This gives the users a very clear view of how long they have focussed in that day, and how long more they have before they meet their goal. 

On the focussing page, it is a timer that counts up how long the user has been in the focus session along with the name of the task they are focussing on. I have made the timer to change its colour like a gradient to boost the aesthetics of the page. Once they click the "Stop" button, the user is met with two more buttons, "Resume" and "Save". As the names suggest, "Resume" allows the user to continue the focus session while "Save" saves the time the user has focussed to the database.

On the streaks page, users can view how many days in a row they have completed each individual tasks along with how many days in a row they have completed every task. This motivates them to meet their daily goals so as to preserve the streak that they have. 

Finally, on the history page, users can delete the focus sessions of that day only, while being able to view their past focus sessions. So users can still delete their focus sessions if they were done accidentally within the day, but will be saved permanently after the day has ended. 

In my project folder, the templates folder contains all the HTML templates for each page of my website. The static folder holds the CSS elements that style my project. app.py is the main file that runs my website while helpers.py has some additional functions I have made that would clog up the main app.py file which is why I created a seperate file for them.
