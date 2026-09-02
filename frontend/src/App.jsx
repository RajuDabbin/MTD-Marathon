import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import HostApp from './HostApp';
import StudentApp from './StudentApp';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/student" replace />} />
        <Route path="/host" element={<HostApp />} />
        <Route path="/student" element={<StudentApp />} />
      </Routes>
    </Router>
  );
}