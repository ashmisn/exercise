import React, { useState } from 'react';
import { Activity, ArrowRight, CheckCircle, Download, Monitor, TrendingUp, Clock, Calendar, User, Clock as ClockIcon, Shield, Target, Zap } from 'lucide-react';

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

const BACKEND_URL = 'https://exercise-7edj.onrender.com';

const AILMENTS = [
  { value: 'shoulder injury', label: 'Shoulder Injury', icon: '💪', gradient: 'from-blue-600 via-cyan-600 to-teal-600' },
  { value: 'elbow injury', label: 'Elbow Injury', icon: '🦾', gradient: 'from-teal-600 via-emerald-600 to-green-600' },
  { value: 'wrist injury', label: 'Wrist Injury', icon: '✋', gradient: 'from-cyan-600 via-sky-600 to-blue-600' },
  { value: 'leg/knee injury', label: 'Leg/Knee Injury', icon: '🦵', gradient: 'from-emerald-600 via-teal-600 to-cyan-600' },
];

const MOCK_PROGRESS = {
  totalReps: 1240,
  avgAccuracy: 92.5,
  sessionsThisWeek: 4,
  lastSession: 'Shoulder Flexion',
  lastSessionDate: 'October 4, 2025',
};

export const Home: React.FC<HomeProps> = ({ onStartSession }) => {
  const [selectedAilment, setSelectedAilment] = useState('');
  const [exercisePlan, setExercisePlan] = useState<ExercisePlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [userProfile, setUserProfile] = useState({
    name: 'Alex Rivera',
    age: 28,
    height: 172,
    weight: 68,
    existingAilments: 'None',
  });

  const [currentView, setCurrentView] = useState<'dashboard' | 'predictor' | 'profile'>('dashboard');

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
        headers: { 'Content-Type': 'application/json' },
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
    setError('');
    try {
      const response = await fetch(`${BACKEND_URL}/api/pdf/user123`, {
        method: 'GET',
      });

      if (!response.ok) {
        const text = await response.text();
        let errorMessage = `Failed to fetch PDF. Server status: ${response.status}`;
        try {
            const errorData = JSON.parse(text);
            errorMessage = errorData.detail || errorMessage;
        } catch { /* response was not JSON */ }
        throw new Error(errorMessage);
      }

      const blob = await response.blob();
      const pdfBlob = new Blob([blob], { type: 'application/pdf' });

      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `rehab_report.pdf`;
      if (contentDisposition && contentDisposition.indexOf('filename=') !== -1) {
          filename = contentDisposition.split('filename=')[1].replace(/"/g, '');
      }

      const url = window.URL.createObjectURL(pdfBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

    } catch (err: any) {
      console.error('Download failed', err);
      setError(`Could not download PDF report: ${err.message}.`);
    }
  };

  const handleProfileChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setUserProfile(prev => ({
        ...prev,
        [name]: (type === 'number' ? parseFloat(value) : value)
    }));
  };

  if (currentView === 'predictor') {
    return (
        <div className="min-h-screen bg-gradient-to-br from-sky-50 via-cyan-50 to-teal-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
                <button
                    onClick={() => setCurrentView('dashboard')}
                    className="mb-8 flex items-center text-cyan-700 hover:text-cyan-900 font-semibold transition-colors"
                    style={{ fontFamily: '"Inter", sans-serif' }}
                >
                    &larr; Back to Dashboard
                </button>
                <div className="bg-white rounded-2xl shadow-lg p-10 border border-cyan-100">
                    <h2 className="text-3xl font-bold text-gray-900 mb-4" style={{ fontFamily: '"Inter", sans-serif' }}>
                        Recovery Time Predictor
                    </h2>
                    <p className="text-gray-600" style={{ fontFamily: '"Inter", sans-serif' }}>
                      Predictor component goes here
                    </p>
                </div>
            </div>
        </div>
    );
  }

  if (currentView === 'profile') {
    const inputClasses = "w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-all duration-200 bg-white text-gray-900";
    const labelClasses = "block text-sm font-semibold text-gray-700 mb-2";

      return (
          <div className="min-h-screen bg-gradient-to-br from-sky-50 via-cyan-50 to-teal-50 py-12 px-4 sm:px-6 lg:px-8">
              <div className="max-w-2xl mx-auto bg-white rounded-2xl shadow-xl p-10 border border-cyan-100" style={{ fontFamily: '"Inter", sans-serif' }}>
                  <div className="flex items-center gap-4 mb-10">
                    <div className="bg-gradient-to-br from-cyan-600 to-teal-600 p-4 rounded-xl">
                      <User className="w-8 h-8 text-white" />
                    </div>
                    <h2 className="text-4xl font-bold text-gray-900" style={{ fontFamily: '"Inter", sans-serif' }}>
                      Patient Profile
                    </h2>
                  </div>

                  <div className="space-y-6">
                      <div>
                          <label htmlFor="name" className={labelClasses}>Full Name</label>
                          <input type="text" id="name" name="name" value={userProfile.name} onChange={handleProfileChange} className={inputClasses} required />
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div>
                              <label htmlFor="age" className={labelClasses}>Age (Years)</label>
                              <input type="number" id="age" name="age" value={userProfile.age} onChange={handleProfileChange} className={inputClasses} min="1" max="100" />
                          </div>
                          <div>
                              <label htmlFor="height" className={labelClasses}>Height (cm)</label>
                              <input type="number" id="height" name="height" value={userProfile.height} onChange={handleProfileChange} className={inputClasses} min="50" />
                          </div>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div>
                              <label htmlFor="weight" className={labelClasses}>Weight (kg)</label>
                              <input type="number" id="weight" name="weight" value={userProfile.weight} onChange={handleProfileChange} className={inputClasses} min="20" />
                          </div>
                          <div>
                              <label htmlFor="existingAilments" className={labelClasses}>Existing Conditions</label>
                              <input type="text" id="existingAilments" name="existingAilments" value={userProfile.existingAilments} onChange={handleProfileChange} className={inputClasses} placeholder="e.g., Asthma" />
                          </div>
                      </div>
                      <button
                          onClick={() => setCurrentView('dashboard')}
                          className="w-full bg-gradient-to-r from-cyan-600 to-teal-600 text-white py-4 rounded-xl font-semibold text-lg hover:from-cyan-700 hover:to-teal-700 transition-all duration-200 shadow-lg hover:shadow-xl"
                          style={{ fontFamily: '"Inter", sans-serif' }}
                      >
                          Save Changes
                      </button>
                  </div>
              </div>
          </div>
      );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-sky-50 to-cyan-50 relative" style={{ fontFamily: '"Inter", sans-serif' }}>
      <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-20">
        <div className="absolute top-20 left-10 w-96 h-96 bg-cyan-200 rounded-full mix-blend-multiply filter blur-3xl animate-blob"></div>
        <div className="absolute top-40 right-20 w-96 h-96 bg-teal-200 rounded-full mix-blend-multiply filter blur-3xl animate-blob animation-delay-2000"></div>
        <div className="absolute bottom-20 left-40 w-96 h-96 bg-blue-200 rounded-full mix-blend-multiply filter blur-3xl animate-blob animation-delay-4000"></div>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto p-4 md:p-8">
        <header className="flex items-center justify-between mb-12 bg-white rounded-2xl shadow-lg p-8 border-b-4 border-cyan-600">
          <div className="flex items-center gap-5">
            <div className="bg-gradient-to-br from-cyan-600 to-teal-600 p-4 rounded-xl shadow-lg">
              <Activity className="w-10 h-10 text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-gray-900" style={{ fontFamily: '"Inter", sans-serif' }}>
                AI Rehabilitation Dashboard
              </h1>
              <p className="text-sm text-gray-600 font-medium mt-1">Evidence-based recovery programs powered by AI</p>
            </div>
          </div>
          <div className="flex items-center gap-3 bg-gradient-to-r from-cyan-50 to-teal-50 px-5 py-3 rounded-xl cursor-pointer hover:shadow-md transition-all border border-cyan-200" onClick={() => setCurrentView('profile')}>
            <div className="bg-gradient-to-br from-cyan-600 to-teal-600 p-2 rounded-lg">
              <User className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-xs text-gray-500 font-medium">Patient</p>
              <p className="text-sm font-semibold text-gray-900">{userProfile.name}</p>
            </div>
          </div>
        </header>

        <div className="bg-white rounded-2xl shadow-md p-8 mb-8 border-l-4 border-teal-600">
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-3">
                  <Shield className="w-7 h-7 text-teal-600" />
                  <h3 className="text-2xl font-bold text-gray-900" style={{ fontFamily: '"Inter", sans-serif' }}>
                    Patient Information
                  </h3>
                </div>
                <button
                    onClick={() => setCurrentView('profile')}
                    className="text-sm text-cyan-700 hover:text-cyan-900 font-semibold bg-cyan-50 px-4 py-2 rounded-lg hover:bg-cyan-100 transition-all"
                >
                    Edit Profile
                </button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
                <div className="bg-gradient-to-br from-blue-50 to-cyan-50 p-5 rounded-xl border border-blue-100">
                    <span className="font-bold text-3xl text-blue-700 block">{userProfile.age}</span>
                    <span className="text-sm text-blue-600 font-medium">Age (years)</span>
                </div>
                <div className="bg-gradient-to-br from-cyan-50 to-teal-50 p-5 rounded-xl border border-cyan-100">
                    <span className="font-bold text-3xl text-cyan-700 block">{userProfile.height}</span>
                    <span className="text-sm text-cyan-600 font-medium">Height (cm)</span>
                </div>
                <div className="bg-gradient-to-br from-teal-50 to-emerald-50 p-5 rounded-xl border border-teal-100">
                    <span className="font-bold text-3xl text-teal-700 block">{userProfile.weight}</span>
                    <span className="text-sm text-teal-600 font-medium">Weight (kg)</span>
                </div>
                <div className="bg-gradient-to-br from-emerald-50 to-green-50 p-5 rounded-xl border border-emerald-100">
                    <span className="font-semibold text-lg text-emerald-700 block truncate">{userProfile.existingAilments || 'None'}</span>
                    <span className="text-sm text-emerald-600 font-medium">Conditions</span>
                </div>
            </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          <div className="xl:col-span-2 space-y-8">
            {error && (
              <div className="bg-red-50 border-l-4 border-red-500 text-red-800 px-6 py-4 rounded-lg shadow-sm font-medium">
                {error}
              </div>
            )}

            {!exercisePlan ? (
              <div className="bg-white rounded-2xl shadow-lg p-10 border border-gray-200">
                <div className="flex items-center gap-3 mb-3">
                  <Target className="w-8 h-8 text-cyan-600" />
                  <h2 className="text-3xl font-bold text-gray-900" style={{ fontFamily: '"Inter", sans-serif' }}>
                    Select Treatment Area
                  </h2>
                </div>
                <p className="text-gray-600 mb-10 font-medium text-base">
                  Choose the area requiring physical therapy to generate your personalized rehabilitation plan
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
                  {AILMENTS.map((ailment) => (
                    <button
                      key={ailment.value}
                      onClick={() => setSelectedAilment(ailment.value)}
                      className={`w-full p-7 rounded-xl border-2 transition-all duration-200 shadow-md hover:shadow-lg ${
                        selectedAilment === ailment.value
                          ? 'border-cyan-600 bg-gradient-to-br from-cyan-50 to-teal-50 ring-2 ring-cyan-300'
                          : 'border-gray-200 bg-white hover:border-cyan-400'
                      }`}
                    >
                      <div className="flex items-center">
                        <span className="text-5xl mr-5">{ailment.icon}</span>
                        <div className="text-left flex-1">
                          <h3 className={`text-xl font-bold mb-1 ${selectedAilment === ailment.value ? 'text-transparent bg-clip-text bg-gradient-to-r ' + ailment.gradient : 'text-gray-800'}`} style={{ fontFamily: '"Inter", sans-serif' }}>
                            {ailment.label}
                          </h3>
                          <p className="text-sm text-gray-600 font-medium">
                            Evidence-based therapy program
                          </p>
                        </div>
                        {selectedAilment === ailment.value && (
                          <CheckCircle className="w-7 h-7 text-cyan-600 ml-auto flex-shrink-0" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>

                <button
                  onClick={handleGetPlan}
                  disabled={loading || !selectedAilment}
                  className="w-full bg-gradient-to-r from-cyan-600 to-teal-600 text-white py-5 rounded-xl font-semibold text-lg shadow-lg hover:shadow-xl hover:from-cyan-700 hover:to-teal-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
                  style={{ fontFamily: '"Inter", sans-serif' }}
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
                      Generating Your Plan...
                    </>
                  ) : (
                    <>
                      Generate Rehabilitation Plan
                      <ArrowRight className="w-5 h-5" />
                    </>
                  )}
                </button>
              </div>
            ) : (
              <div className="bg-white rounded-2xl shadow-lg p-10 border border-gray-200">
                <div className="flex items-center gap-3 mb-4">
                  <Zap className="w-8 h-8 text-teal-600" />
                  <h2 className="text-3xl font-bold text-gray-900" style={{ fontFamily: '"Inter", sans-serif' }}>
                    Your Rehabilitation Plan
                  </h2>
                </div>
                <p className="text-gray-600 font-medium mb-6">Treatment for: <span className="font-semibold text-gray-900">{exercisePlan.ailment}</span></p>

                <div className="flex flex-wrap items-center gap-4 mb-8">
                  <span className="bg-gradient-to-r from-teal-600 to-emerald-600 text-white px-5 py-2 rounded-lg font-semibold shadow-md text-base">
                    {exercisePlan.difficulty_level.toUpperCase()}
                  </span>
                  <span className="font-semibold flex items-center gap-2 bg-blue-100 px-4 py-2 rounded-lg text-blue-800">
                    <Clock className="w-5 h-5" />
                    {exercisePlan.duration_weeks} Week Program
                  </span>
                  <button
                    onClick={handleDownloadPDF}
                    className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white px-5 py-2 rounded-lg hover:from-blue-700 hover:to-cyan-700 flex items-center gap-2 transition-all shadow-md hover:shadow-lg font-semibold"
                  >
                    <Download className="w-5 h-5" />
                    Download Report
                  </button>
                </div>

                <div className="space-y-5">
                  {exercisePlan.exercises.map((exercise, index) => (
                    <div
                      key={index}
                      className="border-2 border-gray-200 rounded-xl p-7 bg-gradient-to-br from-white to-gray-50 shadow-sm hover:shadow-md transition-all flex flex-col md:flex-row items-center justify-between hover:border-cyan-300"
                    >
                      <div className="mb-4 md:mb-0 md:mr-6 flex-1">
                        <h3 className="text-xl font-bold text-gray-900 mb-2" style={{ fontFamily: '"Inter", sans-serif' }}>
                          {index + 1}. {exercise.name}
                        </h3>
                        <p className="text-gray-600 mb-4 font-medium text-sm leading-relaxed">{exercise.description}</p>
                        <div className="flex flex-wrap gap-3 text-sm font-semibold">
                          <span className="bg-teal-100 text-teal-800 px-4 py-1.5 rounded-lg flex items-center gap-1.5">
                            <Activity className="w-4 h-4" />
                            {exercise.target_reps} reps
                          </span>
                          <span className="bg-emerald-100 text-emerald-800 px-4 py-1.5 rounded-lg">
                            {exercise.sets} sets
                          </span>
                          <span className="bg-cyan-100 text-cyan-800 px-4 py-1.5 rounded-lg">
                            {exercise.rest_seconds}s rest
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={() => onStartSession(exercisePlan, exercise)}
                        className="bg-gradient-to-r from-cyan-600 to-teal-600 text-white px-7 py-3.5 rounded-xl font-semibold hover:from-cyan-700 hover:to-teal-700 transition-all whitespace-nowrap shadow-md hover:shadow-lg flex items-center justify-center gap-2"
                        style={{ fontFamily: '"Inter", sans-serif' }}
                      >
                        Start Session
                        <Monitor className="w-5 h-5" />
                      </button>
                    </div>
                  ))}
                </div>

                <button
                  onClick={() => setExercisePlan(null)}
                  className="mt-8 w-full bg-gray-100 text-gray-700 py-3.5 rounded-xl font-semibold hover:bg-gray-200 transition-all shadow-sm border border-gray-300"
                >
                  Select Different Area
                </button>
              </div>
            )}
          </div>

          <div className="xl:col-span-1 space-y-6">
            <h2 className="text-2xl font-bold text-gray-900" style={{ fontFamily: '"Inter", sans-serif' }}>
              Progress Overview
            </h2>

            <button
                onClick={() => setCurrentView('predictor')}
                className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 text-white px-5 py-4 rounded-xl hover:from-blue-700 hover:to-cyan-700 flex items-center justify-center gap-3 transition-all shadow-md hover:shadow-lg font-semibold"
                style={{ fontFamily: '"Inter", sans-serif' }}
            >
                <ClockIcon className="w-5 h-5" />
                Estimate Recovery Time
            </button>

            <div className="bg-white rounded-xl shadow-md p-7 border-l-4 border-emerald-600">
                <p className="text-base font-bold text-gray-800 mb-4" style={{ fontFamily: '"Inter", sans-serif' }}>Most Recent Session</p>
                <div className="flex items-center gap-4">
                    <div className="bg-gradient-to-br from-emerald-500 to-teal-600 p-3.5 rounded-xl flex items-center justify-center shadow-md">
                        <CheckCircle className="w-7 h-7 text-white" />
                    </div>
                    <div>
                        <p className="text-lg font-semibold text-gray-900">{MOCK_PROGRESS.lastSession}</p>
                        <p className="text-sm text-gray-500 flex items-center gap-2 font-medium">
                            <Calendar className="w-4 h-4" /> {MOCK_PROGRESS.lastSessionDate}
                        </p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl shadow-md p-6 border border-blue-100">
                <p className="text-xs text-blue-700 font-semibold mb-2 uppercase tracking-wide">Total Reps</p>
                <p className="text-4xl font-bold text-blue-700">
                  {MOCK_PROGRESS.totalReps}
                </p>
              </div>

              <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl shadow-md p-6 border border-emerald-100">
                <p className="text-xs text-emerald-700 font-semibold mb-2 uppercase tracking-wide">Accuracy</p>
                <p className="text-4xl font-bold text-emerald-700 flex items-center">
                  {MOCK_PROGRESS.avgAccuracy}%
                </p>
              </div>

              <div className="bg-gradient-to-br from-cyan-50 to-teal-50 rounded-xl shadow-md p-6 col-span-2 border border-cyan-100">
                <p className="text-xs text-cyan-700 font-semibold mb-2 uppercase tracking-wide">This Week</p>
                <p className="text-4xl font-bold text-cyan-700">
                  {MOCK_PROGRESS.sessionsThisWeek} <span className="text-xl font-semibold">Sessions</span>
                </p>
              </div>
            </div>

            <button
                onClick={handleDownloadPDF}
                className="w-full bg-gray-900 text-white px-5 py-4 rounded-xl hover:bg-gray-800 flex items-center justify-center gap-3 transition-all shadow-md hover:shadow-lg font-semibold"
                style={{ fontFamily: '"Inter", sans-serif' }}
              >
                <Download className="w-5 h-5" />
                Download Full Report
              </button>
          </div>
        </div>
        <Chatbot/>
      </div>
    </div>
  );
};


