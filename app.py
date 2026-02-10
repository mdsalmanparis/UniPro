from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import plotly
import plotly.express as px
import pandas as pd
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'student_data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS ---
enrollments = db.Table('enrollments',
    db.Column('student_id', db.Integer, db.ForeignKey('student.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    register_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    mobile_number = db.Column(db.String(20), nullable=False)
    email_address = db.Column(db.String(120), nullable=False)
    address = db.Column(db.Text, nullable=False)
    dob = db.Column(db.Date, nullable=False)
    blood_group = db.Column(db.String(5), nullable=False)
    batch_start_year = db.Column(db.Integer, nullable=False)
    batch_end_year = db.Column(db.Integer, nullable=False)
    degree = db.Column(db.String(20), nullable=False) 
    program = db.Column(db.String(100), nullable=False)
    total_semesters = db.Column(db.Integer, nullable=False)
    courses = db.relationship('Course', secondary=enrollments, backref=db.backref('students', lazy='dynamic'))

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    credit = db.Column(db.Integer, nullable=False)
    offering_dept = db.Column(db.String(50), nullable=False)
    hours = db.Column(db.Integer, nullable=False)
    instructor_name = db.Column(db.String(100), nullable=False)

class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    cia1 = db.Column(db.Float, nullable=False)
    cia2 = db.Column(db.Float, nullable=False)
    model = db.Column(db.Float, nullable=False)
    internal = db.Column(db.Float, nullable=False)
    semester = db.Column(db.Float, nullable=False)
    total_internal_40 = db.Column(db.Float, nullable=False)
    total_external_60 = db.Column(db.Float, nullable=False)
    final_mark_100 = db.Column(db.Float, nullable=False)
    student = db.relationship('Student', backref='evaluations')
    course = db.relationship('Course', backref='evaluations')

with app.app_context():
    db.create_all()

# --- ROUTES ---

# 1. DASHBOARD (Analytics Only)
@app.route('/')
def index():
    students = Student.query.all()
    
    # KPIs
    total_students = len(students)
    unique_programs = 0
    latest_batch = "N/A"
    
    chart_degree_json = None
    chart_program_json = None
    chart_batch_json = None

    if students:
        data = [{'Degree': s.degree, 'Program': s.program, 'Batch': s.batch_start_year} for s in students]
        df = pd.DataFrame(data)

        unique_programs = df['Program'].nunique()
        latest_batch = df['Batch'].max()

        # Charts
        fig_degree = px.bar(df.groupby('Degree').size().reset_index(name='Count'), 
                            x='Degree', y='Count', color='Degree', title="By Degree")
        chart_degree_json = json.dumps(fig_degree, cls=plotly.utils.PlotlyJSONEncoder)

        fig_program = px.pie(df.groupby('Program').size().reset_index(name='Count'), 
                             values='Count', names='Program', title="By Program")
        chart_program_json = json.dumps(fig_program, cls=plotly.utils.PlotlyJSONEncoder)

        fig_batch = px.line(df.groupby('Batch').size().reset_index(name='Count'), 
                            x='Batch', y='Count', markers=True, title="Enrollment Growth")
        chart_batch_json = json.dumps(fig_batch, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('index.html', 
                           total_students=total_students,
                           unique_programs=unique_programs,
                           latest_batch=latest_batch,
                           chart_degree=chart_degree_json,
                           chart_program=chart_program_json,
                           chart_batch=chart_batch_json,
                           students=students) # Passed for the 'Recent List'

# 2. STUDENT MANAGEMENT (New Route)
@app.route('/student', methods=['GET', 'POST'])
def student():
    if request.method == 'POST':
        try:
            new_student = Student(
                register_number=request.form['register_number'],
                name=request.form['name'],
                mobile_number=request.form['mobile_number'],
                email_address=request.form['email_address'],
                address=request.form['address'],
                dob=datetime.strptime(request.form['dob'], '%Y-%m-%d').date(),
                blood_group=request.form['blood_group'],
                batch_start_year=int(request.form['batch_start_year']),
                batch_end_year=int(request.form['batch_end_year']),
                degree=request.form['degree'],
                program=request.form['program'],
                total_semesters=int(request.form['total_semesters'])
            )
            db.session.add(new_student)
            db.session.commit()
            flash('Student Registered Successfully!', 'success')
            return redirect(url_for('student'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('student'))

    # GET Request: Show List
    students = Student.query.order_by(Student.id.desc()).all()
    return render_template('student.html', students=students)

# 3. COURSES
@app.route('/courses', methods=['GET', 'POST'])
def courses():
    if request.method == 'POST':
        try:
            new_course = Course(
                name=request.form['name'],
                course_code=request.form['course_code'],
                credit=int(request.form['credit']),
                offering_dept=request.form['offering_dept'],
                hours=int(request.form['hours']),
                instructor_name=request.form['instructor_name']
            )
            db.session.add(new_course)
            db.session.commit()
            flash('Course Created!', 'success')
            return redirect(url_for('courses'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('courses'))
    
    courses_list = Course.query.all()
    return render_template('courses.html', courses=courses_list)

# 4. ENROLLMENTS
@app.route('/enrollments', methods=['GET', 'POST'])
def enrollments():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        course_id = request.form.get('course_id')
        if student_id and course_id:
            s = Student.query.get(student_id)
            c = Course.query.get(course_id)
            if c not in s.courses:
                s.courses.append(c)
                db.session.commit()
                flash('Enrolled!', 'success')
            else:
                flash('Already Enrolled', 'warning')
        return redirect(url_for('enrollments'))

    students = Student.query.all()
    courses = Course.query.all()
    
    course_data = [{'id': c.id, 'code': c.course_code, 'name': c.name, 'count': c.students.count()} for c in courses]
    
    selected_course = None
    enrolled_students = []
    if request.args.get('view_course_id'):
        selected_course = Course.query.get(request.args.get('view_course_id'))
        if selected_course:
            enrolled_students = selected_course.students.all()

    return render_template('enrollments.html', students=students, courses=courses, course_stats=course_data, selected_course=selected_course, enrolled_students=enrolled_students)

# 5. EVALUATION
@app.route('/evaluation', methods=['GET', 'POST'])
def evaluation():
    if request.method == 'POST':
        try:
            new_eval = Evaluation(
                student_id=request.form['student_id'],
                course_id=request.form['course_id'],
                cia1=float(request.form['cia1']),
                cia2=float(request.form['cia2']),
                model=float(request.form['model']),
                internal=float(request.form['internal']),
                semester=float(request.form['semester']),
                total_internal_40=float(request.form['calc_internal']),
                total_external_60=float(request.form['calc_external']),
                final_mark_100=float(request.form['calc_total'])
            )
            db.session.add(new_eval)
            db.session.commit()
            flash('Marks Saved!', 'success')
            return redirect(url_for('evaluation'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('evaluation'))

    students = Student.query.all()
    courses = Course.query.all()
    evaluations = Evaluation.query.all()
    return render_template('evaluation.html', students=students, courses=courses, evaluations=evaluations)

if __name__ == "__main__":
    app.run(debug=True)