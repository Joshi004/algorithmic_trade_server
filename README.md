# algorithmic_trade_server
---
Steps To Setup 

1. Clone The Application 
2. Activate ats_env virtual enviornment for python
    source ats_env bin/activate
3. Run server with following command
    pip install -r requirements.txt
    python manage.py runserver

3. Also make sure the all the migrations are applied before you run the server
    python manage.py makemigrations
    python manage.py migrate

 For The migrations to run make sure you have MySQL setup on your local
     Required version - Ver 8.0.32

---

To Install MySQL on MAC you can use brew
    brew update
    brew install mysql@8.0.32
    After the installation is complete, you can start the MySQL service:
        brew services start mysql@8.0.32
    
    mysql_secure_installation
### This command will guide you through the process of setting a root password, removing anonymous users, disallowing remote root login, and removing the test database. You can choose the options that suit your needs.

    mysql -u root -p
#### You will be prompted to enter the root password you set during the secure installation process.

### Make sure you have a database named ats_db before runing the migrations

---
## Also You would neeed Redis installed so that channals can work properly


### Open a terminal on your macOS.
### Update Homebrew to make sure you have the latest version by running the following command:

brew update

# Install Redis by running the following command:

brew install redis
### After the installation is complete, you can start the Redis server by running the following command:

brew services start redis

### This will start the Redis server in the background.

### To verify that Redis is running, you can use the Redis CLI. Open a new terminal window and run the following command:

redis-cli ping
### If Redis is running properly, you will see the response PONG.
### That's it! Redis is now installed and running on your macOS system. You can use the Redis CLI or connect to Redis from your applications.

