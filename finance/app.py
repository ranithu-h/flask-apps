import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # get current user_id
    id = session["user_id"]
    cash = db.execute("SELECT cash FROM users WHERE id = ?", id)
    balance = cash[0]["cash"]
    balance = round(balance, 3)
    accounts = db.execute("SELECT * FROM accounts WHERE account_id = ? AND number_of_shares >= 1 ", id)

    # show index page
    return render_template("index.html", accounts=accounts, balance = balance)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # get user info
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        id = session["user_id"]
        shares = int(request.form.get("shares"))
        try:
            if shares < 0:
                return apology("Shares cannot be negative")
            elif isinstance(shares, float):
                return apology("Shares cannot be negative")
        except ValueError:
            return apology("Shares must be only integers")

        symbol = request.form.get("symbol")
        quotes= lookup(symbol)
        #cheking for errors
        try:
            cash = db.execute("SELECT cash FROM users WHERE id = ? ", id )
            cash = cash[0]["cash"]
            number_of_shares = db.execute("SELECT number_of_shares FROM accounts JOIN users ON users.id = accounts.account_id WHERE users.id = ? AND symbol = ? ", id, quotes["symbol"])
            cost = round(quotes["price"],3) * float(shares)
        except TypeError:
            return apology("Invalid symbol")

        if float(cash) < cost:
            return apology("Can't Afford It")
        else:
            #checking if the number of shares is empty
            if number_of_shares == []:
                shares_balance = shares
                db.execute("INSERT INTO accounts (account_id,number_of_shares, price, symbol, name) VALUES (?,?,?,?,?)",id, shares_balance, round(quotes["price"],3), quotes["symbol"],quotes["name"] )
            else:
                shares_balance = int(number_of_shares[0]["number_of_shares"]) + shares

            #make changes to database
            balance = float(cash) - cost
            name_of_company = quotes["name"]
            db.execute("UPDATE users SET cash = ? WHERE id = ? ", balance, id )
            db.execute( "UPDATE accounts SET number_of_shares = ? WHERE account_id = ? AND  symbol = ? ",shares_balance, id, quotes["symbol"]  )
            db.execute("UPDATE accounts SET price = ? WHERE symbol = ?", round(quotes["price"],3), quotes["symbol"])
            db.execute("INSERT INTO transactions (name_of_company,price ,symbol ,shares, type, user_id, transacted)  VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)",name_of_company,round(quotes["price"],3),quotes["symbol"],shares,"BUY", id)
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    #user info
    id = session["user_id"]
    accounts = db.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY transacted DESC", id)
    #rendering history page
    return render_template("history.html", accounts=accounts)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("MISSING SYMBOL")

        # calling the lookup function
        dictionary = lookup(request.form.get("symbol"))

        # checking if dictionary is blank
        if len(dictionary) < 1:
            return apology("INVALID SYMBOL")

        # if not empty and contains values printing the stuff out
        else:
            return render_template("quoted.html", name=dictionary["name"], price=dictionary["price"], symbol=dictionary["symbol"])


    else:
        # User reached route via GET (as by clicking a link or via redirect)
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Ensure password again was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide password again")

        # Ensure passwords match
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("PASSWORDS DON'T MATCH")

        # Ensure username is not already taken
        rows = db.execute("SELECT id FROM users WHERE username = ?;", request.form.get("username"))
        if len(rows) < 1:

            # if not taken adding username and password to database
            db.execute("INSERT INTO users (username, hash) VALUES (?,?);", request.form.get("username"), generate_password_hash(request.form.get("password")))

            id = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("username"))

            # Remember which user has logged in
            session["user_id"] = id[0]["id"]

            # Redirect user to homepage
            return redirect("/")

        else:

            # if already taken
            return apology("Username is Already Taken")


    else:
        return render_template("register.html")





@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # geting user info
    id = session["user_id"]
    accounts = db.execute("SELECT * FROM accounts WHERE account_id = ? AND number_of_shares >= 1 ", id)
    """Sell shares of stock"""
    if request.method == "POST":
        #for post method get info
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        cash = db.execute("SELECT cash FROM users WHERE id = ? ", id )
        cash = cash[0]["cash"]
        quotes= lookup(symbol)

        #checking for user error
        if not shares:
            return apology("Missing shares", 403)
        try:
            number_of_shares = db.execute("SELECT number_of_shares FROM accounts JOIN users ON users.id = accounts.account_id WHERE users.id = ? AND symbol = ? ", id, quotes["symbol"])
        except TypeError:
            return apology("Missing symbol", 403)


        cost = round(quotes["price"],3) * shares
        if int(number_of_shares[0]["number_of_shares"]) < shares:
            return apology("You don't know enough shares", 400)
        else:
            #make changes to database
            present_shares = int(number_of_shares[0]["number_of_shares"]) - shares
            present_balance = float(cash) + cost
            name_of_company = quotes["name"]
            db.execute("UPDATE users SET cash = ? WHERE id = ? ", present_balance, id )
            db.execute("UPDATE accounts SET number_of_shares = ? WHERE account_id = ? AND  symbol = ? ",present_shares, id, quotes["symbol"]  )
            db.execute("UPDATE accounts SET price = ? WHERE symbol = ?", round(quotes["price"],3), quotes["symbol"])
            db.execute("INSERT INTO transactions (name_of_company,price ,symbol ,shares, type, user_id, transacted)  VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)",name_of_company,round(quotes["price"],3),quotes["symbol"],shares,"SELL", id)
            return redirect("/")

    else:
        return render_template("sell.html", accounts=accounts)