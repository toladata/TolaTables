#!/bin/bash

##### typical packages #########
apt-get update
apt-get install -y vim
apt-get install -y htop
apt-get install -y fail2ban
apt-get install -y s3cmd

##### Clone Github repo ########
git clone https://github.com/toladata/TolaTables

##### docker-compose ###########
curl -L https://github.com/docker/compose/releases/download/1.8.0/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

#### letsencrypt ##############
#apt-get install -y git python
#cd ~ 
#git clone https://github.com/letsencrypt/letsencrypt 
#cd letsencrypt
#service nginx stop
#docker stop tolaactivity_nginx_1/tolatables_nginx_1
#./letsencrypt-auto certonly --standalone --agree-tos --redirect --duplicate --text --email EMAIL -d DOMAINNAME

######### ELK #########
echo "deb https://packages.elastic.co/beats/apt stable main" |  sudo tee -a /etc/apt/sources.list.d/beats.list
wget -qO - https://packages.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
apt-get update
apt-get install -y filebeat
apt-get install -y topbeat
apt-get install -y packetbeat

### Copy important files to server ###
scp TolaTables/config/mysql.env.secret TTSERVERNAME:/home/TolaTables/config/mysql.env.secret
scp TolaTables/config/settings.secret.yml TTSERVERNAME:/home/TolaTables/config/settings.secret.yml
scp TolaTables/ttrestore.sql TTSERVERNAME:/home/TolaTables/ttrestore.sql
scp TolaTables/dump TTSERVERNAME:/home/TolaTables/dump

docker-compose build

### MySQL container ####
docker-compose up -d mysqldb
sleep 5
docker cp ttrestore.sql tolatables_mysqldb_1:/
sleep 20
docker exec tolatables_mysqldb_1 bash -c "mysql -u USER -pPASSWORD tolatables < ttrestore.sql"
sleep 22
docker exec tolatables_mysqldb_1 bash -c "mysql -u USER -pPASSWORD tolatables < ttrestore.sql"

### MongoDB container ####
docker-compose up -d mongodb
docker cp dump tolatables_mongodb_1:/
docker exec tolatables_mongodb_1 bash -c "mongorestore -d dump"

### Rest of containers ###
docker-compose up



