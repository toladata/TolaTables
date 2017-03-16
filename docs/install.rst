Install
========

TolaTables extends the functionality of TolaData to include a set of tools for collecting, aggregating, cleaning and
editing data from various 3rd party data sources.

## Configuration
Copy the local-sample.py file and rename it to local.py
Change the data base variables to match your local MySQL data bane

## USING virtualenv
(Install virtualenv)
pip install virtualenv

# Create Virtualenv
virtualenv —no-site-packages venv
* use no site packages to prevent virtualenv from seeing your global packages

. venv/bin/activate
* allows us to just use pip from command line by adding to the path rather then full path

##Activate Virtualenv
source venv/bin/activate

## Fix probable mysql path issue (for mac)
export PATH=$PATH:/usr/local/mysql/bin
* or whatever path you have to your installed mysql_config file in the bin folder of mysql

pip install -r requirements.txt

## Set up DB
python manage.py migrate

## MongoDB
Use default MongoDB collcetion
mongod

# Run App
If your using more then one settings file change manage.py to point to local or dev file first
python manage.py runserver 0.0.0.0:8000
GOOGLE API
sudo pip install --upgrade google-api-python-client
* 0’s let it run on any local address i.e. localhost,127.0.0.1 etc.


