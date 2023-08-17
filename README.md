
# Algorithmic Trade Server
---
This is a project that allows you to perform algorithmic trading using a web-based interface. You can use various strategies and indicators to execute trades on different markets and platforms. To set up this project, you need to follow these steps:

1. Clone the application from GitHub using the following command:
    ```
    git clone https://github.com/your_username/algorithmic_trade_server.git
    ```
2. Activate the `ats_env` virtual environment for Python using the following command:
    ```
    source ats_env/bin/activate
    ```
3. Install the required dependencies using the following command:
    ```
    pip install -r requirements.txt
    ```
4. Make sure you have MySQL installed and running on your local system. You need MySQL version 8.0.32 or higher for this project. To install MySQL on macOS, you can use Homebrew as follows:
    - Update Homebrew to make sure you have the latest version by running the following command:
        ```
        brew update
        ```
    - Install MySQL by running the following command:
        ```
        brew install mysql@8.0.32
        ```
    - After the installation is complete, you can start the MySQL service by running the following command:
        ```
        brew services start mysql@8.0.32
        ```
    - Run the `mysql_secure_installation` command to set a root password, remove anonymous users, disallow remote root login, and remove the test database. You can choose the options that suit your needs.
    - Connect to MySQL as root by running the following command and entering the root password you set during the secure installation process:
        ```
        mysql -u root -p
        ```
5. Create a database named `ats_db` in MySQL using the following command:
    ```
    CREATE DATABASE ats_db;
    ```
6. Apply the migrations to create the necessary tables and indexes in the database using the following commands:
    ```
    python manage.py makemigrations
    python manage.py migrate
    ```
7. Make sure you have Redis installed and running on your local system. You need Redis for handling WebSocket connections and channels. To install Redis on macOS, you can use Homebrew as follows:
    - Update Homebrew to make sure you have the latest version by running the following command:
        ```
        brew update
        ```
    - Install Redis by running the following command:
        ```
        brew install redis
        ```
    - After the installation is complete, you can start the Redis server by running the following command:
        ```
        brew services start redis
        ```
    - To verify that Redis is running, you can use the Redis CLI by running the following command in a new terminal window:
        ```
        redis-cli ping
        ```
      If Redis is running properly, you will see the response `PONG`.
8. Start the server using Daphne, which is an asynchronous HTTP, HTTP2 and WebSocket protocol server for Django and ASGI applications. You need Daphne to work with WebSocket connections and channels. To start the server using Daphne, run the following command:
    ```
    daphne ats_base.asgi:application
    ```

That's it! You have successfully set up the algorithmic trade server project on your local system. You can now access it from your browser and start trading with your preferred strategies and indicators. Happy trading! 😊