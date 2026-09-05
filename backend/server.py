from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_quizzes = {}
student_responses = {}
DEFAULT_QUIZ_ID = "MTD-2026"
RESULTS_FILE = "results.json"

# Embedded questions list - guaranteed to load instantly without missing file errors on Render!
EMBEDDED_QUESTIONS = [
    {
        "question_id": 1,
        "question_text": "Which of the following represents a float data type in Python?",
        "options": ["10", "10.5", "\"10.5\"", "[10.5]"],
        "correct_answer": "10.5",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 2,
        "question_text": "Which of the following is a valid string declaration?",
        "options": ["name = John", "name = 'John'", "name = (John)", "name = {John}"],
        "correct_answer": "name = 'John'",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 3,
        "question_text": "How do you create an empty set in Python?",
        "options": ["{}", "set()", "[]", "()"],
        "correct_answer": "set()",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 4,
        "question_text": "Which data type is immutable in Python?",
        "options": ["list", "dict", "set", "tuple"],
        "correct_answer": "tuple",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 5,
        "question_text": "What is the correct syntax to define a dictionary?",
        "options": ["{1, 2, 3}", "['a': 1, 'b': 2]", "{'a': 1, 'b': 2}", "('a': 1)"],
        "correct_answer": "{'a': 1, 'b': 2}",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 6,
        "question_text": "Which function is used to find the number of elements in a string or list?",
        "options": ["count()", "size()", "len()", "length()"],
        "correct_answer": "len()",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 7,
        "question_text": "Which of the following is a valid f-string syntax?",
        "options": ["f'Hello {name}'", "format('Hello {name}')", "f'Hello name'", "'Hello {name}'.f()"],
        "correct_answer": "f'Hello {name}'",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 8,
        "question_text": "Which method is used to format strings using placeholders like '{}'?",
        "options": ["str()", ".format()", "eval()", "print()"],
        "correct_answer": ".format()",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 9,
        "question_text": "Which loop runs as long as a condition remains True?",
        "options": ["for loop", "while loop", "loop", "repeat loop"],
        "correct_answer": "while loop",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 10,
        "question_text": "What causes a while loop to become an infinite loop?",
        "options": ["A condition that never becomes False", "Using a break statement", "Using a counter variable", "Setting a timer"],
        "correct_answer": "A condition that never becomes False",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 11,
        "question_text": "Which of the following creates a list?",
        "options": ["[1, 2, 3]", "(1, 2, 3)", "{1, 2, 3}", "{'a': 1}"],
        "correct_answer": "[1, 2, 3]",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 12,
        "question_text": "Which data type stores key-value pairs?",
        "options": ["list", "tuple", "set", "dict"],
        "correct_answer": "dict",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 13,
        "question_text": "Can a set contain duplicate values in Python?",
        "options": ["Yes", "No", "Only for strings", "Only for numbers"],
        "correct_answer": "No",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 14,
        "question_text": "What is the output type of len('Python')?",
        "options": ["str", "float", "int", "list"],
        "correct_answer": "int",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 15,
        "question_text": "Which brackets are used to define a tuple?",
        "options": ["[]", "{}", "()", "<>"],
        "correct_answer": "()",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 16,
        "question_text": "Which keyword is used to start a while loop?",
        "options": ["for", "while", "loop", "repeat"],
        "correct_answer": "while",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 17,
        "question_text": "Which of the following is a valid float value?",
        "options": ["3", "3.14", "'3.14'", "[3, 14]"],
        "correct_answer": "3.14",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 18,
        "question_text": "How are elements inside a set separated?",
        "options": ["Semicolons", "Colons", "Commas", "Spaces"],
        "correct_answer": "Commas",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 19,
        "question_text": "Which of the following uses key lookup instead of position lookup?",
        "options": ["list", "tuple", "string", "dict"],
        "correct_answer": "dict",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 20,
        "question_text": "Which string formatting technique uses curly braces {} and a preceding letter f?",
        "options": ["f-string", ".format()", "percent formatting", "template string"],
        "correct_answer": "f-string",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 21,
        "question_text": "What will be the output of: x = 'Hello'; print(len(x))",
        "options": ["5", "6", "Hello", "Error"],
        "correct_answer": "6",
        "timer_seconds": 20,
        "type": "radio"
    },
    {
        "question_id": 22,
        "question_text": "What will be the output of: a = 10; b = 20; print(f'{a}{b}')",
        "options": ["30", "1020", "Error", "a b"],
        "correct_answer": "1020",
        "timer_seconds": 20,
        "type": "radio"
    },
    {
        "question_id": 23,
        "question_text": "What will be the output of: text = '{} and {}'; print(text.format('Python', 'Java'))",
        "options": ["Python and Java", "{} and {}", "Error", "Java and Python"],
        "correct_answer": "Python and Java",
        "timer_seconds": 20,
        "type": "radio"
    },
    {
        "question_id": 24,
        "question_text": "What will be the output of: x = 5; while x < 7: print(x); x = x + 1",
        "options": ["5 6", "5 6 7", "6 7", "Infinite loop"],
        "correct_answer": "5 6",
        "timer_seconds": 20,
        "type": "radio"
    },
    {
        "question_id": 25,
        "question_text": "What will be the output of: data = [10, 20]; print(len(data))",
        "options": ["1", "2", "10", "Error"],
        "correct_answer": "2",
        "timer_seconds": 20,
        "type": "radio"
    },
    {
        "question_id": 26,
        "question_text": "What will be the output of: info = {'name': 'Alice'}; print(len(info))",
        "options": ["0", "1", "name", "Error"],
        "correct_answer": "1",
        "timer_seconds": 20,
        "type": "radio"
    },
    {
        "question_id": 27,
        "question_text": "What will be the output of: items = {1, 2, 2, 3}; print(len(items))",
        "options": ["4", "3", "2", "Error"],
        "correct_answer": "3",
        "timer_seconds": 20,
        "type": "radio"
    },
    {
        "question_id": 28,
        "question_text": "What will be the output of: msg = 'Data'; print(f'Value is {msg}')",
        "options": ["Value is Data", "Value is msg", "Data", "Error"],
        "correct_answer": "Value is Data",
        "timer_seconds": 20,
        "type": "radio"
    },
    {
        "question_id": 29,
        "question_text": "What will be the output of: val = 3.5; print(type(val))",
        "options": ["<class 'int'>", "<class 'float'>", "<class 'str'>", "<class 'bool'>"],
        "correct_answer": "<class 'float'>",
        "timer_seconds": 20,
        "type": "radio"
    },
    {
        "question_id": 30,
        "question_text": "What will be the output of: x = 2; while x == 2: print('Loop'); x = 3",
        "options": ["Loop", "Loop Loop", "Error", "No output"],
        "correct_answer": "Loop",
        "timer_seconds": 20,
        "type": "radio"
    },
    {
        "question_id": 31,
        "question_text": "Which of the following structures allows heterogeneous data types (ints, strings, floats) together?",
        "options": ["list", "int only", "float only", "dict keys only"],
        "correct_answer": "list",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 32,
        "question_text": "Which collection type is unordered and unindexed?",
        "options": ["list", "tuple", "string", "set"],
        "correct_answer": "set",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 33,
        "question_text": "How do you define a tuple with a single element?",
        "options": ["(5)", "(5,)", "[5]", "{5}"],
        "correct_answer": "(5,)",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 34,
        "question_text": "Which python component evaluates the length of an iterable container?",
        "options": ["len()", "count()", "size()", "sum()"],
        "correct_answer": "len()",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 35,
        "question_text": "Which loop structure is best suited when the exact number of iterations is unknown beforehand?",
        "options": ["for loop", "while loop", "range loop", "static loop"],
        "correct_answer": "while loop",
        "timer_seconds": 15,
        "type": "radio"
    },
    {
        "question_id": 36,
        "question_text": "What will be the output of: x = 1; while x < 4: print(x); x = x + 1",
        "options": ["1 2 3", "1 2 3 4", "2 3 4", "1 2"],
        "correct_answer": "1 2 3",
        "timer_seconds": 25,
        "type": "radio"
    },
    {
        "question_id": 37,
        "question_text": "What will be the output of: name = 'Code'; print('Language: {}'.format(name))",
        "options": ["Code", "Language: Code", "Language: {}", "Error"],
        "correct_answer": "Language: Code",
        "timer_seconds": 25,
        "type": "radio"
    },
    {
        "question_id": 38,
        "question_text": "What will be the output of: my_dict = {'a': 10, 'b': 20}; print(len(my_dict))",
        "options": ["2", "4", "Error", "3"],
        "correct_answer": "2",
        "timer_seconds": 25,
        "type": "radio"
    },
    {
        "question_id": 39,
        "question_text": "What will be the output of: values = (10, 20, 30); print(type(values))",
        "options": ["<class 'list'>", "<class 'tuple'>", "<class 'set'>", "<class 'dict'>"],
        "correct_answer": "<class 'tuple'>",
        "timer_seconds": 25,
        "type": "radio"
    },
    {
        "question_id": 40,
        "question_text": "What will be the output of: text = 'Python'; print(len(text))",
        "options": ["5", "6", "7", "Error"],
        "correct_answer": "6",
        "timer_seconds": 25,
        "type": "radio"
    }
]

def save_responses_to_disk():
    try:
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(student_responses, f, indent=4)
    except Exception as e:
        print(f"Error saving results: {e}")

def load_responses_from_disk():
    global student_responses
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                student_responses = json.load(f)
        except Exception:
            student_responses = {}

def load_default_quiz():
    active_quizzes[DEFAULT_QUIZ_ID] = {
        "quizId": DEFAULT_QUIZ_ID,
        "questions": EMBEDDED_QUESTIONS,
        "isCompleted": False
    }
    print(f"Successfully loaded {len(EMBEDDED_QUESTIONS)} questions directly into memory!")
    
@app.on_event("startup")
async def startup_event():
    load_default_quiz()
    load_responses_from_disk()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, quiz_id: str, websocket: WebSocket):
        await websocket.accept()
        if quiz_id not in self.active_connections:
            self.active_connections[quiz_id] = []
        self.active_connections[quiz_id].append(websocket)
        print(f"Client connected to room: {quiz_id}")

    def fn_disconnect(self, qid: str, ws: WebSocket):
        if qid in self.active_connections and ws in self.active_connections[qid]:
            self.active_connections[qid].remove(ws)

manager = ConnectionManager()

@app.post("/api/evaluate-quiz")
def evaluate_quiz(data: dict):
    quiz_id = data.get("quizId", DEFAULT_QUIZ_ID)
    quiz = active_quizzes.get(quiz_id)
    responses = student_responses.get(quiz_id, {})

    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    evaluation_results = []
    for usn, resp in responses.items():
        student_data = resp.get("studentInfo", {"usn": usn})
        student_answers = resp.get("answers", {})
        score = 0
        total_questions = len(quiz["questions"])

        for index, q in enumerate(quiz["questions"]):
            ans_key = str(index)
            student_choice = student_answers.get(ans_key, [])
            correct_ans = q["correct_answer"]

            if q["type"] == "radio":
                if str(student_choice).strip().lower() == str(correct_ans).strip().lower():
                    score += 1
            elif q["type"] == "checkbox":
                if isinstance(student_choice, list):
                    student_set = {str(x).strip().lower() for x in student_choice}
                    correct_set = {str(x).strip().lower() for x in correct_ans.split(",")}
                    if student_set == correct_set:
                        score += 1

        percentage = round((score / total_questions) * 100, 2) if total_questions > 0 else 0.0
        evaluation_results.append({
            "student": student_data,
            "score": score,
            "total": total_questions,
            "percentage": percentage,
            "answers": student_answers
        })

    return {"success": True, "results": evaluation_results}

@app.get("/api/get-results/{quiz_id}")
def get_quiz_results(quiz_id: str):
    quiz = active_quizzes.get(quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    responses = student_responses.get(quiz_id, {})
    evaluation_results = []
    
    for usn, resp in responses.items():
        student_data = resp.get("studentInfo", {"usn": usn})
        student_answers = resp.get("answers", {})
        score = 0
        total_questions = len(quiz["questions"])

        for index, q in enumerate(quiz["questions"]):
            ans_key = str(index)
            student_choice = student_answers.get(ans_key, [])
            correct_ans = q["correct_answer"]

            if q["type"] == "radio":
                if str(student_choice).strip().lower() == str(correct_ans).strip().lower():
                    score += 1
            elif q["type"] == "checkbox":
                if isinstance(student_choice, list):
                    student_set = {str(x).strip().lower() for x in student_choice}
                    correct_set = {str(x).strip().lower() for x in correct_ans.split(",")}
                    if student_set == correct_set:
                        score += 1

        percentage = round((score / total_questions) * 100, 2) if total_questions > 0 else 0.0
        evaluation_results.append({
            "student": student_data,
            "score": score,
            "total": total_questions,
            "percentage": percentage,
            "answers": student_answers
        })

    return {"success": True, "results": evaluation_results}

async def start_quiz_timeline(quiz_id: str):
    if quiz_id not in active_quizzes:
        load_default_quiz()

    quiz = active_quizzes.get(quiz_id)
    questions = quiz["questions"]
    total_q = len(questions)
    
    print(f">>> STARTING QUIZ TIMELINE FOR ROOM: {quiz_id} ({total_q} questions) <<<")

    # Send unique shuffled option layouts to each connected client separately
    for conn in manager.active_connections.get(quiz_id, []):
        client_questions = []
        for q in questions:
            q_copy = q.copy()
            options = list(q_copy["options"])
            random.shuffle(options)  # Shuffles options randomly for this user
            q_copy["options"] = options
            client_questions.append(q_copy)

        await conn.send_text(json.dumps({
            "type": "quiz_started",
            "questions": client_questions
        }))

    for index, current_q in enumerate(questions):
        duration = current_q["timer_seconds"]
        host_payload = {
            "type": "host_question_sync",
            "question_text": current_q["question_text"],
            "timer_seconds": duration,
            "index": index,
            "total": total_q
        }
        for conn in manager.active_connections.get(quiz_id, []):
            await conn.send_text(json.dumps(host_payload))
        await asyncio.sleep(duration)

    quiz["isCompleted"] = True
    for conn in manager.active_connections.get(quiz_id, []):
        await conn.send_text(json.dumps({
            "type": "host_quiz_completed_display",
            "duration": 10
        }))
    
    await asyncio.sleep(10)

    for conn in manager.active_connections.get(quiz_id, []):
        await conn.send_text(json.dumps({
            "type": "enable_results_button"
        }))

@app.websocket("/ws/{quiz_id}")
async def websocket_endpoint(websocket: WebSocket, quiz_id: str):
    await manager.connect(quiz_id, websocket)
    student_usn = None

    try:
        while True:
            data_raw = await websocket.receive_text()
            data = json.loads(data_raw)
            event_type = data.get("type")

            if event_type == "join_quiz":
                student_data = data.get("studentData", {})
                student_usn = student_data.get("usn")
                websocket.student_data = student_data

            elif event_type == "start_quiz_sequence":
                asyncio.create_task(start_quiz_timeline(quiz_id))

            elif event_type == "submit_answer":
                if student_usn:
                    if quiz_id not in student_responses:
                        student_responses[quiz_id] = {}
                    student_responses[quiz_id][student_usn] = {
                        "studentInfo": getattr(websocket, "student_data", {"usn": student_usn}),
                        "answers": data.get("answersMap", {})
                    }
                    save_responses_to_disk()

    except WebSocketDisconnect:
        manager.fn_disconnect(quiz_id, websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=5000, reload=True)
