#!/usr/bin/env python

from flask import Flask, render_template, request, redirect, jsonify, url_for
from flask import flash, make_response
from flask import session as login_session
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Category, Book
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import random
import string
import json
import requests

app = Flask(__name__)

# Load the Google Sign-in API Client ID.
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

# Connect to Database and create database session
engine = create_engine(
    'sqlite:///bookcatalog.db',
    connect_args={'check_same_thread': False}
)

Base.metadata.bind = engine

Session = sessionmaker(bind=engine)
session = Session()


# Create anti-forgery state token
@app.route('/login')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps
                                 ('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # See if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    return output


@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = redirect(url_for('home'))
        flash("You are now logged out.")
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# User Helper Functions

def createUser(login_session):
    # Create new user
    newUser = User(
        name=login_session['username'],
        email=login_session['email'],
        picture=login_session['picture']
        )
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    # Get user information by id
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    # Get user id by email
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Redirect to login page.
@app.route('/')
@app.route('/home/')
def home():

    categories = session.query(Category).all()
    books = session.query(Book).all()
    return render_template(
        'home.html', categories=categories)


# Create a new Category
@app.route('/home/new/', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        # If user is not logged redirect to login page
        return redirect(url_for('login'))
    if request.method == 'POST':
        newCategory = Category(name=request.form['name'])
        session.add(newCategory)
        session.commit()
        return redirect(url_for('home'))
    else:
        return render_template('newCategory.html')


# Edit a existing category
@app.route('/home/<int:category_id>/edit/', methods=['GET', 'POST'])
def editCategory(category_id):
    editedCategory = session.query(Category).filter_by(id=category_id).one()
    if 'username' not in login_session:
        # If user is not logged return to login page
        return redirect(url_for('login'))
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = request.form['name']
            flash("Category successfully edited")
            return redirect(url_for('home'))
    else:
        return render_template('editCategory.html', category=editedCategory)


# Delete Category
@app.route('/home/<int:category_id>/delete/', methods=['GET', 'POST'])
def deleteCategory(category_id):
    categoryToDelete = session.query(Category).filter_by(id=category_id).one()
    if 'username' not in login_session:
        # If user is not logged redirect to login page
        return redirect(url_for('login'))
    if request.method == 'POST':
        session.delete(categoryToDelete)
        flash("%s has been successfully deleted!" % categoryToDelete.name)
        session.commit()
        return redirect(url_for('home'))
    else:
        return render_template("deleteCategory.html",
                               category=categoryToDelete)


# Show books of a category
@app.route('/home/<int:category_id>/')
@app.route('/home/<int:category_id>/book/')
def showBook(category_id):
    category = session.query(Category).filter_by(id=category_id).one_or_none()
    books = session.query(Book).filter_by(category_id=category_id).all()
    print books
    return render_template('books.html', category=category, books=books)


# Create a new Book
@app.route('/home/<int:category_id>/book/new/', methods=['GET', 'POST'])
def newBook(category_id):
    if 'username' not in login_session:
        # If user is not logged redirect to login page
        return redirect(url_for('login'))
    if request.method == 'POST':
        book = session.query(Book).filter_by(id=category_id).one()
        new_book = Book(
            name=request.form['name'],
            category_id=category_id,
            description=request.form['description'],
            price=request.form['price']
            )
        session.add(new_book)
        session.commit()
        flash("New book was successfully created!")
        return redirect(url_for('showBook', category_id=category_id))
    else:
        return render_template('newBook.html')
    return render_template('newBook.html', category=category)


# Edit an existing book
@app.route('/home/<int:category_id>/book/<int:book_id>/edit/',
           methods=['GET', 'POST'])
def editBook(category_id, book_id):
    if 'username' not in login_session:
        # If user is not logged redirect to login page
        return redirect(url_for('login'))
    editedBook = session.query(Book).filter_by(id=book_id).one()
    category = session.query(Category).filter_by(id=category_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedBook.name = request.form['name']
        if request.form['description']:
            editedBook.description = request.form['description']
        if request.form['price']:
            editedBook.price = request.form['price']
        session.add(editedBook)
        session.commit()
        flash("Book is successfully edited!")
        return redirect(url_for('showBook', category_id=category_id))
    else:
        return render_template('editBook.html', category_id=category_id,
                               book_id=book_id, book=editedBook)


# Delete a book
@app.route('/home/<int:category_id>/<int:book_id>/delete/',
           methods=['GET', 'POST'])
def deleteBook(category_id, book_id):
    if 'username' not in login_session:
        # If user is not logged redirect to login page
        return redirect(url_for('login'))
    delBook = session.query(Book).filter_by(id=book_id).one()
    if request.method == 'POST':
        session.delete(delBook)
        session.commit()
        flash("Book successfully deleted")
        return redirect(url_for('home', category_id=category_id))
    else:
        return render_template('deleteBook.html', book=delBook)


# JSON API`s

# Return JSON to view all the categories
@app.route('/home/JSON')
def categoryJSON():
    categories = session.query(Category).all()
    return jsonify(categories=[i.serialize for i in categories])


# Return JSON to view all books
@app.route('/home/<int:category_id>/book/JSON')
def bookJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    books = session.query(Book).filter_by(category_id=category_id).all()
    return jsonify(Books=[i.serialize for i in books])


# Return JSON to view a particular book
@app.route('/home/<int:categories_id>/book/<int:book_id>/JSON')
def especificBookJSON(category_id, book_id):
    book = session.query(Book).filter_by(id=book_id).one()
    return jsonify(book=book.serialize)


# End of file
if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    """app.debug = True"""
    app.run(host="0.0.0.0", port=5000)
