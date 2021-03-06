import os
import re
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


# ======== VALIDATION  FUNCTIONS ======== #


def validate_username(username):
    # Validate username.
    # Allow letters, hyphens, numbers and underscores. Length 5-15 chars.
    return re.match("^[a-zA-Z0-9-_]{5,15}$", username)


def validate_password(password):
    # Validate password.
    # Allow any character, length 5-15 chars.
    return re.match("^.{5,15}$", password)


def validate_recipe_name(recipe_name):
    # Validate recipe name.
    # Allow any character, 5- 100 characters.
    return re.match("^.{5,100}$", recipe_name)


def validate_recipe_description(recipe_description):
    # Validate recipe ingredients.
    # Allow any character. 5- 1000 characters.
    return re.match("^.{5,1000}$", recipe_description)


def validate_recipe_instructions(recipe_instructions):
    # Validate recipe instructions.
    # Allow any character. 5-1000 characters.
    return re.match("^.{5,1000}$", recipe_instructions)


def validate_recipe_image(recipe_image):
    # Validate recipe ingredients and recipe instructions.
    # Allow any character between 5-200 characters.
    return re.match("^.{5,200}$", recipe_image)


# ======== CONFIG ======== #


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


# ======== HOME ======== #


@app.route("/")
@app.route("/get_recipes")
def get_recipes():
    # find list of all recipes from db
    recipes = list(mongo.db.recipes.find())
    # display them for all users, logged in or not
    return render_template("recipes.html", recipes=recipes)


@app.route("/search", methods=["GET", "POST"])
def search():
    # when data entered in search form
    query = request.form.get("query")
    # query database for contents of search
    recipes = list(mongo.db.recipes.find({"$text": {"$search": query}}))
    # display results of matches
    return render_template("recipes.html", recipes=recipes)


# ======== USERS ======== #


@app.route("/register", methods=["GET", "POST"])
def register():
    # Check if the message is POST
    if request.method == "POST":
        # Validate data in username
        if request.form.get("username") == "" or not validate_username(
                request.form.get("username")):
            flash("Please enter a valid username: letters,hyphens, nrs and _")
            return redirect(url_for("register"))
        if request.form.get("password") == "" or not validate_password(
           request.form.get("password")):
            flash("Please enter a valid password: any char between 5-15 chars")
            return redirect(url_for("register"))

        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})
        # If it does, flash message informing user username is taken.
        if existing_user:
            flash("This username is already taken")
            return redirect(url_for("register"))

        # Insert new user registration into database with data provided
        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie and flash confirmation
        session["user"] = request.form.get("username").lower()
        flash("User successfully registered")
        # redirect to account page
        return redirect(url_for("account", username=session["user"]))

    # If method is not POST, check if user exists in session variable
    if session.get("username"):
        # If so, redirect user to account page and display flash message
        flash("You are already a registered user")
        return redirect(url_for("account", username=session["user"]))
    # Else, redirect to registration page
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Check if username exists in session variable
    if session.get("username"):
        # If so, redirect user to account page and flash message.
        flash("You are already signed in as " +
              session["user"])
        return redirect(url_for(
            "account", username=session["user"]))

    # Else, check if method is POST
    if request.method == "POST":
        # Validate if the data provided is correct
        if request.form.get("username") == "" or not validate_username(
           request.form.get("username").lower()):
            flash("Please enter a valid username")
            return redirect(url_for("login"))
        if request.form.get("password") == "" or not validate_password(
           request.form.get("password")):
            flash("Please enter a valid password")
            return redirect(url_for("login"))
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})
        # if user exists in database:
        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                    session["user"] = request.form.get("username").lower()
                    # flash success message
                    flash("Hi, {}!".format(
                        request.form.get("username")))
                    # redirect to account
                    return redirect(url_for(
                        "account", username=session["user"]))
            else:
                # invalid password match:flash message and return to login page
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))
        # username doesn't exist in db: flash message and return to login page
        else:
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))
    # if method is not POST: render signin.html template
    return render_template("login.html")


@app.route("/account/<username>", methods=["GET", "POST"])
def account(username):
    # get session user's username from the db
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    # show username in session their page
    if session["user"]:
        return render_template("account.html", username=username)
    # or else send them to login page
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    # remove the user from session cookie
    flash("You are now logged out")
    session.pop("user")
    # redirect to login page
    return redirect(url_for("login"))


@app.route("/delete_account/<username>")
def delete_account(username):
    # get session user's username from the db
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    # if username in session is same delete the account
    mongo.db.users.remove({"username": username.lower()})
    flash("Your account has been deleted")
    session.pop("user")
    return redirect(url_for("register"))


# ======== RECIPES ======== #


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    # if form has been filled and submitted get these and add to db
    if request.method == "POST":
        recipe = {
            "recipe_name": request.form.get("recipe_name"),
            "recipe_description": request.form.get("recipe_description"),
            "recipe_ingredients": request.form.get("recipe_ingredients"),
            "recipe_instructions": request.form.get("recipe_instructions"),
            "category_name": request.form.get("category_name"),
            "recipe_difficulty": request.form.get("recipe_difficulty"),
            "recipe_image": request.form.get("recipe_image"),
            "created_by": session["user"]
        }
        mongo.db.recipes.insert_one(recipe)
        # flash confirmation message
        flash("Your recipe has been added!")
        # redirect to main recipe page
        return redirect(url_for("my_muffins"))

    # if form was not submitted
    categories = mongo.db.categories.find().sort("category_name", 1)
    # get recipe difficulty level from the db
    levels = mongo.db.levels.find().sort("recipe_difficulty", 1)
    return render_template(
        "add_recipe.html", categories=categories, levels=levels)


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    # if form has been filled and submitted add edits to db
    if request.method == "POST":
        submit = {
            "recipe_name": request.form.get("recipe_name"),
            "recipe_description": request.form.get("recipe_description"),
            "recipe_ingredients": request.form.get("recipe_ingredients"),
            "recipe_instructions": request.form.get("recipe_instructions"),
            "category_name": request.form.get("category_name"),
            "recipe_difficulty": request.form.get("recipe_difficulty"),
            "recipe_image": request.form.get("recipe_image"),
            "created_by": session["user"]
        }
        mongo.db.recipes.update({"_id": ObjectId(recipe_id)}, submit)
        # flash confirmation message
        flash("Your recipe has been edited")

    # if form was not submitted with edits
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    categories = mongo.db.categories.find().sort("category_name", 1)
    levels = mongo.db.levels.find().sort("recipe_difficulty", 1)
    # return to edit page
    return render_template(
        "edit_recipe.html", recipe=recipe, categories=categories,
        levels=levels)


@app.route("/delete_recipe/<recipe_id>")
def delete_recipe(recipe_id):
    # remove this recipe id from db
    mongo.db.recipes.remove({"_id": ObjectId(recipe_id)})
    flash("This recipe has been deleted")
    # redirect to main page
    return redirect(url_for("get_recipes"))


@app.route("/my_muffins")
def my_muffins():
    # sort muffins by user who created them
    recipes = mongo.db.recipes.find().sort("created_by")
    # display list of user's muffins
    return render_template("my_muffins.html", recipes=recipes)


# ======== ERROR PAGES ======== #


@ app.errorhandler(404)
def not_found(error):
    # Displays 404 error page
    return render_template("404.html"), 404


@ app.errorhandler(505)
def internal(error):
    # Displays 505 error page
    return render_template("505.html"), 505


# ============================================ #


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=False)
