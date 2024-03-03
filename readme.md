# Grocery Store App

This is a simple Grocery Store web application built using Flask, Flask-SQLAlchemy, Redis, Celery, Vue.js, and other technologies.

## Table of Contents

- [Grocery Store App](#grocery-store-app)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Usage](#usage)
  - [Contributing](#contributing)
  - [License](#license)

## Features

- Browse and search for grocery products
- Add products to the cart
- View and update cart contents
- Place an order
- Asynchronous processing of orders using Celery and Redis
- Asynchronous monthly and daily reminders using Celery and Redis
- Axios for sending requests to the backend server
- Store manager signup/login pages
- Admin login to manage categories and products
- JWT-based token authentication
- Dedicated button to download the report file for store managers
## Requirements
1. Install the Python version (Python 3.9) if not already installed. You can download it from the official Python website: Python Downloads

2. Install backend dependencies using pip:
    ```sh
    pip install -r requirements.txt
    ```
3. Install and set up Redis:
   * Linux:
  
        ```sh
        sudo apt-get update
        ```

        ```sh
        sudo apt-get install redis-server
        ```

        ```sh
        sudo systemctl start redis-server
        ```
   * Macos
            
        ```sh
        brew install redis
        ```

        ```brew services start redis```
4. Install Celery with Redis backend:
    
    ```sh
    pip install celery[redis]
    ```
5. Install frontend dependencies using npm(In Main Folder):
    ```sh
    npm install
    ```
6. Install frontend dependencies using npm(Inside Frontend Folder):
    
    ```sh
    npm install
    ```
7. Install vue-toast-notification
   
    ```sh
    npm install vue-toast-notification
    ```
8. Install Flask and Flask extensions:

    ```sh
    pip install Flask Flask-SQLAlchemy Flask-JWT-Extended Flask-Caching Flask-Cors
    ```
## Usage

To run the Grocery Store app, follow these steps:

1. Open your terminal.

2. Navigate to the root `Documents` directory or move your project folder there:

    ```sh
    cd ~/Documents/grocery-store-app
    ```

3. Ensure the `run_files.sh` script has execute permissions. If not, grant permissions using:

    ```sh
    chmod +x run_files.sh
    ```

4. Run the `run_files.sh` script:

    ```sh
    ./run_files.sh
    ```

This will start the Redis server, Celery worker, Flask development server, and Vue.js development server. Open your web browser and navigate to `http://localhost:8080` to access the Grocery Store app.

**Note:** Before running the `run_files.sh` script, make sure to check the path of your project folder.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).
