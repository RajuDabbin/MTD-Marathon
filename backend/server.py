from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
import csv
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
                content = f.read()
                
            content = content.replace("\r\n", "\n")
            lines = content.split("\n")
            
            for index, line in enumerate(lines, start=1):
                line = line.strip()
                if not line or "question_id" in line.lower():
                    continue
                
                try:
                    # 1. Find the option brackets [...]
                    start_b = line.find('[')
                    end_b = line.rfind(']')
                    
                    if start_b == -1 or end_b == -1:
                        continue
                        
                    # 2. Extract ID and Question Text from the left side
                    left = line[:start_b].strip()
                    if left.endswith(','):
                        left = left[:-1]
                        
                    comma_pos = left.find(',')
                    if comma_pos == -1:
                        continue
                        
                    q_id_str = left[:comma_pos].strip().strip('"\'')
                    q_id = int(q_id_str) if q_id_str.isdigit() else index
                    q_text = left[comma_pos+1:].strip().strip('"\'')
                    
                    # 3. Extract Options safely and split them if they got mashed together
                    options_raw = line[start_b:end_b+1]
                    try:
                        options_list = ast.literal_eval(options_raw)
                        if not isinstance(options_list, list):
                            raise ValueError()
                    except Exception:
                        # Fallback: if it got mashed, clean and split manually
                        cleaned_raw = options_raw.strip("[]")
                        # If it contains our distinct python option patterns, split them intelligently
                        options_list = [o.strip().strip('"\'') for o in cleaned_raw.split(',') if o.strip()]
                    # 4. Extract Answer, Timer, and Type from the right side
                    right = line[end_b+1:].strip()
                    if right.startswith(','):
                        right = right[1:]
                        
                    # Parse remaining values using csv reader on the right snippet
                    parts = next(csv.reader([right]))
                    parts = [p.strip().strip('"\'') for p in parts if p.strip()]
                    
                    if len(parts) >= 3:
                        q_type = parts[-1]
                        q_timer_str = parts[-2]
                        q_timer = int(q_timer_str) if q_timer_str.isdigit() else 15
                        q_correct = ",".join(parts[:-2])
                    elif len(parts) == 2:
                        q_type = "radio"
                        q_timer_str = parts[-1]
                        q_timer = int(q_timer_str) if q_timer_str.isdigit() else 15
                        q_correct = parts[0]
                    else:
                        q_type = "radio"
                        q_timer = 15
                        q_correct = parts[0] if parts else ""
                        
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
                        
            print(f"Successfully loaded {len(questions)} questions cleanly from {CSV_FILE}!")
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
