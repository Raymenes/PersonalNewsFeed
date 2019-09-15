# Helpful links:
## Mongodb related
```
official documentation: 
http://api.mongodb.com/python/current/tutorial.html
shell command: 
https://dzone.com/articles/top-10-most-common-commands-for-beginners

to manually run mongodb on local host:
$brew install mongodb
$mongod --config /usr/local/etc/mongod.conf
```

## Docker related
```
Get started with Docker Compose: 
https://docs.docker.com/compose/gettingstarted/

Elastic Bean Stalk with Docker: 
https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/single-container-docker.html
```

## Elastic Beanstalk related
```
https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/create-deploy-python-flask.html

https://medium.com/@pbojinov/elastic-beanstalk-and-flask-c51e10de7fe0
```

## Start server
1. $mongod --config /usr/local/etc/mongod.conf
2. $python app.py

## Start docker
1. cd /PersonalNewsFeed
2. $sudo docker-compose build 
3. $sudo docker-compose up

## EB CLI
- eb deploy (after making any change and saved the file, just this command would deploy the latest app version to eb env)
- eb ssh