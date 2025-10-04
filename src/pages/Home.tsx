import React, { useState } from 'react';
import { Activity, ArrowRight, CheckCircle, Download } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { Chatbot } from '../components/Chatbot';

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
  { value: 'shoulder injury', label: 'Shoulder Injury', icon: '💪' },
  { value: 'elbow injury', label: 'Elbow Injury', icon: '🦾' },
  { value: 'wrist injury', label: 'Wrist Injury', icon: '✋' },
  { value: 'leg/knee injury', label: 'Leg/Knee Injury', icon: '🦵' },
];

export const Home: React.FC<HomeProps> = ({ onStartSession }) => {
  const { user } = useAuth();
  const [selectedAilment, setSelectedAilment] = useState('');
  const [exercisePlan, setExercisePlan] = useState<ExercisePlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-center mb-12">
          <div className="bg-blue-600 p-4 rounded-2xl">
            <Activity className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 ml-4">
            AI Physiotherapy
          </h1>
        </div>

        {!exercisePlan ? (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-2xl shadow-xl p-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Get Your Personalized Exercise Plan
              </h2>
              <p className="text-gray-600 mb-8">
                Select your ailment to receive a customized rehabilitation program with AI-powered guidance
              </p>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-6">
                  {error}
                </div>
              )}

              <div className="space-y-4 mb-8">
                {AILMENTS.map((ailment) => (
                  <button
                    key={ailment.value}
                    onClick={() => setSelectedAilment(ailment.value)}
                    className={`w-full p-6 rounded-xl border-2 transition-all text-left ${
                      selectedAilment === ailment.value
                        ? 'border-blue-600 bg-blue-50'
                        : 'border-gray-200 hover:border-blue-300 bg-white'
                    }`}
                  >
                    <div className="flex items-center">
                      <span className="text-4xl mr-4">{ailment.icon}</span>
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          {ailment.label}
                        </h3>
                        <p className="text-sm text-gray-600">
                          Specialized exercises for {ailment.label.toLowerCase()} recovery
                        </p>
                      </div>
                      {selectedAilment === ailment.value && (
                        <CheckCircle className="w-6 h-6 text-blue-600 ml-auto" />
                      )}
                    </div>
                  </button>
                ))}
              </div>

              <button
                onClick={handleGetPlan}
                disabled={loading || !selectedAilment}
                className="w-full bg-blue-600 text-white py-4 rounded-xl font-semibold hover:bg-blue-700 focus:ring-4 focus:ring-blue-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center shadow-lg"
              >
                {loading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Loading...
                  </>
                ) : (
                  <>
                    Get My Exercise Plan
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-2xl shadow-xl p-8 mb-6">
              <h2 className="text-3xl font-bold text-gray-900 mb-2">
                Your Exercise Plan
              </h2>
              <div className="flex items-center gap-4 text-sm text-gray-600 mb-6">
                <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full font-medium">
                  {exercisePlan.difficulty_level.charAt(0).toUpperCase() + exercisePlan.difficulty_level.slice(1)}
                </span>
                <span className="font-medium">
                  <span className="text-gray-400">Ailment: </span>
                  {exercisePlan.ailment}
                </span>
                <span>•</span>
                <span>{exercisePlan.duration_weeks} weeks program</span>
              </div>

              <div className="mb-6">
                <button
                  onClick={handleDownloadPDF}
                  className="bg-gradient-to-r from-green-600 to-emerald-600 text-white px-6 py-3 rounded-xl hover:from-green-700 hover:to-emerald-700 flex items-center gap-2 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
                >
                  <Download className="w-5 h-5" />
                  Download Report PDF
                </button>
              </div>

              <div className="grid gap-6">
                {exercisePlan.exercises.map((exercise, index) => (
                  <div
                    key={index}
                    className="border-2 border-gray-200 rounded-xl p-6 hover:border-blue-400 transition-all bg-gray-50/50"
                  >
                    <div className="flex flex-col md:flex-row items-start justify-between">
                      <div className="mb-4 md:mb-0">
                        <h3 className="text-xl font-bold text-gray-900 mb-2">
                          {exercise.name}
                        </h3>
                        <p className="text-gray-600 mb-4">{exercise.description}</p>
                        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-gray-700">
                          <span className="font-semibold text-blue-600">
                            Target: {exercise.target_reps} reps
                          </span>
                          <span>•</span>
                          <span>{exercise.sets} sets</span>
                          <span>•</span>
                          <span>{exercise.rest_seconds}s rest</span>
                        </div>
                      </div>
                      <button
                        onClick={() => onStartSession(exercisePlan, exercise)}
                        className="bg-green-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-green-700 transition-all whitespace-nowrap shadow-lg flex items-center justify-center"
                      >
                        Start Exercise
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <button
                onClick={() => setExercisePlan(null)}
                className="mt-8 w-full bg-gray-100 text-gray-700 py-3 rounded-xl font-medium hover:bg-gray-200 transition-all shadow-md"
              >
                Choose Different Ailment
              </button>
            </div>
          </div>
        )}
      </div>
      <Chatbot />
    </div>
  );
};
