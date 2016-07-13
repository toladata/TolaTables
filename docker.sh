
#!/bin/bash

### It dockerizes automatically ###
cd /home/TolaTables
git stash
git pull origin master

docker-compose build 
docker-compose up -d mysqldb
sleep 15
docker-compose up
