import React, { useState, useEffect, useRef } from 'react';

const BACKEND_WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:5000';
const BACKEND_HTTP_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000';

export default function HostApp() {
  const [quizId, setQuizId] = useState(''); // Removed default value
  const [started, setStarted] = useState(false);
  
  const [timer, setTimer] = useState(0);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);

  const [currentQuestionText, setCurrentQuestionText] = useState('');
  const [isCompletedState, setIsCompletedState] = useState(false);
  const [showResultsButton, setShowResultsButton] = useState(false);
  
  const [results, setResults] = useState(null);
  const [evaluating, setEvaluating] = useState(false);
  const wsRef = useRef(null);

  const handleEnterQuiz = (e) => {
    e.preventDefault();
    if (!quizId.trim()) {
      alert("Please enter a valid Quiz ID");
      return;
    }

    const wsUrl = `${BACKEND_WS_URL}/ws/${quizId.trim()}`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      websocket.send(JSON.stringify({ type: 'join_quiz', studentData: { usn: 'HOST_ADMIN' } }));
      setStarted(true);
    };

    websocket.onerror = () => {
      alert("Failed to connect to backend WebSocket server. Make sure server.py is running!");
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'host_question_sync') {
          setCurrentQuestionText(data.question_text);
          setTimer(data.timer_seconds);
          setCurrentIndex(data.index);
          setTotalQuestions(data.total);
          setIsCompletedState(false);
        } else if (data.type === 'host_quiz_completed_display') {
          setCurrentQuestionText('');
          setIsCompletedState(true);
        } else if (data.type === 'enable_results_button') {
          setShowResultsButton(true);
        }
      } catch (err) {
        console.error("Error parsing incoming WS message:", err);
      }
    };

    wsRef.current = websocket;
  };

  useEffect(() => {
    let interval = null;
    if (timer > 0) {
      interval = setInterval(() => setTimer(prev => prev - 1), 1000);
    }
    return () => clearInterval(interval);
  }, [timer]);

  const startQuizSequence = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'start_quiz_sequence', quizId: quizId.trim() }));
    }
  };

  const fetchResults = async () => {
    setEvaluating(true);
    try {
      const res = await fetch(`${BACKEND_HTTP_URL}/api/evaluate-quiz`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quizId: quizId.trim() })
      });
      const data = await res.json();
      if (data.success) {
        setResults(data.results);
      } else {
        alert(data.error || "Failed to fetch results");
      }
    } catch (err) {
      console.error(err);
      alert("Server connection error while fetching results.");
    } finally {
      setEvaluating(false);
    }
  };

  const exportToCSV = () => {
    if (!results || results.length === 0) {
      alert("No results available to export!");
      return;
    }

    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "USN,Username,Email,College,Semester,Phone,Score,Total,Percentage\n";

    results.forEach(res => {
      const row = [
        `"${res.student.usn || ''}"`,
        `"${res.student.username || ''}"`,
        `"${res.student.email || ''}"`,
        `"${res.student.college || ''}"`,
        `"${res.student.semester || ''}"`,
        `"${res.student.phone || ''}"`,
        res.score,
        res.total,
        `${res.percentage}%`
      ];
      csvContent += row.join(",") + "\n";
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Quiz_Results_${quizId.trim()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!started) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center p-6">
        <div className="bg-gray-800 p-8 rounded-2xl shadow-xl max-w-md w-full border border-gray-700">
          <div className="text-center mb-6">
            <h1 className="text-3xl font-extrabold text-indigo-400">MTD MARATHON</h1>
            <p className="text-sm text-gray-400 mt-1">Host Control Portal</p>
          </div>
          <form onSubmit={handleEnterQuiz} className="space-y-4">
            <input 
              type="text" 
              placeholder="Enter Quiz ID" 
              value={quizId} 
              onChange={e => setQuizId(e.target.value)} 
              required
              className="w-full p-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-indigo-500 outline-none" 
            />
            <button type="submit" className="w-full bg-indigo-600 text-white p-3 rounded-lg font-bold hover:bg-indigo-500 transition cursor-pointer">
              Connect to Quiz Room
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      <nav className="bg-gray-800 border-b border-gray-700 px-8 py-4 flex justify-between items-center shadow-lg">
        <div className="bg-indigo-950 border border-indigo-500/50 px-4 py-2 rounded-full">
          <span className="text-indigo-300 font-bold">Question: </span>
          <span className="text-white font-mono font-bold">{totalQuestions > 0 ? `${currentIndex + 1} / ${totalQuestions}` : '0 / 0'}</span>
        </div>
        <div className="text-center">
          <h1 className="text-2xl font-black tracking-widest text-indigo-400">MTD MARATHON</h1>
        </div>
        <div className="flex items-center space-x-2 bg-red-900/40 border border-red-500/50 px-4 py-2 rounded-full">
          <span className="text-red-400 font-bold">⏱️ Timer:</span>
          <span className="text-red-200 font-mono font-bold text-lg">{timer}s</span>
        </div>
      </nav>

      <main className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-4xl w-full text-center space-y-8">
          {!currentQuestionText && !isCompletedState && (
            <div className="space-y-4">
              <h2 className="text-3xl font-bold text-gray-200">Room Ready: {quizId}</h2>
              <button 
                type="button"
                onClick={startQuizSequence}
                className="bg-indigo-600 text-white px-10 py-4 rounded-xl text-xl font-bold hover:bg-indigo-500 shadow-xl transition transform hover:scale-105 cursor-pointer"
              >
                Start Quiz Now
              </button>
            </div>
          )}

          {currentQuestionText && (
            <div className="bg-gray-800/80 backdrop-blur border border-gray-700 p-12 rounded-3xl shadow-2xl">
              <span className="text-indigo-400 font-bold tracking-wider uppercase text-sm">Active Question</span>
              <h2 className="text-4xl font-extrabold mt-4 mb-6 text-white leading-relaxed">
                {currentQuestionText}
              </h2>
            </div>
          )}

          {isCompletedState && !showResultsButton && (
            <div className="bg-emerald-950/40 border border-emerald-500/50 p-10 rounded-3xl shadow-xl animate-pulse">
              <h2 className="text-4xl font-bold text-emerald-400 mb-2">Quiz Completed!</h2>
              <p className="text-gray-300 text-lg">Finalizing submissions...</p>
            </div>
          )}

          {showResultsButton && (
            <div className="space-y-6">
              <div className="bg-emerald-950/60 border border-emerald-500 p-6 rounded-2xl">
                <h2 className="text-2xl font-bold text-emerald-400 mb-2">Quiz Session Concluded</h2>
                <button 
                  type="button"
                  onClick={fetchResults}
                  disabled={evaluating}
                  className="mt-4 bg-emerald-600 text-white px-8 py-4 rounded-xl text-lg font-bold hover:bg-emerald-500 shadow-lg transition cursor-pointer"
                >
                  {evaluating ? "Evaluating Scores..." : "Display Results"}
                </button>
              </div>
            </div>
          )}

          {results && (
            <div className="mt-8 bg-gray-800 border border-gray-700 rounded-2xl p-6 shadow-xl text-left">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-indigo-300">Final Student Scoreboard</h3>
                <button 
                  type="button"
                  onClick={exportToCSV}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-bold shadow transition cursor-pointer"
                >
                  📥 Download Excel (CSV)
                </button>
              </div>
              <div className="overflow-x-auto max-h-96 overflow-y-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="bg-gray-900 border-b border-gray-700 text-gray-400">
                      <th className="p-3">Name / USN</th>
                      <th className="p-3">College & Sem</th>
                      <th className="p-3">Contact Info</th>
                      <th className="p-3">Score</th>
                      <th className="p-3">Percentage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((res, i) => (
                      <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-900/40">
                        <td className="p-3">
                          <div className="font-bold text-white">{res.student.username}</div>
                          <div className="text-xs text-gray-400">{res.student.usn}</div>
                        </td>
                        <td className="p-3">
                          <div className="text-gray-200">{res.student.college}</div>
                          <div className="text-xs text-gray-400">Sem: {res.student.semester}</div>
                        </td>
                        <td className="p-3">
                          <div className="text-gray-300 text-xs">{res.student.email}</div>
                          <div className="text-gray-400 text-xs">{res.student.phone}</div>
                        </td>
                        <td className="p-3 font-semibold text-indigo-400">{res.score} / {res.total}</td>
                        <td className="p-3 font-bold text-emerald-400">{res.percentage}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}