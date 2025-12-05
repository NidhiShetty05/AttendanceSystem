from flask import Flask,request,jsonify 

import mysql.connector
from flask_cors import CORS




app=Flask(__name__)

CORS(app)

def get_Connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="123456",
        database="attendance_system"
        )

conn=get_Connection()
cur=conn.cursor()

@app.route("/save_attendance",methods=["post"])
def save_attendance():

    data=request.json

    lecture_key=data["lecture_key"]
    subject=data["subject"]
    year=data["year"]
    stream=data["stream"]
    lecture_date_time=data["lecture_date_time"]
    attendance=data["attendance"]
    

    cur.execute("insert into lectures values(%s,%s,%s,%s,%s)ON DUPLICATE KEY UPDATE lecture_datetime = %s",(lecture_key,subject,year,stream,lecture_date_time,lecture_date_time))

    for student_id,status in attendance.items():
        cur.execute("insert into attendance(lecture_key, student_id, status) values(%s,%s,%s) on duplicate key update status=%s",(lecture_key,student_id,status,status)) 

    conn.commit()            
    return jsonify({"message":"Attendance saved successfully!!"})


if __name__ == "__main__":
    app.run(debug=True)