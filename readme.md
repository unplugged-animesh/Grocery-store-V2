# MyGrocery App

The Grocery Store is an online platform for buying various food products in different categories. The categories are created and managed by the store admin.Products are managed by the store manager.He can Add,Update and Delete multiple products in categories.Buyers can easily search their categories and respective products.

## Table of Contents

- [ MyGrocery App](#my-grocery-app)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Usage](#usage)
  - [Contributing](#contributing)
  - [License](#license)

## Features

- User Signup and Login (Token Based)
- Separate Signup and login for admin and store manager.Only one admin with admin key.
- First of all the Store Manager has to  sign up and the admin can approve the Store manager. After that, the store manager can login with the store manager key.
- Creation ,update and deletion of Categories by admin.
- Creation ,update and deletion of Products by Store-manager.
- Store manager can export a csv File regarding his inventory.
- Users can add multiple products at one time.
- Users can search any product and categories by name.
- If User is not buy anything from the store so We will send them reminder mails.
- Monthly report for users for their purchased items and expenditure.
- Users can update any product directly and their amount is also incremented in cart.
- Users can directly delete any item from the cart.
- If any product is finished so you can not add in cart.Show “Out of stock”
- Final checkout page and total amount is shown before placing order.


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
5. Install frontend dependencies using npm:
    
    ```sh
    npm install
    ```

6. Install Flask and Flask extensions:

    ```sh
    pip install Flask Flask-SQLAlchemy Flask-JWT-Extended Flask-Caching Flask-Cors
    ```
## Usage

To run the My Grocery app, follow these steps:

1. Open new terminal when you want to run below codes.
 * Use Cd command for mygrocery folder
     ```sh
    npm run serve
    ```
* Use mygrocery /Backend For running backend code
    
    ```sh
    python3 app.py
    ```

    ```sh
   mailhog
    ```
    
    ```sh
   celery -A app.celery worker -l info
    ```
    ```sh
    celery -A app.celery beat --max-interval 1 -l info
    ```

These command start my backend code using python and frontend code using vuejs.
For daily reminders and monthly report  i use mailhog and celeryworker and celery beat.
This is my `http://localhost:8080` to access the My Grocery app.


## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).
