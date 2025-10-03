import React, { useEffect, useState } from 'react';
import { TrendingUp, Calendar, Target, Award, Activity, AlertCircle, Download } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext'; // Original, correct import

// --- DUMMY INTERFACES (Required for Component to run in isolation) ---
interface ProgressData {
    user_id: string;
    total_sessions: number;
    total_reps: number;
    average_accuracy: number;
    streak_days: number;
    weekly_data: Array<{
        day: string;
        reps: number;
        accuracy: number;
    }>;
    recent_sessions: Array<{
        date: string;
        exercise: string;
        reps: number;
        accuracy: number;
    }>;
}

// Global window extensions for jsPDF and html2canvas (will be loaded by script tags)
declare global {
    interface Window {
        html2canvas: any;
        jsPDF: any;
    }
}
// -------------------------------------------------------------------

// --- NEW GLOBAL SCRIPT LOADER FUNCTION ---
// NOTE: We still load the scripts asynchronously, but the main component won't wait for this Promise.
const scriptPromise = new Promise<void>((resolve, reject) => {
    let loadedCount = 0;
    const requiredScripts = 2;

    const scriptLoaded = () => {
        loadedCount++;
        if (loadedCount === requiredScripts) {
            resolve();
        }
    };
    
    // jsPDF
    const jsPDFScript = document.createElement('script');
    jsPDFScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
    jsPDFScript.onload = scriptLoaded;
    jsPDFScript.onerror = () => reject(new Error('Failed to load jsPDF'));
    document.head.appendChild(jsPDFScript);

    // html2canvas
    const html2canvasScript = document.createElement('script');
    html2canvasScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
    html2canvasScript.onload = scriptLoaded;
    html2canvasScript.onerror = () => reject(new Error('Failed to load html2canvas'));
    document.head.appendChild(html2canvasScript);
});


export const Progress: React.FC = () => {
    const { user } = useAuth(); 
    const reportRef = React.useRef(null); // Ref for the element to capture
    
    const [progressData, setProgressData] = useState<ProgressData | null>(null);
    const [loading, setLoading] = useState(true);
    const [fetchError, setFetchError] = useState<string | null>(null);
    const [isGenerating, setIsGenerating] = useState(false); // Track generation status
    // CRITICAL FIX: Set to TRUE by default, as the click handles the failure immediately
    const [isScriptLoaded, setIsScriptLoaded] = useState(true); 

    const userId = user?.id || 'default_test_user'; 

    useEffect(() => {
        // Only fetch progress data in useEffect. PDF script promise runs in parallel.
        fetchProgress();
        
        // Use the promise only to log success/failure, not to block the UI.
        scriptPromise.then(() => {
            console.log("PDF generation scripts successfully loaded.");
        }).catch(err => {
            console.warn("PDF script loading failed, relying on fallback.", err);
        });

    }, [userId]); 

    const fetchProgress = async () => {
        setLoading(true);
        setFetchError(null);
        
        try {
            const response = await fetch(`http://localhost:8000/api/progress/${userId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            setProgressData(data);
        } catch (err) {
            console.error('Failed to fetch progress:', err);
            setFetchError('Failed to load progress data. Check API connection.');
            setProgressData(null); 
        } finally {
            setLoading(false);
        }
    };

    // --- PDF DOWNLOAD LOGIC ---
    const downloadReport = async () => {
        if (isGenerating) return;
        setIsGenerating(true);
        
        const input = reportRef.current;
        if (!input) {
            setIsGenerating(false);
            return;
        }

        // CRITICAL CHECK: Check if dynamic libraries are available.
        if (!window.html2canvas || !window.jsPDF) {
             console.log('PDF libraries not initialized. Falling back to browser print.');
             window.print();
             setIsGenerating(false);
             return;
        }

        try {
            // 1. Capture the entire report div as an image
            const canvas = await window.html2canvas(input, {
                scale: 2, 
                logging: false,
                useCORS: true,
                scrollX: 0,
                scrollY: -window.scrollY 
            });

            const imgData = canvas.toDataURL('image/jpeg', 1.0);
            
            // 2. Initialize jsPDF
            const pdf = new window.jsPDF.jsPDF('p', 'mm', 'a4');
            const pdfWidth = pdf.internal.pageSize.getWidth();
            const pdfHeight = pdf.internal.pageSize.getHeight();
            const imgHeight = (canvas.height * pdfWidth) / canvas.width;
            
            let position = 0;

            if (imgHeight < pdfHeight) {
                 pdf.addImage(imgData, 'JPEG', 0, position, pdfWidth, imgHeight);
            } else {
                // 3. Multi-page PDF logic
                let heightLeft = imgHeight;
                while (heightLeft >= 0) {
                    position = heightLeft - imgHeight;
                    pdf.addImage(imgData, 'JPEG', 0, position, pdfWidth, imgHeight);
                    heightLeft -= pdfHeight;
                    if (heightLeft > -1) {
                        pdf.addPage();
                    }
                }
            }
            
            pdf.save(`rehab_report_${progressData?.user_id || 'guest'}_${new Date().toLocaleDateString()}.pdf`);

        } catch (error) {
            console.error("Error during high-quality PDF generation:", error);
            // FINAL FALLBACK: If something crashes during generation (e.g., memory), use print.
             window.print(); 
        } finally {
            setIsGenerating(false);
        }
    };
    // -------------------------------

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
                <div className="text-lg text-gray-600 animate-pulse">Loading progress...</div>
            </div>
        );
    }

    if (fetchError || !progressData) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
                <div className="text-lg text-gray-600 p-8 bg-white rounded-xl shadow-lg text-center">
                    <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-3" />
                    <p>{fetchError || "No progress data available"}</p>
                    <p className="text-sm text-gray-400 mt-2">Try completing a session first!</p>
                    <button 
                        onClick={fetchProgress} 
                        className="mt-4 bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition"
                    >
                        Retry Load
                    </button>
                </div>
            </div>
        );
    }

    const currentMaxReps = Math.max(...progressData.weekly_data.map((d) => d.reps));
    const maxReps = currentMaxReps > 0 ? currentMaxReps : 1;
    
    // Function to determine weekly bar color based on accuracy
    const getBarColorClass = (accuracy: number) => {
        if (accuracy > 90) return 'bg-gradient-to-r from-green-500 to-emerald-600';
        if (accuracy > 75) return 'bg-gradient-to-r from-yellow-500 to-orange-500';
        return 'bg-gradient-to-r from-red-500 to-pink-500';
    };

    // Creative Encouragement Logic
    const avgAccuracy = progressData.average_accuracy;
    let encouragementMessage = "You're consistently moving toward recovery! Keep up the control.";
    if (progressData.streak_days > 5) {
        encouragementMessage = "Your streak is incredible! Consistency is the key to healing.";
    } else if (avgAccuracy < 70 && progressData.total_sessions > 3) {
        encouragementMessage = "Focus on control and precision this week to boost your form score!";
    }


    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 py-8">
            <div className="max-w-7xl mx-auto px-4">
                 {/* NEW HEADER FOR DOWNLOAD BUTTON */}
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-4xl font-bold text-gray-900 mb-2">Your Progress</h1>
                        <p className="text-gray-600">Track your rehabilitation journey</p>
                    </div>
                    <button
                        onClick={downloadReport}
                        // CRITICAL: Button is now enabled by default. It disables only while generating.
                        disabled={isGenerating} 
                        className={`px-6 py-3 rounded-lg font-medium transition-all inline-flex items-center shadow-md shadow-blue-300/50 ${
                            !isGenerating
                            ? 'bg-blue-600 text-white hover:bg-blue-700' 
                            : 'bg-gray-400 text-gray-700 cursor-not-allowed'
                        }`}
                    >
                        <Download className="w-5 h-5 mr-2" />
                        {isGenerating ? 'Generating...' : 'Download PDF Report'}
                    </button>
                </div>


                {/* Attach ref to the main content container */}
                <div ref={reportRef} className="p-4 bg-white rounded-xl shadow-2xl"> 

                    {/* KPI Cards (More shadow and lift) */}
                    <div className="grid md:grid-cols-4 gap-6 mb-8">
                        <div className="bg-white rounded-xl shadow-xl p-6 transition transform hover:scale-[1.02] duration-300">
                            <div className="flex items-center justify-between mb-4">
                                <div className="bg-blue-100 p-3 rounded-xl shadow-inner">
                                    <Activity className="w-6 h-6 text-blue-600" />
                                </div>
                            </div>
                            <div className="text-3xl font-extrabold text-gray-900 mb-1">
                                {progressData.total_sessions}
                            </div>
                            <div className="text-sm text-gray-600">Total Sessions</div>
                        </div>

                        <div className="bg-white rounded-xl shadow-xl p-6 transition transform hover:scale-[1.02] duration-300">
                            <div className="flex items-center justify-between mb-4">
                                <div className="bg-green-100 p-3 rounded-xl shadow-inner">
                                    <Target className="w-6 h-6 text-green-600" />
                                </div>
                            </div>
                            <div className="text-3xl font-extrabold text-gray-900 mb-1">
                                {progressData.total_reps}
                            </div>
                            <div className="text-sm text-gray-600">Total Reps</div>
                        </div>

                        <div className="bg-white rounded-xl shadow-xl p-6 transition transform hover:scale-[1.02] duration-300">
                            <div className="flex items-center justify-between mb-4">
                                <div className="bg-yellow-100 p-3 rounded-xl shadow-inner">
                                    <TrendingUp className="w-6 h-6 text-yellow-600" />
                                </div>
                            </div>
                            <div className="text-3xl font-extrabold text-gray-900 mb-1">
                                {progressData.average_accuracy.toFixed(1)}%
                            </div>
                            <div className="text-sm text-gray-600">Avg Accuracy</div>
                        </div>

                        <div className="bg-white rounded-xl shadow-xl p-6 transition transform hover:scale-[1.02] duration-300">
                            <div className="flex items-center justify-between mb-4">
                                <div className="bg-orange-100 p-3 rounded-xl shadow-inner">
                                    <Award className="w-6 h-6 text-orange-600" />
                                </div>
                            </div>
                            <div className="text-3xl font-extrabold text-gray-900 mb-1">
                                {progressData.streak_days}
                            </div>
                            <div className="text-sm text-gray-600">Day Streak</div>
                        </div>
                    </div>

                    {/* Weekly Activity and Recent Sessions */}
                    <div className="grid lg:grid-cols-2 gap-8">
                        <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
                            <div className="flex items-center mb-6">
                                <Calendar className="w-6 h-6 text-blue-600 mr-2" />
                                <h2 className="text-xl font-bold text-gray-900">Weekly Activity (Reps & Accuracy)</h2>
                            </div>

                            <div className="space-y-4">
                                {progressData.weekly_data.map((day, index) => (
                                    <div key={index}>
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-sm font-medium text-gray-700">{day.day}</span>
                                            <div className="flex items-center gap-4 text-sm">
                                                <span className="text-gray-600">{day.reps} reps</span>
                                                <span className={`font-medium ${day.accuracy > 0 ? 'text-green-600' : 'text-gray-400'}`}>
                                                    {day.accuracy.toFixed(0)}%
                                                </span>
                                            </div>
                                        </div>
                                        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                                            {/* Dynamic color based on accuracy */}
                                            <div
                                                className={`h-full rounded-full transition-all ${getBarColorClass(day.accuracy)}`}
                                                style={{ width: `${(day.reps / maxReps) * 100}%` }} 
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="mt-6 pt-6 border-t border-gray-200">
                                <div className="flex items-center justify-between text-sm">
                                    <span className="text-gray-600">Weekly Average</span>
                                    <span className="font-semibold text-gray-900">
                                        {(progressData.weekly_data.reduce((sum, d) => sum + d.reps, 0) / 7).toFixed(0)} reps/day
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
                            <div className="flex items-center mb-6">
                                <Activity className="w-6 h-6 text-green-600 mr-2" />
                                <h2 className="text-xl font-bold text-gray-900">Recent Sessions Focus</h2>
                            </div>

                            <div className="space-y-4">
                                {progressData.recent_sessions.map((session, index) => (
                                    <div
                                        key={index}
                                        className="border-2 border-gray-200 rounded-lg p-4 transition transform hover:shadow-md"
                                    >
                                        <div className="flex items-start justify-between mb-2">
                                            <div>
                                                <h3 className="font-semibold text-gray-900">{session.exercise}</h3>
                                                <p className="text-xs text-blue-600 font-medium">
                                                    {new Date(session.date).toLocaleDateString('en-US', {
                                                        month: 'short', day: 'numeric', year: 'numeric',
                                                    })}
                                                </p>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-2xl font-bold text-blue-600">{session.reps}</div>
                                                <div className="text-xs text-gray-600">reps</div>
                                            </div>
                                        </div>
                                        <div className="flex items-center mt-2">
                                            <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
                                                <div
                                                    className="bg-green-500 h-full rounded-full"
                                                    style={{ width: `${session.accuracy}%` }}
                                                />
                                            </div>
                                            <span className="ml-3 text-sm font-medium text-green-600">
                                                {session.accuracy.toFixed(0)}% Accuracy
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <button className="mt-6 w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-all">
                                View Full Session History
                            </button>
                        </div>
                    </div>

                    {/* Encouragement Banner (Creative) */}
                    <div className="mt-8 bg-gradient-to-r from-blue-600 to-green-600 rounded-xl shadow-lg p-8 text-white relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-30">
                           <Award size={80} />
                        </div>
                        <div className="flex items-center justify-between relative z-10">
                            <div>
                                <h2 className="text-2xl font-extrabold mb-2">Personalized Feedback</h2>
                                <p className="text-blue-100 max-w-lg">
                                    {encouragementMessage}
                                </p>
                            </div>
                            <div className="bg-white bg-opacity-20 backdrop-blur-sm rounded-xl p-6 text-center shadow-lg">
                                <div className="text-4xl font-extrabold mb-1">{progressData.streak_days}</div>
                                <div className="text-sm text-blue-100">Day Streak</div>
                            </div>
                        </div>
                    </div>
                </div> {/* End of reportRef div */}

            </div>
        </div>
    );
};