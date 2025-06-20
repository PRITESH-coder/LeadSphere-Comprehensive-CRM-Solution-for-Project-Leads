from flask import Flask, render_template, request, session, redirect, flash,url_for
from flask_bcrypt import check_password_hash
from flask_mysqldb import MySQL
import random

from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from collections import defaultdict
# from datetime import datetime
import calendar

app =Flask(__name__)
app.secret_key='india'
app.config["MYSQL_HOST"]='localhost'
app.config["MYSQL_USER"]='root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='leadsphere'

mysql=MySQL(app)

#--Index Page-----
@app.route("/")
def index():
    return render_template ('index.html')

@app.context_processor
def inject_dashboard_counts():
    cursor = mysql.connection.cursor()
    # Admin-level values (visible in admin dashboard)
    total_employees = total_clients = total_projects = completed_projects = 0
    # Employee-level values (visible in employee dashboard)
    allocated_projects = employee_completed_projects = announcement_count = 0
                                    
    # -- Admin Dashboard Data --
    cursor.execute("SELECT COUNT(*) FROM employee")
    total_employees = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM enquiry")
    total_clients = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM project")
    total_projects = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM project WHERE project_process = 'Completed'")
    completed_projects = cursor.fetchone()[0]

    # -- Employee Dashboard Data --
    if 'empid' in session:
        emp_id = session['empid']

        # Allocated projects to this employee
        cursor.execute("SELECT COUNT(*) FROM assign_project WHERE employee_id = %s", (emp_id,))
        allocated_projects = cursor.fetchone()[0]

        # Completed projects assigned to this employee
        cursor.execute("""
            SELECT COUNT(*) FROM assign_project a
            JOIN project p ON a.project_id = p.project_id
            WHERE a.employee_id = %s AND p.project_process = 'Completed'
        """, (emp_id,))
        employee_completed_projects = cursor.fetchone()[0]

        # Announcements targeted to this employee
        cursor.execute("SELECT COUNT(*) FROM announcements ")
        announcement_count = cursor.fetchone()[0]

    cursor.close()

    return dict(
        # Admin values
        total_employees=total_employees,
        total_clients=total_clients,
        total_projects=total_projects,
        completed_projects=completed_projects,

        # Employee values
        allocated_projects=allocated_projects,
        employee_completed_projects=employee_completed_projects,
        announcement_count=announcement_count
    )


# # -----------------------Admin -------------------------------------------------------------------------
#------Admin Loge Page----------
@app.route("/adminlogin")
def login():
    return render_template("admin_login.html")

#-------Admin Dashboard after Login --------------
@app.route('/admindashboard',methods=["GET","POST"])
def Admindashboard():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == 'admin' and password == 'Pritesh':
            session['email'] = email
            session['password'] = password
        else:
            message = "Please enter valid Email and Password"
            return render_template("admin_login.html", message=message)
        # Check if user is logged in
    if 'email' not in session:
        return redirect(url_for('admin_login'))  # You must define this route separately
    # Database Connection Open
    cursor = mysql.connection.cursor()
    # Count total employees
    cursor.execute("SELECT COUNT(*) FROM employee")
    total_employees = cursor.fetchone()[0]
    # Count total clients
    cursor.execute("SELECT COUNT(*) FROM enquiry")
    total_clients = cursor.fetchone()[0]
    # Count total projects
    cursor.execute("SELECT COUNT(*) FROM project")
    total_projects = cursor.fetchone()[0]
    # Count completed projects (assuming 'status' column contains 'Completed')
    cursor.execute("SELECT COUNT(*) FROM project WHERE project_process = 'Completed'")
    completed_projects = cursor.fetchone()[0]
    # ✅ Count in-progress projects
    cursor.execute("SELECT COUNT(*) FROM project WHERE project_process = 'In Progress'")
    in_progress_projects = cursor.fetchone()[0]
    # ✅ Get project process by month from datetime column
    cursor.execute("SELECT project_process, date FROM project")
    projects = cursor.fetchall()
    cursor.close()
    # Default dict for holding monthly counts
    monthly_data = defaultdict(lambda: {"Completed": 0, "In Progress": 0})

    for process, date in projects:
        try:
            # Use datetime directly to get month name
            month = date.strftime("%B")
            if process in ["Completed", "In Progress"]:
                monthly_data[month][process] += 1
        except Exception as e:
            continue  # skip if any data is malformed

    # 📅 Ordered month names (January to December)
    all_months = list(calendar.month_name)[1:]  # ['January', ..., 'December']
    completed_by_month = [monthly_data[month]["Completed"] for month in all_months]
    in_progress_by_month = [monthly_data[month]["In Progress"] for month in all_months]
    return render_template('admin/dashboard.html',
                           total_employees=total_employees,
                           total_clients=total_clients,
                           total_projects=total_projects,
                           completed_projects=completed_projects,
                           in_progress_projects=in_progress_projects,
                           months=all_months,
                           completed_data=completed_by_month,
                           in_progress_data=in_progress_by_month) # Always render the admin dashboard

#----Enquiry Form Filling------
@app.route('/enquiry_form')
def enquiry():
    return render_template("admin/enquiry_form.html")

#----Saving Enquiry Form After filling all fields-------
@app.route('/save',methods=['POST','GET'])
def save():
    # print(request.form)  # Print the form data to console
    if(request.method=='POST'):
        name = request.form["txtname"]
        email = request.form["txtemail"]
        enqsubject = request.form["txtenqsubject"]
        if enqsubject=='other':
            enqsubject=request.form['otherCategory']
        enqdetail = request.form["txtenqdetails"]
        # Database Connection Open
        cur = mysql.connection.cursor()
        # Query Specification
        cur.execute('insert into enquiry(name,email,category,details) values(%s,%s,%s,%s)',(name,email,enqsubject,enqdetail))
        #Transaction save
        mysql.connection.commit()
        #Database Connection Close
        cur.close()
        return render_template('admin/enquiry_form.html',success=True)
    return render_template("admin/enquiry_form.html",success=False)

#-----View Enquiry Table------------------
@app.route('/tables')
def Tables():
    # Database connection Open()
    cur = mysql.connection.cursor()
    # Query Specification
    cur.execute('select * from enquiry')
    # fetch all records
    result = cur.fetchall()
    # Database Close()
    cur.close()
    return render_template('admin/tables.html',result=result)

# ----Delete Enquiry of any Person-----------------
@app.route('/delete')
def Delete():
    d = request.args.get('id')
    if d:
        try:
            # Database Connection Open
            cur = mysql.connection.cursor()
            # Query Specification
            cur.execute('DELETE FROM enquiry WHERE id = %s', (d,))
            # Transaction Save
            mysql.connection.commit()
            # Database Close
            cur.close()
            flash('Record deleted successfully!', 'success')
        except Exception as e:
            # Handle the error
            flash(f'Error deleting record: {str(e)}', 'danger')
        finally:
            # Make sure to close the cursor in case of exceptions
            cur.close()

    return redirect('/tables')  # Redirect to the tables after deletion

#-----Adding Employees-----
@app.route('/add_emp')
def Addemployee():
    return render_template('admin/add_emp.html')

#------Saving Register Employee Data------
@app.route('/emp_save',methods=['POST','GET'])
def Empsave():
    if(request.method=='POST'):
        emp_id=request.form['txtempid']
        name=request.form['txtname']
        email=request.form['txtemail']
        password=request.form['txtpassword']
        designation=request.form['txtdesignation']
        if designation=='other':
            designation=request.form['otherdesignation']
        mobile=request.form['txtmobile']
        #Database connection open()
        cur=mysql.connection.cursor()
        #query Specification
        cur.execute("insert into employee(emp_id,emp_name,emp_email,emp_password,emp_designation,emp_mobile) values (%s,%s,%s,%s,%s,%s)",(emp_id,name,email,password,designation,mobile))
        #transaction Save
        mysql.connection.commit()
        #database connection close
        cur.close()
        return render_template('admin/add_emp.html',success=True)
    return render_template('admin/add_emp.html',success=False)

#-------Showing Employee Table------
@app.route('/show_emp')
def ShowingEmp():
    #Database Connection Open()
    cur=mysql.connection.cursor()
    #Query Specification()
    cur.execute("select * from employee")
    #fetchall Database
    result=cur.fetchall()
    #Database Close
    cur.close()
    return render_template('admin/show_emp.html',result=result)

#-------Employee Delete Route---------------
@app.route('/emp_delete')
def Emp_Delete():
    id= request.args.get('id')
    if id:
        try:
            # Database Connection Open
            cur = mysql.connection.cursor()
            # Query Specification
            cur.execute('DELETE FROM employee WHERE emp_id = %s', (id,))
            # Transaction Save
            mysql.connection.commit()
            # Database Close
            cur.close()
            flash('Record deleted successfully!', 'success')
        except Exception as e:
            # Handle the error
            flash(f'Error deleting record: {str(e)}', 'danger')
        finally:
            # Make sure to close the cursor in case of exceptions
            cur.close()

    return redirect('/show_emp')  # Redirect to the tables after deletion


#-------Addings Projects----------
@app.route('/add_project',methods=['POST','GET'])
def Add_project():
    if(request.method=='POST'):
        name=request.form['txtname']
        category=request.form['txtcategory']
        if category =='other':
            category=request.form['txtothercategory']
        budget=request.form['txtbudget']
        technology=request.form['txttechnology']
        project=request.form['txtproject']   #Deadline Project
        project_process=request.form['txtprojectprocess']   #Project Process
        #Database connection open()
        cur=mysql.connection.cursor()
        #query Specification
        cur.execute("insert into project(project_name,category,budget,technology,project_deadline,project_process) values (%s,%s,%s,%s,%s,%s)",(name,category,budget,technology,project,project_process))
        #transaction Save
        mysql.connection.commit()
        #database connection close
        cur.close()
        return render_template('admin/add_project.html',success=True)
    return render_template('admin/add_project.html',success=False)

#-------Showing Project List-------
@app.route('/show_project')
def Showproject():
    # Database Connection Open()
    cur = mysql.connection.cursor()
    # Query Specification()
    cur.execute("select * from project")
    # fetchall Database
    result = cur.fetchall()
    # Database Close
    cur.close()
    return render_template('admin/show_project.html',result=result)

#---------Veiwing project-------
@app.route('/view_project',methods=['POST','GET'])
def View_project():
    id = request.args.get('id')
    #Database Connection Open()
    cur =mysql.connection.cursor()
    #Query Specification()
    cur.execute('select * from project where project_id=%s',(id,))
    project=cur.fetchone()
    print("Project Record list :",project)
    cur.close()
    return render_template("admin/update_project.html",project=project)

#-------Project Delete Route---------------
@app.route('/project_delete')
def project_Delete():
    id= request.args.get('id')
    if id:
        try:
            # Database Connection Open
            cur = mysql.connection.cursor()
            # Query Specification
            cur.execute('DELETE FROM project WHERE project_id = %s', (id,))
            # Transaction Save
            mysql.connection.commit()
            # Database Close
            cur.close()
            flash('Record deleted successfully!', 'success')
        except Exception as e:
            # Handle the error
            flash(f'Error deleting record: {str(e)}', 'danger')
        finally:
            # Make sure to close the cursor in case of exceptions
            cur.close()

    return redirect('/show_project')  # Redirect to the tables after deletion

#--------Assign Project Page--------
#-----------Modify code--------
@app.route('/assign_project', methods=['GET', 'POST'])
def AssignProject():
    message = ""
    if request.method == 'POST':
        selected_employee_ids = request.form.getlist('employee_id')  # From checkboxes
        selected_project = request.form.get('selected_project')      # From dropdown

        if selected_employee_ids and selected_project:
            cur = mysql.connection.cursor()

            try:
                # Fetch employee names from DB for selected IDs
                format_strings = ','.join(['%s'] * len(selected_employee_ids))
                cur.execute(f"SELECT emp_id, emp_name FROM employee WHERE emp_id IN ({format_strings})", tuple(selected_employee_ids))
                employee_data = cur.fetchall()
                # Insert each selected employee into assign_project table
                for emp_id, emp_name in employee_data:
                    cur.execute(
                        'INSERT INTO assign_project (project_id, employee_id, employee_name) VALUES (%s, %s, %s)',
                        (selected_project, emp_id, emp_name)
                    )
                mysql.connection.commit()
                flash("Assignments added successfully.", "success")
            except Exception as e:
                print("Error during assignment:", e)
                mysql.connection.rollback()
                flash("An error occurred while assigning the project.", "danger")
            finally:
                cur.close()
    # Fetch data for display in GET or after POST
    cur = mysql.connection.cursor()
    # Employees not already assigned to any project
    cur.execute("""
        SELECT * FROM employee
       
    """)
    result = cur.fetchall()
    # Projects that are not yet assigned
    cur.execute("""
        SELECT * FROM project
        WHERE project_id NOT IN (SELECT project_id FROM assign_project)
    """)
    project = cur.fetchall()
    cur.close()
    return render_template("admin/assign_project.html", result=result, project=project, message=message)

#-------Show Assign Project Page-----latest code----
@app.route('/show_assign_project', methods=['GET'])
def Show_assign_project():
    # Database connection open
    cur = mysql.connection.cursor()
    # Fetch all projects and their respective assignments
    # Fetch projects that have assignments
    cur.execute('''
            SELECT p.project_id, p.project_name, ap.employee_id, ap.employee_name
            FROM project p
            INNER JOIN assign_project ap ON p.project_id = ap.project_id
            ORDER BY p.project_id
        ''')
    assignments = cur.fetchall()  # Fetch the results for all projects and their assigned employees
    # Database Close
    cur.close()
    # Render template and pass the assignments to it
    return render_template("admin/show_assign_project.html", assignments=assignments)

#-----------Assign Project Graph Page----------------
@app.route("/assign_project_graph")
def Assign_Graph():
    # Database Connection Open
    cur = mysql.connection.cursor()
    # Step 1: Fetch project names
    cur.execute('SELECT project_id, project_name FROM project')
    project_names_data = cur.fetchall()
    print("project_names_data:-", project_names_data)
    # Create a dictionary of project names keyed by project_id
    project_names = {project_id: project_name for project_id, project_name in project_names_data}
    # Step 2: Fetch employee counts for each project
    cur.execute('''
        SELECT project_id, COUNT(employee_id) AS employee_count 
        FROM assign_project 
        GROUP BY project_id
    ''')
    project_employee_counts = cur.fetchall()
    # Debugging employee count results
    print("project_employee_counts:-", project_employee_counts)
    # Create a dictionary for employee counts, converting project_id to int
    employee_count_dict = {int(project_id): employee_count for project_id, employee_count in project_employee_counts}
    # Initialize projects list
    projects = []
    # Map employee counts to project names
    for project_id, project_name in project_names.items():
        employee_count = employee_count_dict.get(project_id, 0)  # Gets count or defaults to 0
        projects.append((project_name, employee_count))
    # Final debug output of the constructed projects list
    print("Project Record list:", projects)
    cur.close()
    return render_template('admin/assign_project_graph.html', projects=projects)

#------------Enquiry Process code------------
@app.route("/enquiry_process", methods=['POST', 'GET'])
def Enquiry_process():
    if request.method == 'POST':
        # Get data from form submission
        id = request.form.get('id')  # <-- Get from form, not from URL
        phase = request.form.get('txtphase')
        description = request.form.get('txtdescription')
        cur = mysql.connection.cursor()
        if id and phase and description:
            id = int(id)  # Ensure it's an integer
            cur.execute("""
                UPDATE enquiry
                SET phase_name = %s, description = %s
                WHERE id = %s
            """, (phase, description, id))
            mysql.connection.commit()
            flash('Enquiry Process updated successfully!', 'success')
        else:
            flash('Update failed: Missing required fields.', 'danger')

        cur.close()
        return redirect(f'/enquiry_process?id={id}')  # Keep ID in URL after update
    else:
        # GET request
        id = request.args.get('id')  # Get from URL
        if not id:
            flash('Invalid access. No enquiry ID provided.', 'danger')
            return redirect('/some_other_page')
        cur = mysql.connection.cursor()
        cur.execute('SELECT category, phase_name,description, id FROM enquiry WHERE id = %s', (id,))
        result = cur.fetchone()
        cur.close()
        return render_template("admin/enquiry_process.html", result=result, selected_phase=result[1])

#--------Content_Dashboard Page-------------
@app.route('/content_dashboard')
def Contentdashboard():
    return render_template('admin/content_admindashboard.html')

#--------Add_Announcement Page-------------------
@app.route('/add_announcement', methods=['GET', 'POST'])
def add_announcement():
    if request.method == 'POST':
        message = request.form['message']
        type_ = request.form['type']
        team = request.form['team']
        cur = mysql.connection.cursor()
        cur.execute("""
                   INSERT INTO announcements (message, type, team)
                   VALUES (%s, %s, %s)
               """, (message, type_, team))
        mysql.connection.commit()
        cur.close()
        # Flash a success message
        flash('Announcement added successfully!', 'success')
        return redirect(url_for('add_announcement'))  # adjust this if you use another route name
    return render_template('admin/add_announcement.html')

#--------Admin Logout-------------
@app.route('/logout')
def logout():
    session['email']=None
    session['password']=None
    return render_template('index.html')

#--------------------------------Employee Module-------------------------------------------------------------------

# ----------Employee_Dashboard------
@app.route('/employee_dashboard',methods=['GET','POST'])
def Employee_Dashboard():
    return render_template('employee_dashboard.html',name=session['name'],emp_id=session['empid'])

#----------Employee Login Page----------------------
@app.route('/employee_login',methods=['GET','POST'])
def employee_login():
    msg=''
    # For GET requests or failed POST requests, render the login page
    if request.method=='POST':
        email = request.form['txtemail']
        password = request.form['txtpassword']
        # Database Connection Open
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM employee WHERE emp_email=%s AND emp_password=%s',(email,password,))
        record = cur.fetchone()
        if record:
            session['loggedin']=True
            session['email']=record[2]
            session['name']=record[1]
            session['empid']=record[0]
            return redirect(url_for("Employee_Dashboard"))
        else:
            # Use flash to set the error message
            flash('Incorrect Email and Password. Try Again!', 'danger')  # 'danger' is a Bootstrap category for errors
    return render_template('employee_login.html')

#---------Announcement Page--------------
@app.route('/announcement')
def show_announcements():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, message, type, team, created_at FROM announcements ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    announcements = []
    for row in rows:
        announcements.append({
            'id': row[0],
            'message': row[1],
            'type': row[2].lower(),  # 'info', 'urgent', etc.
            'team': row[3],
            'date': row[4].strftime('%B %d, %Y'),
            'time': row[4].strftime('%I:%M %p')  # Format like "02:45 PM"
        })
    return render_template('employee/announcement.html', announcements=announcements)

#-----------Allocated Project List to Employee Page--------
@app.route('/allocated_project')
def Allocated_project():
    emp_id=session['empid']
    # Database Connection Open
    cur = mysql.connection.cursor()
    cur.execute("SELECT ap.project_id, p.project_name, p.category, p.budget, p.technology, p.project_deadline, p.project_process, p.date FROM employee e JOIN assign_project ap ON e.emp_id = ap.employee_id JOIN project p ON ap.project_id = p.project_id WHERE e.emp_id = %s AND p.project_process = 'In Progress'", (emp_id,))
    # Fetch all the results
    projects = cur.fetchall()
    # Close the database connection
    cur.close()
    return render_template("employee/allocated_project.html",projects=projects,name=session['name'])

#----------------Completed Project Page---------------
@app.route('/completed_project')
def Completed_project():
    emp_id = session['empid']
    # Database Connection Open
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT ap.project_id, p.project_name, p.category, p.budget, p.technology, p.project_deadline, p.project_process, p.date FROM employee e JOIN assign_project ap ON e.emp_id = ap.employee_id JOIN project p ON ap.project_id = p.project_id WHERE e.emp_id = %s AND p.project_process = 'Completed'",
        (emp_id,))
    # Fetch all the results
    projects = cur.fetchall()
    # Close the database connection
    cur.close()
    return render_template("employee/completed_project.html",projects=projects,name=session['name'])

#------------Employee Profile Page-------------------
@app.route('/emp_profile', methods=['GET', 'POST'])
def emp_profile():
    if request.method == 'POST':
        # Retrieve emp_id from form (hidden input)
        emp_id = request.form['txtempid']
        # Retrieve other form data
        name = request.form['txtname']
        email = request.form['txtemail']
        password = request.form['txtpassword']
        designation = request.form['txtdesignation']
        otherdesignation = request.form.get('otherdesignation', None)
        mobile = request.form['txtmobile']
        # Determine the designation value
        designation_value = otherdesignation if (designation == 'other' and otherdesignation) else designation
        # Execute the update
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE employee SET emp_name=%s, emp_email=%s, emp_password=%s, emp_designation=%s, emp_mobile=%s WHERE emp_id=%s",
            (name, email, password, designation_value, mobile, emp_id)
        )
        mysql.connection.commit()
        cur.close()
        flash('Profile updated successfully!', 'success')
        return redirect('/emp_profile')
    else:
        # Fetch current data for display
        emp_id = session['empid']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM employee WHERE emp_id=%s", (emp_id,))
        result = cur.fetchall()
        cur.close()
        return render_template("employee/emp_profile.html", result=result,name=session['name'], emp_id = session['empid'])

#--------------Progress Report Page------------------
#-_______-------------Updated code-----------
from flask import session, render_template
from datetime import datetime
import re
#--------------Progress Report Page------------------
@app.route('/progress_report')
def progress_report():
    emp_id = session.get('empid')
    cursor = mysql.connection.cursor()
    # Fetch project_process, category, and date for all projects assigned to the employee
    cursor.execute("""
        SELECT p.project_process, p.category, p.date
        FROM assign_project ap
        JOIN project p ON ap.project_id = p.project_id
        WHERE ap.employee_id = %s
    """, (emp_id,))
    records = cursor.fetchall()
    cursor.close()
    # Initialize monthly progress dictionary (1 = Jan, ..., 12 = Dec)
    monthly_progress = {i: 0 for i in range(1, 13)}
    for project_process, category, project_date in records:
        score = 0
        # Parse date
        if isinstance(project_date, str):
            project_date = datetime.strptime(project_date, "%Y-%m-%d %H:%M:%S")
        month = project_date.month
        # Normalize fields
        project_process = project_process.strip().lower()
        if category:
            category = category.strip().lower().replace('-', ' ').replace('_', ' ')
        # Process status scoring
        if project_process == 'in progress':
            score += 10
            print("Matched process: In Progress (+10%)")
        elif project_process == 'completed':
            score += 20
            print("Matched process: Completed (+20%)")
        # Category scoring
        if category:
            if 'web development' in category:
                score += 5
                print("Matched category: Web Development (+5%)")
            if 'blockchain development' in category:
                score += 15
                print("Matched category: Blockchain Development (+15%)")
            if 'game development' in category:
                score += 20
                print("Matched category: Game Development (+20%)")
            if 'data science' in category or 'machine learning' in category:
                score += 25
                print("Matched category: DS/ML (+25%)")

        # Cap individual score for the project
        if score > 100:
            score = 100
        elif score < 10:
            score = 10

        monthly_progress[month] += score
        print(f"Score for month {month}: {monthly_progress[month]}")
    # Cap monthly progress at 100
    for m in monthly_progress:
        if monthly_progress[m] > 100:
            monthly_progress[m] = 100
        elif monthly_progress[m] < 10 and monthly_progress[m] > 0:
            monthly_progress[m] = 10

    # Convert to list for Chart.js
    month_labels = ["January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"]
    progress_data = [monthly_progress[i] for i in range(1, 13)]
    return render_template(
        'employee/progress_report.html',
        name=session['name'],
        progress_data=progress_data,
        month_labels=month_labels
    )

#-----------------------Client Module--------------------------------------
#------Client Login Page----------
@app.route("/client_login",methods=['POST','GET'])
def client_login():
    # For GET requests or failed POST requests, render the login page
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Database Connection Open
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM client WHERE email=%s AND password=%s', (email, password,))
        record = cur.fetchone()
        if record:
            session['loggedin'] = True
            session['email'] = record[3]
            session['password'] = record[7]
            session['id'] = record[0]
            # You could optionally flash a success message here if you want
            # flash('Login successful!', 'success')
            return redirect(url_for("client_dashboard"))
        else:
            # Use flash to set the error message
            flash('Incorrect Email and Password. Try Again!', 'danger')  # 'danger' is a Bootstrap category for errors
    return render_template('client_login.html')

#----------------------------Client-Registration---------------------------------
@app.route("/client_registration", methods=['POST','GET'])
def client_registration():
    if (request.method == 'POST'):
        lead_name = request.form["name"]
        email = request.form["email"]
        password = request.form['password']
        mobile = request.form['mobile']
        # Database Connection Open
        cur = mysql.connection.cursor()
        # Query Specification
        cur.execute('insert into client(lead_name,email,password,mobile) values(%s,%s,%s,%s)',(lead_name, email,  password, mobile))
        # Transaction save
        mysql.connection.commit()
        # Database Connection Close
        cur.close()
        return render_template('client/client_registration.html', success=True)
    return render_template("client/client_registration.html", success=False)

#-----------------------------Client-Dashboard---------------------------------
@app.route("/client_dashboard" ,methods=['POST','GET'])
def client_dashboard():
    return render_template("client_dashboard.html")

#-----------------------------Client-Enquiry-Project---------------------------------
@app.route("/enquiry_project")
def enquiry_project():
    return render_template("client/enquiry_project.html")

#--------------Saving Enquiry Form After filling all fields--------------------
@app.route('/saving',methods=['POST','GET'])
def saving():
    if(request.method=='POST'):
        lead_name = request.form["txtname"]
        email = request.form["txtemail"]
        enqsubject = request.form["txtenqsubject"]
        if enqsubject=='other':
            enqsubject=request.form['otherCategory']
        enquiry_detail = request.form["txtenqdetails"]
        # Database Connection Open
        cur = mysql.connection.cursor()
        # Query Specificationx
        cur.execute('insert into client(lead_name,email,category,enquiry_details) values(%s,%s,%s,%s)',(lead_name,email,enqsubject,enquiry_detail))
        #Transaction save
        mysql.connection.commit()
        #Database Connection Close
        cur.close()
        return render_template('client/enquiry_project.html',success=True)
    return render_template("client/enquiry_project.html",success=False)

#-----------------------------Client-Show-enquiry---------------------------------
@app.route("/show_enquiry")
def show_enquiry():
    id = session['id']
    # Database connection Open()
    cur = mysql.connection.cursor()
    # Query Specification
    cur.execute('SELECT lead_name, email, mobile, category, enquiry_details, date FROM client WHERE id = %s', (id,))
    # fetch all records
    result = cur.fetchall()
    # Database Close()
    cur.close()
    return render_template("client/show_enquiry.html",result=result)

#-----------------------------Client-Profile---------------------------------
@app.route("/update_profile" ,methods=["POST","GET"])
def update_profile():
    if request.method == 'POST':
        lead_name = request.form.get('lead_name')
        email = request.form.get('email')
        mobile = request.form.get('phone')  # or 'mobile', depending on your fix
        password = request.form.get('password')
        id = session['id']
        # Database Connection Open/-
        cur = mysql.connection.cursor()
        # Query Specification
        cur.execute('update client set lead_name= %s,email = %s, mobile=%s, password=%s where id= %s', (lead_name, email, mobile,password,id,))
        # Transaction Save
        mysql.connection.commit()
        # Database Connection Close
        cur.close()
        return render_template("client/update_profile.html")
        # Handle GET request
    return render_template("client/update_profile.html")

#-----------------------------Client-Add-Payment---------------------------------
@app.route("/add_payment")
def add_payment():
    return render_template("client/add_payment.html")

#-----------------------------Client-View-Payment---------------------------------
@app.route("/client_view_payment")
def client_view_payment():
    return render_template("client/client_view_payment.html")

app.run(debug=True)

