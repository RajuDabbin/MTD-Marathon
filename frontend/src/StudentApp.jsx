import React, { useState, useRef } from 'react';

const BACKEND_WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:5000';

export default function StudentApp() {
  const [joined, setJoined] = useState(false);
  const [quizId, setQuizId] = useState('');
  const [student, setStudent] = useState({
    email: '',
    username: '',
    usn: '',
    college: '',
    semester: '',
    phone: ''
  });

  const [quizStarted, setQuizStarted] = useState(false);
  const [questions, setQuestions] = useState([]);
  const [answersMap, setAnswersMap] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const wsRef = useRef(null);

  const handleJoin = (e) => {
    e.preventDefault();
    if (!quizId.trim()) {
      alert("Please enter a Quiz ID.");
      return;
    }

    // STRICT VALIDATION RULES
    const nameRegex = /^[A-Za-z\s]+$/;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const phoneRegex = /^[6-9]\d{9}$/;

    if (!nameRegex.test(student.username.trim())) {
      alert("Error: Full Name should only include alphabets and spaces.");
      return;
    }

    if (!emailRegex.test(student.email.trim())) {
      alert("Error: Please enter a valid email format.");
      return;
    }

    const semNum = Number(student.semester);
    if (isNaN(semNum) || semNum < 1 || semNum > 8) {
      alert("Error: Semester must be a number between 1 and 8.");
      return;
    }

    if (!nameRegex.test(student.college.trim())) {
      alert("Error: College Name should only include alphabets and spaces.");
      return;
    }

    if (!phoneRegex.test(student.phone.trim())) {
      alert("Error: Phone number must be strictly 10 digits and start with 6, 7, 8, or 9.");
      return;
    }

    const websocket = new WebSocket(`${BACKEND_WS_URL}/ws/${quizId.trim()}`);

    websocket.onopen = () => {
      websocket.send(JSON.stringify({ type: 'join_quiz', studentData: student }));
      setJoined(true);
    };

    websocket.onerror = () => {
      alert("Could not connect to backend server. Make sure server.py is running!");
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'quiz_started') {
        setQuestions(data.questions);
        setQuizStarted(true);
      }
    };

    wsRef.current = websocket;
  };

  const handleAnswerChange = (qIndex, option, type) => {
    if (type === 'radio') {
      setAnswersMap({ ...answersMap, [qIndex]: option });
    } else {
      const current = answersMap[qIndex] || [];
      const updated = current.includes(option) ? current.filter(x => x !== option) : [...current, option];
      setAnswersMap({ ...answersMap, [qIndex]: updated });
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'submit_answer', answersMap }));
    }
    setSubmitted(true);
  };

  if (!joined) {
    return (
      <div className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center p-6">
        <div className="bg-slate-800 border border-slate-700 p-8 rounded-2xl shadow-2xl max-w-md w-full">
          <div className="text-center mb-6">
            <h1 className="text-2xl font-extrabold text-emerald-400">MTD MARATHON</h1>
            <p className="text-xs text-slate-400 mt-1">Student Examination Portal</p>
          </div>
          <form onSubmit={handleJoin} className="space-y-4">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Quiz Room ID</label>
              <input type="text" value={quizId} onChange={e => setQuizId(e.target.value)} required className="w-full p-3 bg-slate-900 border border-slate-700 rounded-xl text-sm outline-none focus:border-emerald-500" />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Email Address</label>
              <input type="email" value={student.email} onChange={e => setStudent({...student, email: e.target.value})} required className="w-full p-3 bg-slate-900 border border-slate-700 rounded-xl text-sm outline-none focus:border-emerald-500" />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Full Name</label>
              <input type="text" value={student.username} onChange={e => setStudent({...student, username: e.target.value})} required className="w-full p-3 bg-slate-900 border border-slate-700 rounded-xl text-sm outline-none focus:border-emerald-500" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">USN</label>
                <input type="text" value={student.usn} onChange={e => setStudent({...student, usn: e.target.value})} required className="w-full p-3 bg-slate-900 border border-slate-700 rounded-xl text-sm outline-none focus:border-emerald-500" />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Semester</label>
                <input type="number" min="1" max="8" value={student.semester} onChange={e => setStudent({...student, semester: e.target.value})} required className="w-full p-3 bg-slate-900 border border-slate-700 rounded-xl text-sm outline-none focus:border-emerald-500" />
              </div>
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">College Name</label>
              <input type="text" value={student.college} onChange={e => setStudent({...student, college: e.target.value})} required className="w-full p-3 bg-slate-900 border border-slate-700 rounded-xl text-sm outline-none focus:border-emerald-500" />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Phone Number</label>
              <input type="tel" maxLength="10" value={student.phone} onChange={e => setStudent({...student, phone: e.target.value})} required className="w-full p-3 bg-slate-900 border border-slate-700 rounded-xl text-sm outline-none focus:border-emerald-500" />
            </div>
            <button type="submit" className="w-full bg-emerald-600 text-white p-3.5 rounded-xl font-bold hover:bg-emerald-500 cursor-pointer mt-2">
              Join Assessment
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center p-6">
        <div className="bg-slate-800 border border-slate-700 p-8 rounded-2xl shadow-2xl max-w-md w-full text-center space-y-4">
          <div className="w-16 h-16 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto text-2xl font-bold">✓</div>
          <h2 className="text-2xl font-bold text-white">Successfully Submitted!</h2>
        </div>
      </div>
    );
  }

  if (!quizStarted) {
    return (
      <div className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center p-6">
        <div className="bg-slate-800 border border-slate-700 p-8 rounded-2xl shadow-2xl max-w-md w-full text-center space-y-4">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-500 mx-auto"></div>
          <h3 className="text-lg font-bold text-white">Waiting for host to start...</h3>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 py-10 px-4 flex justify-center">
      <div className="max-w-2xl w-full space-y-6">
        <div className="bg-slate-800 border border-slate-700 p-6 rounded-2xl flex justify-between items-center shadow-lg">
          <h1 className="text-lg font-black text-emerald-400">MTD MARATHON - Answer Sheet</h1>
          <span className="bg-emerald-500/10 text-emerald-400 font-bold text-xs px-3 py-1.5 rounded-full">Live Session</span>
        </div>

        <form onSubmit={handleManualSubmit} className="space-y-4">
          {questions.map((q, qIndex) => {
            const isRadio = q.type === 'radio';
            return (
              <div key={qIndex} className="bg-slate-800 border border-slate-700 p-6 rounded-2xl shadow-md space-y-4">
                <div className="border-b border-slate-700 pb-3">
                  <span className="text-sm font-bold text-emerald-400">Question {qIndex + 1}</span>
                  <div className="text-xs text-slate-400 mt-1">
                    {isRadio ? "🔘 Select a correct answer" : "☑️ Select all correct answers"}
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  {q.options.map((opt, oIndex) => {
                    const isChecked = isRadio 
                      ? answersMap[qIndex] === opt 
                      : (answersMap[qIndex] || []).includes(opt);

                    return (
                      <label 
                        key={oIndex} 
                        className={`flex items-center p-3.5 rounded-xl border cursor-pointer transition-all ${
                          isChecked 
                            ? 'bg-emerald-950/40 border-emerald-500 text-emerald-200' 
                            : 'bg-slate-900/60 border-slate-700 text-slate-300'
                        }`}
                      >
                        <input 
                          type={q.type} 
                          name={`question-${qIndex}`}
                          value={opt}
                          checked={isChecked}
                          onChange={() => handleAnswerChange(qIndex, opt, q.type)}
                          className="mr-3 h-4 w-4 accent-emerald-500"
                        />
                        <span className="text-sm font-medium">{opt}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            );
          })}

          <button 
            type="submit" 
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white p-4 rounded-xl font-bold text-base shadow-xl cursor-pointer"
          >
            Submit Final Answer Sheet
          </button>
        </form>
      </div>
    </div>
  );
}
