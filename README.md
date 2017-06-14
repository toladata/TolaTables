

Tola Tables [![Build Status](https://travis-ci.org/toladata/TolaTables.svg?branch=master)](https://travis-ci.org/toladata/TolaTables)
====
Share, Load, Edit and Display data from various mobile data collection platforms.

The Read app is intended for use with FormHub data collection platform.  You should be able
to add an additional app using Read as a template to import data or create new "reads"
from other data sources.  You only need to import the new app, add the new read templates
and update the base template to include your new app as sub-navigation to the main read.

Feed: A new JSON or XML feed of one or more aggregated data sources<br>
Read: A data source to load data into the system from<br>
Silo: A data store that can combine one or more Feeds (Data sources)<br>
Display: Where data is viewed and edited<br>

## Configuration
Ensure that the configuration files (`.secret`, `.secret.yml`) are in the `config` folder.

## To deploy changes in tables servers
Once all your changes have been commited to the repo, and before pushing them, run:
`. travis.sh`

## To deploy locally
Run the following commands from the root of this repository:
  - `docker-compose build`
  - `docker-compose up -d mysqldb`
  - `docker-compose up`

## Files added for the Docker version

/
 - Dockerfile
 - docker-compose.yml
 - travis.sh
 - docker.sh

/config
 - nginx.conf
 - mysql.env.secret (not public)
 - settings.secret.yml (not public)

/local/settings
 - local.py

/silo
 - client_secrets.json (not public)



## USING virtualenv
mkdir tolatables
cd tolatables
(Install virtualenv)
pip install virtualenv

# Create Virtualenv
virtualenv venv
* use no site packages to prevent virtualenv from seeing your global packages

source venv/bin/activate
* allows us to just use pip from command line by adding to the path rather then full path

##Activate Virtualenv
source venv/bin/activate

## Fix probable mysql path issue (for mac)
export PATH=$PATH:/usr/local/mysql/bin
* or whatever path you have to your installed mysql_config file in the bin folder of mysql

pip install -r requirements.txt

## Set up DB
python manage.py makemigrations
python manage.py migrate

##load starting data into db
Load all the files contained within:
python manage.py loaddata fixtures/
with:
python manage.py loaddata <filepath>


# Run App
If your using more then one settings file change manage.py to point to local or dev file first
python manage.py runserver 0.0.0.0:8000
GOOGLE API
sudo pip install --upgrade google-api-python-client
* 0’s let it run on any local address i.e. localhost,127.0.0.1 etc.

#Filtering data from the api endpoint
To filter data from api/silos/#{pk}/data endpoint add a mongodb query to the modifier at the end
of the url
Ex. api/silo/2/data?query={"nm":"Henry"}
More advanced query language can be found at https://docs.mongodb.com/manual/
