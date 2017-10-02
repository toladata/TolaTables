

Tola Tables [![Build Status](https://travis-ci.org/toladata/TolaTables.svg?branch=master)](https://travis-ci.org/toladata/TolaTables)
====
Share, load, edit and display data from various mobile data collection platforms.
The data itself is stored in MongoDB but metadata and dashboarding is done through
Django and a relational database.  The Silo app provides most of the functionality.
It stores data source and destination locations, manages the data import process,
and manages permissions and other meta-processes.


After login, the user can choose to import data from several different platforms,
including Google Sheets, Ona, and CommCare.  Data from multiple sources can be
combined into a single table (aka Silo).

## Installation
```
git clone https://github.com/toladata/TolaTables.git
cd TolaTables
```

## Configuration
First copy the sample config files:

```
cp tola/settings/local.example.py tola/settings/local.py
cp silo/client_secrets_example.json silo/client_secrets.json
cp fixtures/sites.json fixtures/sites_local.json
cp fixtures/tolasites.json fixtures/tolasites_local.json
cp fixtures/tags.json fixtures/tags_local.json
cp fixtures/read_types_.json fixtures/read_types_local.json
```

Once copied, modify all new files to suit your own particular installation and
organization.  The local.py file contains Django settings, client_secrets.py contains Google Auth related settings, and the fixture files are a starter set of metadata for your organization.  You will need to load the sites and tolasites fixtures in order to run Tola, and loading read_types is required for importing data.

If you have password protected your MongoDB database, you will need to update the settings in the local.py file to match your setup.  If you have not password protected the MongoDB instance, you can comment out the MONGODB section in local.py and uncomment the same section in base.py.  

Once you are done configuring the fixtures you can load them:
```
./manage.py loaddata sites_local
./manage.py loaddata tolasites_local
./manage.py loaddata tags_local
./manage.py loaddata read_types_local
```


## Deploy using Virtualenv
Virtualenv allows us to customize an encapsulated version of python to use with your app.

### Install and use a Virtualenv
First install Virtualenv to you system python installation, then initiate a python virtual environment and load the required python modules.
```
pip install virtualenv
cd ..
virtualenv --no-site-packages venv
source venv/bin/activate
```
You should now see '(venv)' added to the left side of your prompt.  If you don't, you have not successfully activated the Virtualenv.

Now install the python modules into the Virtualenv:

`pip install -r TolaTables/requirements.txt`

### Install selenium
You may need to install [selenium](http://www.seleniumhq.org/) as well.  On a Mac, the easiest way is to run
`brew install selenium`

### Fix probable mysql path issue (for Mac)
Some MacOS systems have trouble seeing the MySql installation.  If you are using MySql, you may need to run this command.

`export PATH=$PATH:/usr/local/mysql/bin`

### Set up the Database
`python manage.py migrate`

### Install and start application servers
This App uses Celery and RabbitMQ as a queueing system for certain data imports and stores data in a MongoDB database.  All of these applications require their own servers to be running concurrently with your main application server.  These instructions enable you to run interactive servers from the command-line on your local computer;  you will eventually have four servers running at once.  For server environments (and for your local development environment if you choose), you will likely daemonize these services.

#### Install and run RabbitMQ
Follow the [RabbitMQ installation guide](http://docs.celeryproject.org/en/latest/getting-started/brokers/rabbitmq.html#setting-up-rabbitmq).  For macOS, if you have homebrew installed, you should be able to `brew install rabbitmq`. Once RabbitMQ is installed you can start the server with `rabbitmq-server` and stop it with `rabbitmqctl stop`.

#### Start Celery worker
The Celery library should have been installed with the rest of the python packages you installed earlier.  You can start celery worker using `celery -A tola  worker -l info`. For more information check out its [documentation](http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html#using-celery-with-django).

#### Start MongoDB
MongoDB uses `/data/db` as the default directory for its database files and if you run a bare `mongod` command, your data will go into that directory.  If you wish to use a different directory, you can run `mongod --dbpath <path/to/your/dir>`, as described in the MongoDB [docs](https://docs.mongodb.com/manual/tutorial/install-mongodb-on-os-x/#run-mongodb).  Your data directory should be outside of the TolaTables repository.

### Start Django devserver
If your using more then one settings file change manage.py to point to local or dev file.  Then run
`python manage.py runserver`

## Using Tola
If you use your browser to navigate to `localhost:8000`, you should now find a Tola login screen.

### Filtering data from the api endpoint
To filter data from api/silos/#{pk}/data endpoint add a mongodb query to the modifier at the end
of the url
Ex. api/silo/2/data?query={"nm":"Henry"}
More advanced query language can be found at https://docs.mongodb.com/manual/
To sort data data add onto the url sort=<column_name> for ascending or sort=-<column_name> for
descending

## Updating to 0.9.2
0.9.2 changes the way data is stored in MongoDB to increase efficiency and reduce storage space. To accommodate these changes it is necessary to run the collect_silo_columns command otherwise no data will show up in TolaTables. 0.9.2 adds indexes to the MongoDB to make reading and writing faster. To enforce this change run the add_indexes_for_silos command.

## Testing
Do not run unit tests on a production database. Django is not set up to make a test MongoDB so data is added and removed from the MongoDB in settings. Any data with silo_id 1 will be damaged or deleted.
