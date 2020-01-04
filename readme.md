# Discord Role Assignment Bot
## Assigning roles since 2019

### What does it do?
This is a JSON configurable bot written in discord.py, that seeks to
automate many role-based inconveniences, it asks questions and assigns
roles based off that, it has a role database that will assign roles,
and even an anonymous complaints system.

### Dependencies
* Python 3
* discord.py (rewrite)
* colorama
* redis (for some modules)
* requests (for the mee6 module)

#### Setup and Configuration
This bot works just like any other one, throw it onto Heroku, AWS, your own personal server, and let it run. Just make sure that the bot is only on one server, since it won't work on multiple in it's current state.

To learn about configuration, check the bundled config.json for help.

