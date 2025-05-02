# Algorithmic Trade Server
---
This is a project that allows you to perform algorithmic trading using a web-based interface. You can use various strategies and indicators to execute trades on different markets and platforms.

## Setting Up with Docker (Recommended)

The easiest way to set up the application is using Docker:

1. Clone the application from GitHub using the following command:
   ```
   git clone https://github.com/your_username/algorithmic_trade_server.git
   ```
   
2. Navigate to the project directory:
   ```
   cd algorithmic_trade_server
   ```

3. Build and start the application using Docker Compose:
   ```
   docker-compose up -d
   ```
   
   This will start all required services:
   - The Django application on port 18000 (container name: ats-django-app)
   - MySQL database on port 13306 (container name: ats-mysql-db)
   - Redis for WebSockets on port 16379 (container name: ats-redis-server)
   
4. The application will be available at http://localhost:18000

### Development with Docker

- All your local files are mounted into the Docker container, so you can edit them locally and see changes immediately
- View application logs:
  ```
  docker-compose logs -f ats-app
  ```
- Run migrations:
  ```
  docker-compose exec ats-app python manage.py migrate
  ```
- Run a specific command in the container:
  ```
  docker-compose exec ats-app <command>
  ```
- Stop all services:
  ```
  docker-compose down
  ```
- Reset everything (including volumes):
  ```
  docker-compose down -v
  ```

### Connection Information

- MySQL database:
  - Host: localhost
  - Port: 13306
  - Username: ats_user
  - Password: ats_password
  - Database: ats_db

- Redis:
  - Host: localhost
  - Port: 16379

## Setting Up Manually (Alternative)

If you prefer to set up the application without Docker, follow these steps:

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
