from flask import Flask, render_template, request, redirect, url_for, session, flash

import sqlite3
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

app.secret_key = 'secret_key'

UPLOAD_FOLDER = 'static/uploads'  # Folder to store uploaded images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = os.path.join('static', UPLOAD_FOLDER)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


property_list = []

def initialize_database():
    conn = sqlite3.connect('your_database.db')  # Specify the correct database name here
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 first_name TEXT NOT NULL,
                 last_name TEXT NOT NULL,
                 email TEXT NOT NULL,
                 password TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 page TEXT,
                 comment_text TEXT,
                 FOREIGN KEY(user_id) REFERENCES users(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS properties
                 (property_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 address TEXT NOT NULL,
                 postcode TEXT NOT NULL,
                 description TEXT,
                 electricity_cost TEXT,
                 water_cost TEXT,
                 internet_cost TEXT,
                 council_tax TEXT,
                 landlord_review TEXT,
                 property_tip TEXT,
                 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                 image_path TEXT)''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS property_votes (
        vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        user_id INTEGER,
        vote_type TEXT,  -- 'upvote' or 'downvote'
        FOREIGN KEY(property_id) REFERENCES properties(property_id),
        FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('First_name')
        last_name = request.form.get('Last_name')
        email = request.form.get('Email')
        password = request.form.get('Password')

        if not first_name or not last_name or not email or not password:
            error_statement = 'All form fields required...'
            return render_template('register.html', error_statement=error_statement)

        conn = sqlite3.connect('your_database.db')  # Specify the correct database name here
        c = conn.cursor()
        c.execute('INSERT INTO users (first_name, last_name, email, password) VALUES (?, ?, ?, ?)',
                  (first_name, last_name, email, password))
        conn.commit()
        conn.close()

        # Redirect to the appropriate route after successful registration
        return redirect(url_for('login'))  # Replace 'login' with the actual route name

    return render_template('register.html')

if __name__ == '__main__':
    initialize_database()
    app.run(debug=True)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('Email')
        password = request.form.get('Password')

        conn = sqlite3.connect('your_database.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['user'] = {
                'id': user[0],
                'first_name': user[1],
                'last_name': user[2],
                'email': user[3],
                # Add other user data here if needed
            }
            return redirect(url_for('profile'))

        error_statement = 'Invalid email or password'
        return render_template('login.html', error_statement=error_statement)

    return render_template('login.html')



@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    if user_id:
        conn = sqlite3.connect('your_database.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        conn.close()

        if user:
            return render_template('profile.html', user=user)

    return redirect(url_for('login'))

@app.route('/submit-property', methods=['GET', 'POST'])
def submit_property():
    # Check if user is logged in
    if 'user_id' not in session:
        return render_template('login.html', logged_in=False)
    
    if request.method == 'POST':
        required_fields = ['address', 'postcode', 'description', 'electricity', 'water', 'internet', 'council_tax', 'landlord_review', 'property_tip']
        missing_fields = [field for field in required_fields if not request.form.get(field)]
        if missing_fields:
            error_statement = f"Missing required fields: {', '.join(missing_fields)}"
            return render_template('about.html', error_statement=error_statement)

        # Construct property_details from form data
        property_details = {field: request.form[field] for field in required_fields}
        property_details['image_path'] = None  # Default image path is None

        file = request.files.get('file')  # Use .get() to handle cases where 'file' field is missing

        # If a file is selected and it is allowed
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            property_details['image_path'] = os.path.join(UPLOAD_FOLDER, filename).replace('\\', '/')
        elif file and not file.filename:
            # Handle case where a file field exists but no file is selected
            pass  # Do nothing, proceed without an image
        elif file:
            # Handle case where an invalid file is uploaded
            error_statement = 'Invalid file type. Allowed types are png, jpg, jpeg, gif.'
            return render_template('about.html', error_statement=error_statement)

        # Inserting into database
        conn = sqlite3.connect('your_database.db')
        c = conn.cursor()
        c.execute('''INSERT INTO properties (address, postcode, description, electricity, water, internet, council_tax, landlord_review, property_tip, image_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (property_details['address'], property_details['postcode'], property_details['description'],
                   property_details['electricity'], property_details['water'], property_details['internet'],
                   property_details['council_tax'], property_details['landlord_review'], property_details['property_tip'], property_details['image_path']))
        conn.commit()
        conn.close()

        property_list.append(property_details)

        return redirect(url_for('quality'))  # Redirecting to the home page after successful submission
    return render_template('submit_property.html')  # Render the form template




@app.route('/quality-feedback')
def quality_feedback():
    conn = sqlite3.connect('your_database.db')  # Specify the correct database name here
    c = conn.cursor()
    c.execute('SELECT * FROM properties')
    properties = c.fetchall()
    conn.close()

@app.route('/properties')
def show_properties():
    conn = sqlite3.connect('your_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties")
    properties = cursor.fetchall()
    conn.close()
    return render_template('quality', properties=properties)


@app.route('/comment/<page>', methods=['POST'])
def comment(page):
    user_id = session.get('user_id')
    comment_text = request.form.get('comment_text')

    if user_id and comment_text:
        conn = sqlite3.connect('your_database.db')
        c = conn.cursor()
        c.execute('INSERT INTO comments (user_id, page, comment_text) VALUES (?, ?, ?)',
                  (user_id, page, comment_text))
        conn.commit()
        conn.close()

    return redirect(url_for(page))

@app.route('/comments/<page>')
def comments(page):
    conn = sqlite3.connect('your_database.db')
    c = conn.cursor()
    c.execute('SELECT users.first_name, users.last_name, comments.comment_text FROM comments JOIN users ON comments.user_id = users.id WHERE comments.page = ?', (page,))
    comments = c.fetchall()
    conn.close()

    return render_template('comments.html', page=page, comments=comments)

@app.route('/comments/<page>')
def comments_page(page):
    conn = sqlite3.connect('your_database.db')
    c = conn.cursor()
    c.execute('SELECT users.first_name, users.last_name, comments.comment_text FROM comments JOIN users ON comments.user_id = users.id WHERE comments.page = ?', (page,))
    comments = c.fetchall()
    conn.close()

    return render_template('comments.html', page=page, comments=comments)




@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    title = "Connor Jones's Portfolio"
    return render_template("index.html", title=title)

@app.route('/about', methods=['GET', 'POST'])
def about():
    title = "About"
    page = 'about'  # Initialize the page variable
    
    if request.method == 'POST':
        # Handle comment submission here
        user_id = session.get('user_id')
        comment_text = request.form.get('comment_text')
        
        if user_id and comment_text:
            conn = sqlite3.connect('your_database.db')
            c = conn.cursor()
            c.execute('INSERT INTO comments (user_id, page, comment_text) VALUES (?, ?, ?)',
                      (user_id, page, comment_text))
            conn.commit()
            conn.close()
    
    conn = sqlite3.connect('your_database.db')
    c = conn.cursor()
    c.execute('SELECT users.first_name, users.last_name, comments.comment_text FROM comments JOIN users ON comments.user_id = users.id WHERE comments.page = ?', (page,))
    comments = c.fetchall()
    
    # Fetch the original content for the page
    original_content = "Your original about page content goes here..."
    
    conn.close()
    
    return render_template("about.html", title=title, page=page, comments=comments, original_content=original_content)

@app.route('/quality', methods=['GET', 'POST'])
def quality():
    title = "Quality"
    page = 'quality'

    # Retrieve the search and filter query from the URL parameters
    search_query = request.args.get('search')
    filter_query = request.args.get('filter')  # New filter parameter

    # Connect to the database
    conn = sqlite3.connect('your_database.db')
    c = conn.cursor()

    # Define the base query with the logic for counting upvotes and downvotes
    base_query = '''
        SELECT p.*,
               SUM(CASE WHEN pv.vote_type = 'upvote' THEN 1 ELSE 0 END) as upvotes,
               SUM(CASE WHEN pv.vote_type = 'downvote' THEN 1 ELSE 0 END) as downvotes
        FROM properties p
        LEFT JOIN property_votes pv ON p.propertyid = pv.property_id
    '''

    # Modify the query based on the filter
    if filter_query == "upvotes":
        order_by = " ORDER BY upvotes DESC"
    elif filter_query == "downvotes":
        order_by = " ORDER BY downvotes DESC"
    else:
        order_by = ""

    # Execute the query with search and filter logic
    if search_query:
        c.execute(base_query + " WHERE p.address LIKE ? OR p.postcode LIKE ? GROUP BY p.propertyid" + order_by,
                  ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        c.execute(base_query + " GROUP BY p.propertyid" + order_by)

    properties = c.fetchall()
    conn.close()

    # Handle comment submission (similar to your existing code)
    if request.method == 'POST':
        user_id = session.get('user_id')
        comment_text = request.form.get('comment_text')

        if user_id and comment_text:
            conn = sqlite3.connect('your_database.db')
            c = conn.cursor()
            c.execute('INSERT INTO comments (user_id, page, comment_text) VALUES (?, ?, ?)',
                      (user_id, page, comment_text))
            conn.commit()
            conn.close()

    # Retrieve comments for the quality page (as per your existing logic)
    conn = sqlite3.connect('your_database.db')
    c = conn.cursor()
    c.execute('SELECT users.first_name, users.last_name, comments.comment_text FROM comments JOIN users ON comments.user_id = users.id WHERE comments.page = ?', (page,))
    comments = c.fetchall()
    conn.close()

    # Render the template with the properties data and any additional required data
    return render_template("quality.html", title=title, page=page, comments=comments, properties=properties)


@app.route('/vote/<int:property_id>/<vote_type>', methods=['POST'])
def vote(property_id, vote_type):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('your_database.db')
    c = conn.cursor()

    # Check if the user has already voted for this property
    c.execute('SELECT * FROM property_votes WHERE property_id = ? AND user_id = ?', (property_id, user_id))
    existing_vote = c.fetchone()

    if existing_vote:
        error_statement = 'You have already voted for this property.'
        return render_template('fail.html', error_statement=error_statement)
    else:
        # Insert the new vote as the user hasn't voted for this property yet
        c.execute('INSERT INTO property_votes (property_id, user_id, vote_type) VALUES (?, ?, ?)',
                  (property_id, user_id, vote_type))
        conn.commit()

    conn.close()
    return redirect(url_for('quality'))


@app.route('/Subscribe')
def subscribe():
    title = "Contact"
    return render_template("subscribe.html", title=title)

@app.route('/login')
def contact():
    title = "Contact"
    return render_template("login.html", title=title)

@app.route('/form', methods=["post"])
def form():
    First_name = request.form.get("First_name")
    Last_name = request.form.get("Last_name")
    Email = request.form.get("Email")

    

    if not First_name or not Last_name or not Email:
        error_statement = "All form fields required..."
        return render_template("fail.html", error_statement=error_statement)


    title = "Thank You!"
    return render_template("form.html", title=title, First_name=First_name, Last_name=Last_name, Email=Email)

if __name__ == '__main__':
    app.secret_key = 'your_secret_key'
    init_db()
    app.run(debug=True)
