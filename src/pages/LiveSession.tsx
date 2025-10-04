import React, { useRef, useState, useEffect } from 'react';
import { Camera, StopCircle, Play, AlertCircle, CheckCircle, Award, RotateCw, MoveLeft, MoveRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';


// --- INTERFACE DEFINITIONS (omitted for brevity) ---
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
}

interface LiveSessionProps {
    plan: ExercisePlan;
    exercise: Exercise;
    onComplete: () => void;
}

interface FeedbackItem {
    type: 'correction' | 'encouragement' | 'warning' | 'progress'; // Added 'progress' type
    message: string;
}

interface Landmark {
    x: number; 
    y: number; 
    visibility: number;
}

interface Coordinate {
    x: number;
    y: number;
}

interface DrawingData {
    landmarks: Landmark[]; 
    angleData?: { 
        angle: number, 
        A: Coordinate, 
        B: Coordinate, 
        C: Coordinate 
    }
}

const POSE_CONNECTIONS: [number, number][] = [
    [11, 12], [11, 13], [13, 15], [15, 17], [15, 19], [15, 21], [17, 19], [12, 14], [14, 16], [16, 18], [16, 20], [16, 22],
    [11, 23], [12, 24], [23, 24], [23, 25], [24, 26], [25, 27], [26, 28], [27, 29], [28, 30], [29, 31], [30, 32], [27, 31], [28, 32]
];

// --- DRAWING UTILITY FUNCTION (omitted for brevity) ---
const drawLandmarks = (
    ctx: CanvasRenderingContext2D,
    drawingData: DrawingData,
    width: number,
    height: number,
) => {
    ctx.clearRect(0, 0, width, height);
    ctx.lineWidth = 4;
    const { landmarks, angleData } = drawingData;

    // 1. Draw Skeleton Lines
    // 🎨 Aesthetic Change: Use a softer, glowing blue line color
    ctx.strokeStyle = 'rgba(0, 150, 255, 0.9)'; 
    POSE_CONNECTIONS.forEach(([i, j]) => {
        const p1 = landmarks[i];
        const p2 = landmarks[j];

        if (p1?.visibility > 0.6 && p2?.visibility > 0.6) {
            ctx.beginPath();
            ctx.moveTo(p1.x * width, p1.y * height);
            ctx.lineTo(p2.x * width, p2.y * height);
            ctx.stroke();
        }
    });

    // 2. Draw Joints (Circles)
    // 🎨 Aesthetic Change: Use a vibrant coral color for active joints
    ctx.fillStyle = '#FF7F50'; 
    landmarks.forEach(p => {
        if (p.visibility > 0.6) {
            ctx.beginPath();
            ctx.arc(p.x * width, p.y * height, 6, 0, 2 * Math.PI);
            ctx.fill();
        }
    });

    // 3. Draw Angle Text
    if (angleData && angleData.angle > 0) {
        const { angle, A, B, C } = angleData;

        const center = { x: B.x * width, y: B.y * height };
        const pA = { x: A.x * width, y: A.y * height };
        const pC = { x: C.x * width, y: C.y * height };
        
        const startAngle = Math.atan2(pA.y - center.y, pA.x - center.x);
        const endAngle = Math.atan2(pC.y - center.y, pC.x - center.x);
        
        let start = startAngle < 0 ? startAngle + 2 * Math.PI : startAngle;
        let end = endAngle < 0 ? endAngle + 2 * Math.PI : endAngle;

        if (start > end) { [start, end] = [end, start]; }
        
        // Draw Angle Arc
        ctx.strokeStyle = '#32CD32'; // Lime green for the angle indicator
        ctx.lineWidth = 5;
        ctx.beginPath();
        ctx.arc(center.x, center.y, 40, start, end);
        ctx.stroke();

        // Draw Angle Text
        ctx.fillStyle = '#FFFFFF';
        ctx.strokeStyle = '#10B981'; // Mint shadow
        ctx.lineWidth = 4;
        ctx.font = 'bold 30px sans-serif'; // Bolder font
        
        const textX = center.x + 10;
        const textY = center.y - 10;

        ctx.strokeText(`${angle.toFixed(0)}°`, textX, textY);
        ctx.fillText(`${angle.toFixed(0)}°`, textX, textY);
    }
};

// ----------------------------------------------------


export const LiveSession: React.FC<LiveSessionProps> = ({ exercise, onComplete }) => {
    const { user } = useAuth(); // Get authenticated user
    const videoRef = useRef<HTMLVideoElement>(null);
    const hiddenCanvasRef = useRef<HTMLCanvasElement>(null); 
    const drawingCanvasRef = useRef<HTMLCanvasElement>(null); 
    
    const sessionStateRef = useRef<any>({ 
        reps: 0, 
        stage: 'down', 
        angle: 0, 
        last_rep_time: 0 
    }); 

    // UI State
    const [isActive, setIsActive] = useState(false);
    const [reps, setReps] = useState(0);
    const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
    const [accuracy, setAccuracy] = useState(0);
    const [error, setError] = useState('');
    const [drawingData, setDrawingData] = useState<DrawingData | null>(null);
    
    // NEW STATE: Side Toggle Control
    const [analysisSide, setAnalysisSide] = useState<'auto' | 'left' | 'right'>('auto');
    const [setsCompleted, setSetsCompleted] = useState(0);
    const [showCompletionModal, setShowCompletionModal] = useState(false);
    
    const intervalRef = useRef<NodeJs.Timeout | null>(null);
    const [lastActivityTime, setLastActivityTime] = useState(Date.now());
    const PAUSE_TIMEOUT_MS = 5000; 

    // --- GIF MAP (paths corrected to root public folder) ---
    const EXERCISE_GIF_MAP: { [key: string]: string } = {
        "shoulder flexion": "/standing-shoulder-flexion.gif",
        "shoulder abduction": "/standing-shoulder-abduction.gif",
        "elbow flexion": "/seated-elbow-flexion.gif",
        "elbow extension": "/seated-elbow-extension.gif",
        "shoulder internal rotation": "/shoulder-internal-rotation.gif",
        "knee flexion": "/supine-knee-flexion.gif",
        "ankle dorsiflexion": "/seated-ankle-dorsiflexion.gif",
        "wrist flexion": "/seated-wrist-flexion.gif",
    };
    
    // --- Dynamic GIF Logic ---
    const exerciseKey = exercise.name.toLowerCase();
    const gifSrc = EXERCISE_GIF_MAP[exerciseKey] || "/default-exercise-guide.gif"; 
    const gifDisplayName = exercise.name;
    const gifPlaceholderText = "Image Not Available";


    // --- PAUSE/INACTIVITY DETECTOR (omitted for brevity) ---
    useEffect(() => {
        let pauseCheckInterval: NodeJS.Timeout | null = null;

        if (isActive) {
            pauseCheckInterval = setInterval(() => {
                const timeSinceLastActivity = Date.now() - lastActivityTime;
                
                if (timeSinceLastActivity > PAUSE_TIMEOUT_MS && reps > 0 && setsCompleted < exercise.sets) {
                    console.log(`PAUSE DETECTED: Auto-saving session.`);
                    stopSession(true, true); 
                }
            }, 1000); 

        } else if (pauseCheckInterval) {
            clearInterval(pauseCheckInterval);
        }

        return () => {
            if (pauseCheckInterval) clearInterval(pauseCheckInterval);
        };
    }, [isActive, lastActivityTime, reps, setsCompleted, exercise.sets]); 


    // --- Save Session Result Function (omitted for brevity) ---
    const saveSessionResult = async (finalReps: number, finalAccuracy: number, isAutoSave: boolean) => {
        if (!user?.id) {
            console.error("Cannot save session: User ID is missing.");
            return;
        }
        if (finalReps === 0) {
            console.log("Session ended with 0 reps, not saving.");
            return;
        }
        
        try {
            const response = await fetch('https://exercise-7edj.onrender.com/api/save_session', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: user.id, 
                    exercise_name: exercise.name,
                    reps_completed: finalReps,
                    accuracy_score: finalAccuracy,
                }),
            });

            if (!response.ok) {
                const errorDetail = await response.json().catch(() => ({ detail: 'Unknown Save Error' }));
                console.error('Failed to save session:', response.status, errorDetail.detail);
            }
        } catch (error) {
            console.error('Network error while saving session:', error);
        }
    };

    // --- Core analysis and session control functions (omitted for brevity) ---
    // ... (All other complex functions like captureAndAnalyze, stopSession, startCamera remain the same)
    
    // --- Helper function for aesthetic feedback colors ---
    const getFeedbackColor = (type: string) => {
        switch (type) {
            // 🎨 Aesthetic colors for feedback boxes
            case 'correction': return 'bg-yellow-100 border-yellow-400 text-yellow-800';
            case 'encouragement': return 'bg-green-100 border-green-400 text-green-800';
            case 'warning': return 'bg-red-100 border-red-400 text-red-800';
            case 'progress': return 'bg-blue-100 border-blue-400 text-blue-800'; // Added for calibration/current movement
            default: return 'bg-gray-100 border-gray-300 text-gray-700';
        }
    };

    const handleSideChange = (side: 'auto' | 'left' | 'right') => {
        // ... (function logic remains the same)
        setAnalysisSide(side);
        if (isActive) {
            // Restart session to clear state for new side
            stopSession(false, false); 
            setTimeout(startCamera, 500);
        }
    };
    
    // --- Render Side Toggle UI (omitted for brevity) ---
    const SideToggleButton = (
        <div className="flex items-center space-x-2 bg-white p-2 rounded-xl border border-gray-200">
            <RotateCw className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-semibold text-gray-700">Side:</span>
            
            {/* Auto Button */}
            <button
                onClick={() => handleSideChange('auto')}
                className={`px-3 py-1 rounded-full text-xs font-bold transition ${
                    analysisSide === 'auto' ? 'bg-indigo-500 text-white shadow-md' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
                AUTO
            </button>
            
            {/* Left Button */}
            <button
                onClick={() => handleSideChange('left')}
                className={`px-3 py-1 rounded-full text-xs font-bold transition ${
                    analysisSide === 'left' ? 'bg-indigo-500 text-white shadow-md' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
                LEFT
            </button>
            
            {/* Right Button */}
            <button
                onClick={() => handleSideChange('right')}
                className={`px-3 py-1 rounded-full text-xs font-bold transition ${
                    analysisSide === 'right' ? 'bg-indigo-500 text-white shadow-md' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
                RIGHT
            </button>
        </div>
    );
    // ---------------------------

    // --- Final Completion Modal Component (omitted for brevity) ---
    if (showCompletionModal) {
        return (
            <div className="fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center z-50 p-4">
                <div className="bg-white rounded-3xl shadow-2xl p-10 w-full max-w-md text-center transform transition-all duration-300 scale-100">
                    <Award className="w-16 h-16 text-yellow-500 mx-auto mb-6 animate-pulse" />
                    <h2 className="text-3xl font-extrabold text-green-600 mb-3">
                        🎉 Mission Complete! 🎉
                    </h2>
                    <p className="text-gray-700 mb-8 font-medium">
                        You crushed all **{exercise.sets} sets** of **{exercise.name}**! Your commitment is incredible.
                    </p>
                    <div className="bg-green-50 rounded-xl p-4 mb-8">
                        <p className="font-extrabold text-xl text-green-800">
                            Total Sets: {setsCompleted} / {exercise.sets}
                        </p>
                    </div>
                    <button
                        onClick={onComplete}
                        className="w-full bg-indigo-600 text-white py-4 rounded-xl text-lg font-bold hover:bg-indigo-700 transition-all shadow-lg"
                    >
                        Back to Progress
                    </button>
                </div>
            </div>
        );
    }
    // ------------------------------------


    return (
        // 🎨 Aesthetic Change: Soft pastel background gradient
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 py-12">
            <div className="max-w-7xl mx-auto px-4">
                {/* 🎨 Aesthetic Change: Large rounded corners and distinct shadow */}
                <div className="bg-white rounded-3xl shadow-2xl p-10">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-10 border-b pb-6 border-gray-100">
                        <div className="mb-4 md:mb-0">
                            <h1 className="text-4xl font-extrabold text-gray-800 mb-1">
                                {exercise.name} 
                            </h1>
                            <p className="text-lg text-indigo-500 font-semibold mb-3">{exercise.description}</p>
                            
                            {/* NEW: Display the side toggle next to the exercise title */}
                            <div className="mt-4">{SideToggleButton}</div>
                        </div>
                        <button
                            onClick={() => {
                                // Only save if reps > 0
                                stopSession(reps > 0, true); 
                            }} 
                            // 🎨 Aesthetic Change: Clear secondary action button
                            className="bg-gray-100 text-gray-600 px-6 py-3 rounded-xl font-semibold hover:bg-gray-200 transition-all text-sm"
                        >
                            End Session
                        </button>
                    </div>

                    <div className="grid lg:grid-cols-2 gap-10">
                        {/* LEFT COLUMN: VIDEO & GIF GUIDE */}
                        <div className="order-2 lg:order-1">
                            {/* Image/Video Display */}
                            {/* 🎨 Aesthetic Change: Soft shadow around video container */}
                            <div className="relative bg-gray-900 rounded-3xl overflow-hidden aspect-video shadow-xl">
                                
                                {/* Video element shows the live stream (omitted for brevity) */}
                                <video
                                    ref={videoRef}
                                    autoPlay
                                    playsInline
                                    muted
                                    className="w-full h-full object-cover transform scale-x-[-1]" // Flipping the video horizontally (optional)
                                />
                                <canvas ref={hiddenCanvasRef} className="hidden" />

                                {/* Drawing canvas OVERLAY */}
                                <canvas
                                    ref={drawingCanvasRef}
                                    className="absolute top-0 left-0 w-full h-full object-cover transform scale-x-[-1]"
                                />

                                {/* Start/Stop UI overlay */}
                                {!isActive && (
                                    <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-70">
                                        <div className="text-center p-6 bg-white bg-opacity-90 rounded-2xl shadow-2xl">
                                            <Camera className="w-12 h-12 text-indigo-600 mx-auto mb-4" />
                                            <p className="text-gray-800 text-xl font-semibold mb-6">Ready to begin?</p>
                                            <button
                                                onClick={startCamera}
                                                // 🎨 Aesthetic Change: Gradient button
                                                className="bg-gradient-to-r from-green-500 to-teal-500 text-white px-8 py-4 rounded-full text-lg font-bold hover:from-green-600 hover:to-teal-600 transition-all inline-flex items-center shadow-lg"
                                            >
                                                <Play className="w-5 h-5 mr-2 fill-white" />
                                                Start Session
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* GIF Display and Error */}
                            <div className="mt-8">
                                {error && (
                                    // 🎨 Aesthetic Change: Bolder error box
                                    <div className="mb-6 bg-red-100 border-2 border-red-400 text-red-800 px-5 py-4 rounded-xl text-base font-medium flex items-center shadow-sm">
                                        <AlertCircle className="w-6 h-6 mr-3" />
                                        {error}
                                    </div>
                                )}
                                
                                {/* Instruction/GIF AREA - ALWAYS DISPLAYED */}
                                <div className="bg-white p-6 border-2 border-gray-100 rounded-2xl text-center shadow-md">
                                    <h3 className="font-extrabold text-xl text-gray-800 mb-3 border-b pb-2 border-gray-200">Reference Form</h3>
                                    <p className="text-sm text-gray-600 mb-4">Maintain this form throughout the movement for best results.</p>
                                    
                                    {/* DYNAMIC GIF SOURCE */}
                                    <img 
                                        src={gifSrc} 
                                        alt={gifDisplayName} 
                                        // 🎨 Aesthetic Change: Slightly larger image and stronger styling
                                        className="w-56 h-56 object-contain mx-auto rounded-xl shadow-lg border-4 border-white"
                                        onError={(e) => { 
                                            e.currentTarget.onerror = null; 
                                            e.currentTarget.src = `https://placehold.co/224x224/FF6347/ffffff?text=${gifPlaceholderText}`; 
                                        }}
                                    />
                                    <p className="text-sm text-indigo-500 font-medium mt-3">Current Exercise: {gifDisplayName}</p>
                                </div>

                            </div>

                            {isActive && (
                                <button
                                    onClick={() => stopSession(true, true)}
                                    // 🎨 Aesthetic Change: Prominent danger button
                                    className="mt-6 w-full bg-red-500 text-white py-4 rounded-xl text-lg font-bold hover:bg-red-600 transition-all inline-flex items-center justify-center shadow-lg"
                                >
                                    <StopCircle className="w-6 h-6 mr-3" />
                                    Stop & Save Progress
                                </button>
                            )}
                            <div className="mt-4 text-sm text-gray-500 text-center">
                                {isActive && `| Auto-save if paused for ${PAUSE_TIMEOUT_MS / 1000} seconds`}
                            </div>
                        </div>

                        {/* RIGHT COLUMN: METRICS & FEEDBACK */}
                        <div className="space-y-6 order-1 lg:order-2">
                            
                            {/* REPS & ACCURACY BOXES */}
                            <div className="grid grid-cols-2 gap-4">
                                {/* Reps Card */}
                                {/* 🎨 Aesthetic Change: Soft shadow, bold font */}
                                <div className="bg-indigo-50 rounded-3xl p-6 shadow-md border-b-4 border-indigo-200">
                                    <div className="text-6xl font-extrabold text-indigo-600 mb-1">
                                        {reps}
                                    </div>
                                    <div className="text-md text-gray-600 font-semibold">
                                        Reps
                                    </div>
                                    <div className="text-xs text-gray-500 mt-2">
                                        Target: {exercise.target_reps} / set
                                    </div>
                                </div>

                                {/* Accuracy Card */}
                                <div className="bg-teal-50 rounded-3xl p-6 shadow-md border-b-4 border-teal-200">
                                    <div className="text-6xl font-extrabold text-teal-600 mb-1">
                                        {accuracy.toFixed(0)}%
                                    </div>
                                    <div className="text-md text-gray-600 font-semibold">
                                        Accuracy
                                    </div>
                                    <div className="text-xs text-gray-500 mt-2">
                                        Avg. Form Score
                                    </div>
                                </div>
                            </div>

                            {/* SESSION DETAILS */}
                            <div className="bg-white border border-gray-200 rounded-3xl p-6 shadow-md">
                                <h3 className="text-xl font-extrabold text-gray-800 mb-4 border-b pb-2">
                                    Session Progress
                                </h3>
                                <div className="space-y-3 text-base">
                                    <div className="flex justify-between items-center">
                                        <span className="text-gray-600 font-medium flex items-center">
                                            <CheckCircle className="w-5 h-5 mr-2 text-indigo-400" />Sets Completed:
                                        </span>
                                        <span className="font-extrabold text-indigo-600">{setsCompleted} / {exercise.sets}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-gray-600 font-medium flex items-center">
                                            <RotateCw className="w-5 h-5 mr-2 text-green-400" />Current Reps:
                                        </span>
                                        <span className="font-extrabold text-green-600">{reps}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Rest Time:</span>
                                        <span className="font-semibold text-gray-700">{exercise.rest_seconds} seconds</span>
                                    </div>
                                </div>
                            </div>

                            {/* REAL-TIME FEEDBACK */}
                            <div className="bg-white border-2 border-gray-300 rounded-3xl p-6 shadow-xl min-h-[250px] relative">
                                <h3 className="text-xl font-extrabold text-gray-800 mb-4 border-b pb-2">
                                    Live Coaching
                                </h3>
                                <div className="space-y-3 max-h-[300px] overflow-y-auto">
                                    {feedback.length > 0 ? (
                                        feedback.map((item, index) => (
                                            <div
                                                key={index}
                                                // 🎨 Aesthetic Change: Rounded, bordered feedback boxes
                                                className={`px-4 py-3 rounded-xl border-2 font-medium text-sm transition-opacity duration-300 ${getFeedbackColor(item.type)}`}
                                            >
                                                {item.message}
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-gray-500 text-center py-10 font-medium">
                                            {isActive ? 'Start moving to begin calibration...' : 'Start the session to receive live coaching.'}
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* SET COMPLETION BANNER */}
                            {reps >= exercise.target_reps && setsCompleted < exercise.sets && (
                                <div className="bg-green-100 border-4 border-green-500 rounded-3xl p-6 text-center shadow-2xl animate-bounce">
                                    <div className="text-3xl font-extrabold text-green-800 mb-3">
                                        🔥 SET COMPLETE!
                                    </div>
                                    <p className="text-lg text-green-700 mb-5 font-semibold">
                                        Great job! Take a {exercise.rest_seconds} second rest before Set {setsCompleted + 2}.
                                    </p>
                                    <button
                                        onClick={handleSetCompletion}
                                        className="bg-green-600 text-white px-8 py-3 rounded-full text-lg font-bold hover:bg-green-700 transition-all shadow-lg"
                                    >
                                        Start Next Set ({setsCompleted + 1} / {exercise.sets})
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
