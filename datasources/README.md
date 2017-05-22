This file will be a guide on how write an independent app that allows users
to import data from a data system of your choosing.

#App folder
Goes in datasources/

#Your Apps readme
In order for the tolatables to read the your apps urls, the tolatables admin must paste a way to
find your apps urls. To accomplish this in your readme put a line for the tolatables admin to paste
in the tola/urls.py . It should look something like:

url(r'YOUR_APP/', include('datasources.YOUR_APP.urls')),

#static files
Goes in datasources/YOUR_APP/static/

#html files
Goes in datasources/YOUR_APP/templates

#add your data source to dropdown file

#new models

#using existing models



#running the server
before running the server you will want to put your static files into a place TolaTables can access
from the TolaTables directory run python manage.py collectstatic

Read up on:
  template finders in the django settings
  collect static command manage.py
