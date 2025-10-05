import React, { useState, useEffect } from 'react';
import { Activity, ArrowRight, CheckCircle, Download, Monitor, TrendingUp, Clock, Calendar, User } from 'lucide-react';
// FIX: Adjusted paths to assume components and contexts are siblings to pages/Home.tsx, 
// or in a directory structure relative to the project root.
import { useAuth } from '../contexts/AuthContext'; 
import { Chatbot } from '../components/Chatbot'; 

// --- Interface Definitions ---
interface Exercise {
  name: string;
  description: string;
  target_reps: number;
  sets: number;
  rest_seconds: number;
}

interface ExercisePlan {
  ailment: string;
  exercises: Exercise[];
  difficulty_level: string;
  duration_weeks: number;
}

interface HomeProps {
  onStartSession: (plan: ExercisePlan, exercise: Exercise) => void;
}

// --- Configuration ---
const BACKEND_URL = 'https://exercise-7edj.onrender.com';

const AILMENTS = [
  { value: 'shoulder injury', label: 'Shoulder Injury', icon: '💪' },
  { value: 'elbow injury', label: 'Elbow Injury', icon: '🦾' },
  { value: 'wrist injury', label: 'Wrist Injury', icon: '✋' },
  { value: 'leg/knee injury', label: 'Leg/Knee Injury', icon: '🦵' },
];

// Mock data for the Dashboard (This would normally come from the /api/progress endpoint)
const MOCK_PROGRESS = {
  totalReps: 1240,
  avgAccuracy: 92.5,
  sessionsThisWeek: 4,
  lastSession: 'Shoulder Flexion',
  lastSessionDate: 'October 4, 2025',
};

// =========================================================================
// Dashboard Component (Main Layout)
// =========================================================================

export const Home: React.FC<HomeProps> = ({ onStartSession }) => {
  const { user } = useAuth();
  const [selectedAilment, setSelectedAilment] = useState('');
  const [exercisePlan, setExercisePlan] = useState<ExercisePlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // --- API Handlers ---
  const handleGetPlan = async () => {
    if (!selectedAilment) {
      setError('Please select an ailment');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${BACKEND_URL}/api/get_plan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ailment: selectedAilment }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'Failed to fetch exercise plan');
      }

      const data = await response.json();
      setExercisePlan(data);
    } catch (err: any) {
      setError(`Failed to load plan: ${err.message}. Make sure the backend is running.`);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    if (!user?.id) {
      console.warn('User ID missing for PDF download.');
      return;
    }

    try {
      const response = await fetch(`${BACKEND_URL}/api/pdf/${user.id}`, {
        method: 'GET',
      });

      if (!response.ok) throw new Error('Failed to fetch PDF');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `rehab_report_${user.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed', err);
      setError('Could not download PDF. Try again later.');
    }
  };

  // --- Render ---
  return (
    // 1. Aesthetic Background: Soft gradients and rounded corners
    <div className="min-h-screen bg-gray-50 font-sans p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header Section */}
        <header className="flex items-center justify-between mb-12 bg-white p-6 rounded-3xl shadow-lg border-b-4 border-blue-100">
          <div className="flex items-center">
            <div className="bg-gradient-to-br from-blue-600 to-indigo-700 p-3 rounded-xl shadow-xl">
              <Activity className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-3xl font-extrabold text-gray-900 ml-4 tracking-tight">
              AI Rehab Dashboard
            </h1>
          </div>
          <div className="flex items-center text-gray-700 font-medium">
            <User className="w-5 h-5 mr-2 text-indigo-500" />
            <span>{user?.email || 'Guest User'}</span>
          </div>
        </header>

        {/* 2. Main Dashboard Grid */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          
          {/* COLUMN 1/3: Plan Selection & Display (Main Focus) */}
          <div className="xl:col-span-2 space-y-8">
            
            {/* Error Message Display */}
            {error && (
              <div className="bg-red-50 border border-red-300 text-red-700 px-6 py-4 rounded-xl shadow-md text-sm">
                {error}
              </div>
            )}

            {/* A. Plan Selection View */}
            {!exercisePlan ? (
              <div className="bg-white rounded-3xl shadow-2xl p-8 border-t-8 border-blue-500">
                <h2 className="text-3xl font-bold text-gray-900 mb-2">
                  1. Choose Your Focus Area
                </h2>
                <p className="text-gray-600 mb-8">
                  Select the area requiring therapy to generate your personalized program.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                  {AILMENTS.map((ailment) => (
                    <button
                      key={ailment.value}
                      onClick={() => setSelectedAilment(ailment.value)}
                      className={`w-full p-6 rounded-2xl border-2 transition-all text-left shadow-lg transform hover:scale-[1.02] hover:shadow-xl duration-300 ${
                        selectedAilment === ailment.value
                          ? 'border-indigo-600 bg-indigo-50 ring-4 ring-indigo-200'
                          : 'border-gray-200 bg-white hover:border-blue-400'
                      }`}
                    >
                      <div className="flex items-center">
                        <span className="text-4xl mr-4">{ailment.icon}</span>
                        <div>
                          <h3 className="text-xl font-extrabold text-gray-900">
                            {ailment.label}
                          </h3>
                          <p className="text-sm text-gray-500">
                            Specialized {ailment.label.toLowerCase()} recovery.
                          </p>
                        </div>
                        {selectedAilment === ailment.value && (
                          <CheckCircle className="w-6 h-6 text-indigo-600 ml-auto flex-shrink-0" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>

                <button
                  onClick={handleGetPlan}
                  disabled={loading || !selectedAilment}
                  className="w-full bg-gradient-to-r from-teal-500 to-green-600 text-white py-4 rounded-xl font-bold text-lg tracking-wider shadow-xl shadow-teal-500/30 hover:shadow-green-500/50 hover:from-teal-600 hover:to-green-700 focus:ring-4 focus:ring-teal-200 transition-all duration-300 transform hover:-translate-y-1 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {loading ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Generating Plan...
                    </>
                  ) : (
                    <>
                      Get My Custom Plan
                      <ArrowRight className="w-5 h-5 ml-2" />
                    </>
                  )}
                </button>
              </div>
            ) : (
              // B. Plan Display View
              <div className="bg-white rounded-3xl shadow-2xl p-8 border-t-8 border-teal-500">
                <h2 className="text-3xl font-extrabold text-gray-900 mb-3">
                  Your Custom Plan: {exercisePlan.ailment}
                </h2>
                
                {/* Plan Metadata */}
                <div className="flex flex-wrap items-center gap-6 text-sm text-gray-600 mb-6 border-b pb-4">
                  <span className="bg-indigo-100 text-indigo-800 px-3 py-1 rounded-full font-bold shadow-sm">
                    {exercisePlan.difficulty_level.toUpperCase()}
                  </span>
                  <span className="font-medium flex items-center gap-1">
                    <Clock className="w-4 h-4 text-gray-400" />
                    {exercisePlan.duration_weeks} Weeks
                  </span>
                  <button
                    onClick={handleDownloadPDF}
                    className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-5 py-2 rounded-xl hover:from-blue-700 hover:to-indigo-700 flex items-center gap-2 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
                  >
                    <Download className="w-5 h-5" />
                    Download PDF
                  </button>
                </div>

                {/* Exercise List */}
                <div className="grid gap-6">
                  {exercisePlan.exercises.map((exercise, index) => (
                    <div
                      key={index}
                      className="border-2 border-gray-100 rounded-xl p-6 transition-all bg-gray-50/50 shadow-md flex flex-col md:flex-row items-center justify-between hover:border-blue-500"
                    >
                      <div className="mb-4 md:mb-0 md:mr-6 flex-1">
                        <h3 className="text-xl font-bold text-gray-900 mb-1">
                          {index + 1}. {exercise.name}
                        </h3>
                        <p className="text-gray-600 mb-3 text-sm">{exercise.description}</p>
                        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-700 font-medium">
                          <span className="text-blue-600 flex items-center gap-1">
                            <Activity className="w-4 h-4" />
                            Target: {exercise.target_reps} reps
                          </span>
                          <span>|</span>
                          <span>Sets: {exercise.sets}</span>
                          <span>|</span>
                          <span>Rest: {exercise.rest_seconds}s</span>
                        </div>
                      </div>
                      <button
                        onClick={() => onStartSession(exercisePlan, exercise)}
                        className="bg-gradient-to-r from-green-500 to-teal-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-green-600 hover:to-teal-700 transition-all whitespace-nowrap shadow-lg flex items-center justify-center transform hover:scale-[1.05]"
                      >
                        Start Session
                        <Monitor className="w-5 h-5 ml-2" />
                      </button>
                    </div>
                  ))}
                </div>

                {/* Reset Button */}
                <button
                  onClick={() => setExercisePlan(null)}
                  className="mt-8 w-full bg-gray-100 text-gray-700 py-3 rounded-xl font-medium hover:bg-gray-200 transition-all shadow-md border"
                >
                  Choose Different Ailment
                </button>
              </div>
            )}
          </div>

          {/* COLUMN 2/3: Progress Dashboard (Fixed/Stats View) */}
          <div className="xl:col-span-1 space-y-8">
            <h2 className="text-2xl font-bold text-gray-800 tracking-tight">
              My Progress Summary
            </h2>
            
            <div className="bg-white rounded-3xl shadow-xl p-6 border-l-4 border-teal-500">
                <p className="text-lg font-medium text-gray-800 mb-4">Latest Achievement</p>
                <div className="flex items-center gap-4">
                    <div className="bg-teal-500 p-3 rounded-full flex items-center justify-center shadow-lg">
                        <CheckCircle className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <p className="text-lg font-bold text-gray-900">{MOCK_PROGRESS.lastSession}</p>
                        <p className="text-sm text-gray-500 flex items-center gap-1">
                            <Calendar className="w-3 h-3" /> {MOCK_PROGRESS.lastSessionDate}
                        </p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Card 1: Total Reps */}
              <div className="bg-white rounded-xl shadow-lg p-5 border-l-4 border-blue-500">
                <p className="text-sm text-gray-500 font-medium">Total Reps</p>
                <p className="text-3xl font-extrabold text-blue-600 mt-1">
                  {MOCK_PROGRESS.totalReps}
                </p>
              </div>

              {/* Card 2: Average Accuracy */}
              <div className="bg-white rounded-xl shadow-lg p-5 border-l-4 border-green-500">
                <p className="text-sm text-gray-500 font-medium">Avg. Accuracy</p>
                <p className="text-3xl font-extrabold text-green-600 mt-1 flex items-center">
                  {MOCK_PROGRESS.avgAccuracy}%
                  <TrendingUp className="w-5 h-5 ml-2 text-green-400" />
                </p>
              </div>
              
              {/* Card 3: Sessions This Week */}
              <div className="bg-white rounded-xl shadow-lg p-5 col-span-2 border-l-4 border-indigo-500">
                <p className="text-sm text-gray-500 font-medium">Sessions This Week</p>
                <p className="text-3xl font-extrabold text-indigo-600 mt-1">
                  {MOCK_PROGRESS.sessionsThisWeek}
                </p>
              </div>
            </div>
            
            {/* Call to Action for Report */}
             <button
                onClick={handleDownloadPDF}
                className="w-full bg-gray-800 text-white px-5 py-3 rounded-xl hover:bg-gray-700 flex items-center justify-center gap-2 transition-all shadow-xl transform hover:scale-[1.01]"
              >
                <Download className="w-5 h-5" />
                View Full Progress Report
              </button>
          </div>
          
        </div>
      </div>
      
      {/* Floating Chatbot */}
      <Chatbot />
    </div>
  );
};
