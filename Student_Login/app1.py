from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import extract, func

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

ATTENDANCE_THRESHOLD = 75  # percentage

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)  # 'present' or 'absent'

    student = db.relationship('Student', backref=db.backref('attendances', lazy=True))
    subject = db.relationship('Subject', backref=db.backref('attendances', lazy=True))


def create_tables():
    db.create_all()

@app.route('/teacher/attendance', methods=['POST'])
def mark_attendance():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid or missing JSON"}), 400
    
    student_id = data.get('student_id')
    subject_id = data.get('subject_id')
    date_str = data.get('date')  # Expecting 'YYYY-MM-DD'
    status = data.get('status')  # 'present' or 'absent'

    if not all([student_id, subject_id, date_str, status]):
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        from datetime import datetime
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Date must be in YYYY-MM-DD format"}), 400

    if status not in ['present', 'absent']:
        return jsonify({"error": "Status must be 'present' or 'absent'"}), 400

    # Check if student and subject exist
    student = Student.query.get(student_id)
    subject = Subject.query.get(subject_id)
    if not student or not subject:
        return jsonify({"error": "Invalid student_id or subject_id"}), 400

    # Check if attendance already marked for this student, subject and date
    existing = Attendance.query.filter_by(student_id=student_id, subject_id=subject_id, date=date).first()
    if existing:
        existing.status = status
    else:
        attendance = Attendance(student_id=student_id, subject_id=subject_id, date=date, status=status)
        db.session.add(attendance)
    db.session.commit()

    return jsonify({"message": "Attendance marked successfully"}), 200

@app.route('/student/attendance/<int:student_id>/monthly/<int:year>/<int:month>', methods=['GET'])
def monthly_attendance(student_id, year, month):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    # Aggregate attendance per subject for given month
    attendance_data = db.session.query(
        Attendance.subject_id,
        Subject.name,
        func.count(Attendance.id).label('total_classes'),
        func.sum(func.case([(Attendance.status == 'present', 1)], else_=0)).label('present_count')
    ).join(Subject).filter(
        Attendance.student_id == student_id,
        extract('year', Attendance.date) == year,
        extract('month', Attendance.date) == month
    ).group_by(Attendance.subject_id).all()

    result = []
    for subj_id, subj_name, total, present in attendance_data:
        percent = (present / total) * 100 if total else 0
        defaulter = percent < ATTENDANCE_THRESHOLD
        result.append({
            "subject_id": subj_id,
            "subject_name": subj_name,
            "total_classes": total,
            "present": present,
            "attendance_percentage": round(percent, 2),
            "defaulter": defaulter
        })

    return jsonify({"student_id": student_id, "year": year, "month": month, "attendance": result})

@app.route('/student/attendance/<int:student_id>/semester/<int:start_month>/<int:end_month>/<int:year>', methods=['GET'])
def semester_attendance(student_id, start_month, end_month, year):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    
    # Aggregate attendance per subject for semester months range
    attendance_data = db.session.query(
        Attendance.subject_id,
        Subject.name,
        func.count(Attendance.id).label('total_classes'),
        func.sum(func.case([(Attendance.status == 'present', 1)], else_=0)).label('present_count')
    ).join(Subject).filter(
        Attendance.student_id == student_id,
        extract('year', Attendance.date) == year,
        Attendance.date >= f"{year}-{start_month:02d}-01",
        Attendance.date <= f"{year}-{end_month:02d}-31"
    ).group_by(Attendance.subject_id).all()

    result = []
    for subj_id, subj_name, total, present in attendance_data:
        percent = (present / total) * 100 if total else 0
        defaulter = percent < ATTENDANCE_THRESHOLD
        result.append({
            "subject_id": subj_id,
            "subject_name": subj_name,
            "total_classes": total,
            "present": present,
            "attendance_percentage": round(percent, 2),
            "defaulter": defaulter
        })

    return jsonify({"student_id": student_id, "year": year, "semester_months": f"{start_month}-{end_month}", "attendance": result})

if __name__ == '__main__':
    app.run(debug=True)
