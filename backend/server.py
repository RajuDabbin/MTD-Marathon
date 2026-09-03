from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
import ast

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
CSV_FILE = "quiz_questions.csv"

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
    questions = []
    
    if os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, mode="r", encoding="utf-8") as f:
                lines = f.readlines()
                
            # Skip header line if it exists
            start_idx = 1 if lines and "question_id" in lines[0].lower() else 0
            
            for index, line in enumerate(lines[start_idx:], start=1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Find the bracket positions for options [...]
                    start_bracket = line.find('[')
                    end_bracket = line.rfind(']')
                    
                    if start_bracket == -1 or end_bracket == -1:
                        print(f"Skipping line {index}: No option brackets found.")
                        continue
                        
                    # Part 1: Before options -> question_id and question_text
                    prefix = line[:start_bracket].strip()
                    if prefix.endswith(','):
                        prefix = prefix[:-1]
                    
                    first_comma = prefix.find(',')
                    if first_comma == -1:
                        q_id = index
                        q_text = prefix
                    else:
                        q_id_str = prefix[:first_comma].strip()
                        q_id = int(q_id_str) if q_id_str.isdigit() else index
                        q_text = prefix[first_comma + 1:].strip().strip('"')
                        
                    # Part 2: The options list inside brackets
                    options_raw = line[start_bracket:end_bracket + 1]
                    try:
                        options_list = ast.literal_eval(options_raw)
                    except Exception:
                        # Fallback parsing if literal_eval fails on raw strings
                        options_list = [opt.strip().strip('"').strip("'") for opt in options_raw[1:-1].split(',')]
                        
                    # Part 3: After options -> correct_answer, timer_seconds, type
                    suffix = line[end_bracket + 1:].strip()
                    if suffix.startswith(','):
                        suffix = suffix[1:]
                        
                    suffix_parts = [p.strip().strip('"').strip("'") for p in suffix.split(',')]
                    
                    # Expecting at least type and timer at the end, correct_answer right after options
                    q_type = suffix_parts[-1] if len(suffix_parts) >= 1 else "radio"
                    q_timer = int(suffix_parts[-2]) if len(suffix_parts) >= 2 and suffix_parts[-2].isdigit() else 15
                    
                    # Everything else between suffix start and last 2 parts is the correct answer
                    correct_ans_parts = suffix_parts[:-2] if len(suffix_parts) >= 2 else suffix_parts
                    q_correct = ",".join(correct_ans_parts).strip().strip('"').strip("'")
                    
                    questions.append({
                        "question_id": q_id,
                        "question_text": q_text,
                        "options": options_list,
                        "correct_answer": q_correct,
                        "timer_seconds": q_timer,
                        "type": q_type
                    })
                except Exception as row_err:
                    print(f"Skipping malformed row {index}: {row_err}")
                    
            print(f"Successfully loaded {len(questions)} questions from {CSV_FILE}!")
        except Exception as e:
            print(f"Error parsing CSV file: {e}")
    else:
        print(f"Warning: {CSV_FILE} not found in repository root!")

    active_quizzes[DEFAULT_QUIZ_ID] = {
        "quizId": DEFAULT_QUIZ_ID,
        "questions": questions,
        "isCompleted": False
    }

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

    for conn in manager.active_connections.get(quiz_id, []):
        await conn.send_text(json.dumps({
            "type": "quiz_started",
            "questions": questions
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
    
    Asyncio.sleep(10)

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
