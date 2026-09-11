from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
import uvicorn
import random
from sqlalchemy import create_engine, Column, String, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mtd_marathon")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ParticipantModel(Base):
    __tablename__ = "participants"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(String, index=True)
    usn = Column(String, index=True)
    student_info = Column(JSON)
    answers = Column(JSON, nullable=True)
    score = Column(Integer, default=0)
    total = Column(Integer, default=0)
    percentage = Column(Integer, default=0)
    status = Column(String, default="Joined") # "Joined"

Base.metadata.create_all(bind=engine)
# ===================================================================

active_quizzes = {}
QUIZ_FILE = "questions.json"

def load_quizzes_from_file():
    global active_quizzes
    if os.path.exists(QUIZ_FILE):
        try:
            with open(QUIZ_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for q_id, questions in data.items():
                    active_quizzes[q_id] = {
                        "quizId": q_id,
                        "questions": questions,
                        "isCompleted": False
                    }
            print(f"Successfully loaded {len(active_quizzes)} quizzes from {QUIZ_FILE}!")
        except Exception as e:
            print(f"Error reading {QUIZ_FILE}: {e}")
    else:
        print(f"Warning: {QUIZ_FILE} not found. No quizzes loaded.")

@app.on_event("startup")
async def startup_event():
    load_quizzes_from_file()

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

def compute_participant_score(quiz, student_answers):
    score = 0
    questions = quiz["questions"]
    total_questions = len(questions)

    for index, q in enumerate(questions):
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
    return score, total_questions, percentage

@app.post("/api/evaluate-quiz")
def evaluate_quiz(data: dict):
    quiz_id = data.get("quizId")
    quiz = active_quizzes.get(quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz ID not found")

    db = SessionLocal()
    try:
        participants = db.query(ParticipantModel).filter_by(quiz_id=quiz_id).all()
        evaluation_results = []

        for p in participants:
            answers = p.answers or {}
            score, total, percentage = compute_participant_score(quiz, answers)
            
            p.score = score
            p.total = total
            p.percentage = percentage
            db.commit()

            evaluation_results.append({
                "student": p.student_info,
                "score": score,
                "total": total,
                "percentage": percentage,
                "answers": answers
            })

        return {"success": True, "results": evaluation_results}
    finally:
        db.close()

@app.get("/api/get-results/{quiz_id}")
def get_quiz_results(quiz_id: str):
    quiz = active_quizzes.get(quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz ID not found")
    
    db = SessionLocal()
    try:
        participants = db.query(ParticipantModel).filter_by(quiz_id=quiz_id).all()
        evaluation_results = []

        for p in participants:
            answers = p.answers or {}
            score, total, percentage = compute_participant_score(quiz, answers)

            p.score = score
            p.total = total
            p.percentage = percentage
            db.commit()

            evaluation_results.append({
                "student": p.student_info,
                "score": score,
                "total": total,
                "percentage": percentage,
                "answers": answers
            })

        return {"success": True, "results": evaluation_results}
    finally:
        db.close()

async def start_quiz_timeline(quiz_id: str):
    quiz = active_quizzes.get(quiz_id)
    if not quiz:
        print(f"Quiz ID {quiz_id} not found for timeline start.")
        return

    questions = quiz["questions"]
    total_q = len(questions)
    
    print(f">>> STARTING QUIZ TIMELINE FOR ROOM: {quiz_id} ({total_q} questions) <<<")

    for conn in manager.active_connections.get(quiz_id, []):
        client_questions = []
        for q in questions:
            q_copy = q.copy()
            options = list(q_copy["options"])
            random.shuffle(options)
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
    # Validate if quiz_id exists before accepting or handling
    if quiz_id not in active_quizzes:
        await websocket.accept()
        await websocket.send_text(json.dumps({"type": "error", "message": "Invalid Quiz ID"}))
        await websocket.close()
        return

    await manager.connect(quiz_id, websocket)
    student_usn = None
    db = SessionLocal()

    try:
        while True:
            data_raw = await websocket.receive_text()
            data = json.loads(data_raw)
            event_type = data.get("type")

            if event_type == "join_quiz":
                student_data = data.get("studentData", {})
                student_usn = student_data.get("usn")
                websocket.student_data = student_data

                if student_usn:
                    existing = db.query(ParticipantModel).filter_by(quiz_id=quiz_id, usn=student_usn).first()
                    if not existing:
                        new_participant = ParticipantModel(
                            quiz_id=quiz_id,
                            usn=student_usn,
                            student_info=student_data,
                            status="Joined"
                        )
                        db.add(new_participant)
                        db.commit()
                        print(f"Participant {student_usn} recorded in PostgreSQL for Quiz ID: {quiz_id}.")

            elif event_type == "start_quiz_sequence":
                asyncio.create_task(start_quiz_timeline(quiz_id))

            elif event_type == "submit_answer":
                if student_usn:
                    answers_map = data.get("answersMap", {})
                    quiz = active_quizzes.get(quiz_id)
                    score, total, percentage = compute_participant_score(quiz, answers_map)
                    
                    participant = db.query(ParticipantModel).filter_by(quiz_id=quiz_id, usn=student_usn).first()
                    if participant:
                        participant.answers = answers_map
                        participant.score = score
                        participant.total = total
                        participant.percentage = percentage
                        participant.status = "Completed"
                        db.commit()
                        print(f"Score updated in PostgreSQL for {student_usn} in room {quiz_id}: {score}/{total}")
                    else:
                        new_participant = ParticipantModel(
                            quiz_id=quiz_id,
                            usn=student_usn,
                            student_info=getattr(websocket, "student_data", {"usn": student_usn}),
                            answers=answers_map,
                            score=score,
                            total=total,
                            percentage=percentage,
                            status="Completed"
                        )
                        db.add(new_participant)
                        db.commit()

    except WebSocketDisconnect:
        manager.fn_disconnect(quiz_id, websocket)
    finally:
        db.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
