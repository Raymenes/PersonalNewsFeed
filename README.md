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
1. $source virt/bin/activate  # activate python venv
2. $pip freeze > requirements.txt 
3. $eb init -p python-3.6 flask-tutorial --region us-east-2 # if creating eb app for the 1st time
4. $eb deploy (after making any change and saved the file, just this command would deploy the latest app version to eb env)
5. $eb init && eb ssh # to ssh into host