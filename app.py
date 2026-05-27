import os
import mysql.connector
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')


def get_db_connection(host=None, user=None, password=None):
    return mysql.connector.connect(
        host=host or os.getenv("DB_HOST", "localhost"),
        user=user or os.getenv("DB_USER", "root"),
        password=password or os.getenv("DB_PASSWORD", "")
    )


def setup_database_tables(db):
    cursor = db.cursor()

    cursor.execute("CREATE DATABASE IF NOT EXISTS online_quiz_exam")
    db.database = 'online_quiz_exam'

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(100)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INT PRIMARY KEY AUTO_INCREMENT,
        question VARCHAR(255),
        option1 VARCHAR(100),
        option2 VARCHAR(100),
        option3 VARCHAR(100),
        option4 VARCHAR(100),
        answer VARCHAR(100)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        result_id INT PRIMARY KEY AUTO_INCREMENT,
        student_name VARCHAR(100),
        marks INT
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM questions")
    count = cursor.fetchone()[0]

    if count == 0:
        cursor.execute("""
        INSERT INTO questions 
        (question, option1, option2, option3, option4, answer)
        VALUES
        (
            'What is Python?',
            'Programming Language',
            'Animal',
            'Movie',
            'Game',
            'Programming Language'
        ),
        (
            'Which keyword is used for loop?',
            'if',
            'for',
            'print',
            'break',
            'for'
        ),
        (
            'Which symbol is used for comments in Python?',
            '//',
            '#',
            '/*',
            '--',
            '#'
        )
        """)
        db.commit()

    cursor.close()


def is_db_connected():
    try:
        db = get_db_connection()
        db.close()
        return True
    except:
        return False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/status', methods=['GET'])
def db_status():
    return jsonify({"connected": is_db_connected()})


@app.route('/api/connect', methods=['POST'])
def connect_db():
    data = request.json or {}

    host = data.get("host", "localhost")
    user = data.get("user", "root")
    password = data.get("password", "")

    try:
        db = get_db_connection(host, user, password)

        with open('.env', "w") as f:
            f.write(f"DB_HOST={host}\n")
            f.write(f"DB_USER={user}\n")
            f.write(f"DB_PASSWORD={password}\n")

        os.environ["DB_HOST"] = host
        os.environ["DB_USER"] = user
        os.environ["DB_PASSWORD"] = password

        setup_database_tables(db)
        db.close()

        return jsonify({
            "success": True,
            "message": "Database connected successfully!"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/register', methods=['POST'])
def register_student():
    data = request.json or {}
    name = data.get("name", "")

    if not name:
        return jsonify({"error": "Name is required"}), 400

    try:
        db = get_db_connection()
        db.database = 'online_quiz_exam'

        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO students (name) VALUES (%s)",
            (name,)
        )

        db.commit()

        student_id = cursor.lastrowid

        cursor.close()
        db.close()

        return jsonify({
            "success": True,
            "student_id": student_id,
            "name": name
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/questions', methods=['GET'])
def get_questions():
    try:
        db = get_db_connection()
        db.database = 'online_quiz_exam'

        cursor = db.cursor(dictionary=True)

        cursor.execute("""
        SELECT id, question, option1, option2, option3, option4 
        FROM questions
        """)

        questions = cursor.fetchall()

        cursor.close()
        db.close()

        return jsonify(questions)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/submit', methods=['POST'])
def submit_quiz():
    data = request.json or {}

    name = data.get("name", "")
    answers = data.get("answers", {})

    if not name:
        return jsonify({"error": "Student name required"}), 400

    try:
        db = get_db_connection()
        db.database = 'online_quiz_exam'

        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM questions")
        db_questions = cursor.fetchall()

        score = 0
        details = []

        for q in db_questions:

            q_id = str(q['id'])

            user_ans = answers.get(q_id, "")
            correct_answer = q['answer']

            options = [
                q['option1'],
                q['option2'],
                q['option3'],
                q['option4']
            ]

            if user_ans.isdigit() and 1 <= int(user_ans) <= 4:
                user_ans = options[int(user_ans) - 1]

            is_correct = user_ans.lower() == correct_answer.lower()

            if is_correct:
                score += 1

            details.append({
                "question_id": q['id'],
                "question": q['question'],
                "options": options,
                "user_answer": user_ans,
                "correct_answer": correct_answer,
                "is_correct": is_correct
            })

        cursor.execute(
            "INSERT INTO results (student_name, marks) VALUES (%s, %s)",
            (name, score)
        )

        db.commit()

        cursor.close()
        db.close()

        return jsonify({
            "success": True,
            "student_name": name,
            "score": score,
            "total": len(db_questions),
            "percentage": (score / len(db_questions)) * 100 if db_questions else 0,
            "details": details
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    try:
        db = get_db_connection()
        db.database = 'online_quiz_exam'

        cursor = db.cursor(dictionary=True)

        cursor.execute("""
        SELECT * FROM results 
        ORDER BY marks DESC, result_id ASC
        """)

        results = cursor.fetchall()

        cursor.close()
        db.close()

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':

    try:
        if is_db_connected():
            db = get_db_connection()
            setup_database_tables(db)
            db.close()
    except:
        pass

    app.run(debug=True, port=5000)