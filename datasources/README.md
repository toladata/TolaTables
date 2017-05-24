This file will be a guide on how write an independent app that allows users
to import data from a data system of your choosing.

#App folder
Goes in datasources/

#Your Apps readme
In order for your app to run it must be in the list of apps:
put the name of your app in the LOCAL_APPS list in the tola/settings/base.py file

#static files
Goes in YOUR_APP/static/

#template files
Goes in YOUR_APP/templates

#new models

#using existing models
To use existing models use this import
from silo.models import <Model name here>

#navigating to your page
By default tolatables will create a subdomain for use in your apps urls.py file. The name of this
subdomain is your apps name.
In addition tolatables will automatically add a link to your app on the import data dropdown menu.
It'll be of the form "Import from YOUR_APPS_NAME". If you wish to change what appears in
YOUR_APPS_NAME add:
  verbose_name = "NEW_NAME"
to the apps.py file

#to add your type
In order for tola to read your filetype you need to add the read type to the silo_readtype database