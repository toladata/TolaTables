This file will be a guide on how write an independent app that allows users
to import data from a data system of your choosing.

#App folder
Goes in datasources/

#Your Apps readme
Additionally the admin will need to put the name of the app in the base.py file. For testing
purposes you will have to do that manually. The base.py is contained within:
tola/settings

#static files
Goes in YOUR_APP/static/

#html files
Goes in YOUR_APP/templates

#add your data source to dropdown file

#new models

#using existing models
To use existing models use this import
from silo.models import <Model name here>

#dropdown menu
tolatables will automatically 
