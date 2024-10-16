from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Marks, Attendance
import pandas as pd
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Create the database
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home route
@app.route('/')
def index():
    return render_template('index.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']  # 'student' or 'professor'

        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))

        # Create new user
        new_user = User(username=username, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        password = request.form['password']

        # Find user
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.')

            # Redirect based on role
            if user.role == 'student':
                return redirect(url_for('dashboard_student'))
            else:
                return redirect(url_for('dashboard_professor'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))

# Student Dashboard
@app.route('/dashboard_student')
@login_required
def dashboard_student():
    if current_user.role != 'student':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    # Fetch marks and attendance
    marks = Marks.query.filter_by(student_id=current_user.id).all()
    attendance = Attendance.query.filter_by(student_id=current_user.id).all()

    # Prepare data for charts
    subjects = [mark.subject for mark in marks]
    scores = [mark.score for mark in marks]

    attendance_dates = [att.date.strftime('%Y-%m-%d') for att in attendance]
    attendance_status = [att.status for att in attendance]
    # Convert attendance status to numerical values
    attendance_numeric = [1 if status == 'Present' else 0 for status in attendance_status]

    return render_template('dashboard_student.html', marks=marks, attendance=attendance,
                       subjects=subjects, scores=scores,
                       attendance_dates=attendance_dates, attendance_status=attendance_numeric)

# Professor Dashboard
@app.route('/dashboard_professor')
@login_required
def dashboard_professor():
    if current_user.role != 'professor':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    # Fetch all students
    students = User.query.filter_by(role='student').all()

    # Calculate average marks
    student_stats = []
    for student in students:
        marks = Marks.query.filter_by(student_id=student.id).all()
        avg_score = sum([mark.score for mark in marks]) / len(marks) if marks else 0
        student_stats.append({
            'username': student.username,
            'avg_score': avg_score
        })
    
    # Categorize students
    above_avg = [s for s in student_stats if s['avg_score'] > 80]
    avg = [s for s in student_stats if 60 <= s['avg_score'] <= 80]
    below_avg = [s for s in student_stats if s['avg_score'] < 60]

    return render_template('dashboard_professor.html', students=students,
                           above_avg=above_avg, avg=avg, below_avg=below_avg)

# Route to view defaulter list
@app.route('/defaulters')
@login_required
def defaulters():
    if current_user.role != 'professor':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    # Students below 60%
    defaulter_students = []
    students = User.query.filter_by(role='student').all()
    for student in students:
        marks = Marks.query.filter_by(student_id=student.id).all()
        avg_score = sum([mark.score for mark in marks]) / len(marks) if marks else 0
        if avg_score < 60:
            defaulter_students.append({
                'username': student.username,
                'avg_score': avg_score
            })
    
    return render_template('defaulters.html', defaulters=defaulter_students)

if __name__ == '__main__':
    app.run(debug=True)
