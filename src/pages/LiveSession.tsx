import React, { useRef, useState, useEffect } from 'react';
import { Camera, StopCircle, Play, AlertCircle, CheckCircle, Award, Hand, HandPlatter, MoveLeft, MoveRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext'; // Original, correct import


// --- INTERFACE DEFINITIONS ---
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
    type: 'correction' | 'encouragement' | 'warning';
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

// --- DRAWING UTILITY FUNCTION (Outside Component) ---
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
    ctx.strokeStyle = 'rgba(76, 175, 80, 0.9)'; // Green lines
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
    ctx.fillStyle = 'rgb(255, 255, 255)'; // White circles
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

        // Convert normalized coordinates to pixel coordinates
        const center = { x: B.x * width, y: B.y * height };
        const pA = { x: A.x * width, y: A.y * height };
        const pC = { x: C.x * width, y: C.y * height };
        
        // Calculate the angle arc start and end points (simplified for drawing overlay)
        const startAngle = Math.atan2(pA.y - center.y, pA.x - center.x);
        const endAngle = Math.atan2(pC.y - center.y, pC.x - center.x);
        
        let start = startAngle < 0 ? startAngle + 2 * Math.PI : startAngle;
        let end = endAngle < 0 ? endAngle + 2 * Math.PI : endAngle;

        if (start > end) { [start, end] = [end, start]; }
        
        // Draw Angle Arc
        ctx.strokeStyle = '#FFC107'; // Amber color for arc
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(center.x, center.y, 40, start, end);
        ctx.stroke();

        // Draw Angle Text
        ctx.fillStyle = 'white';
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 2;
        ctx.font = 'bold 24px Arial';
        
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
    
    const intervalRef = useRef<NodeJS.Timeout | null>(null);
    const [lastActivityTime, setLastActivityTime] = useState(Date.now());
    const PAUSE_TIMEOUT_MS = 5000; 

    // --- PAUSE/INACTIVITY DETECTOR ---
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
    // ------------------------------------


    // --- Save Session Result Function ---
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
            const response = await fetch('https://exercise-7edj.onrender.com/api/save_session', { // Using localhost for dev stability
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: user.id, 
                    exercise_name: exercise.name,
                    reps_completed: finalReps,
                    accuracy_score: finalAccuracy,
                }),
            });

            if (response.ok) {
                console.log(`Successfully saved ${finalReps} reps to DB (AutoSave: ${isAutoSave}).`);
            } else {
                const errorDetail = await response.json().catch(() => ({ detail: 'Unknown Save Error' }));
                console.error('Failed to save session:', response.status, errorDetail.detail);
            }
        } catch (error) {
            console.error('Network error while saving session:', error);
        }
    };
    // ----------------------------------------


    // --- useEffect for Drawing (Remains the same) ---
    useEffect(() => {
        if (drawingData && drawingCanvasRef.current && isActive) {
            const canvas = drawingCanvasRef.current;
            const ctx = canvas.getContext('2d');
            const video = videoRef.current;
            
            if (ctx && video) {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;

                drawLandmarks(
                    ctx,
                    drawingData,
                    canvas.width,
                    canvas.height
                );
            }
        } else if (drawingCanvasRef.current) {
            drawingCanvasRef.current.getContext('2d')?.clearRect(0, 0, drawingCanvasRef.current.width, drawingCanvasRef.current.height);
        }
    }, [drawingData, isActive]);
    // ----------------------------


    useEffect(() => {
        return () => {
            stopSession(false, false); 
        };
    }, []);

    const captureAndAnalyze = async () => {
        if (!videoRef.current || !hiddenCanvasRef.current || showCompletionModal) return;

        const canvas = hiddenCanvasRef.current;
        const video = videoRef.current;

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        const frameData = canvas.toDataURL('image/jpeg', 0.8);

        const latestState = sessionStateRef.current; 
        
        // CRITICAL: Inject the manually selected side into the state sent to the API
        const stateToSend = {
            ...latestState,
            analysis_side: analysisSide === 'auto' ? null : analysisSide 
        };

        try {
            const response = await fetch('https://exercise-7edj.onrender.com/api/analyze_frame', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    frame: frameData,
                    exercise_name: exercise.name,
                    previous_state: stateToSend, 
                }),
            });

            if (!response.ok) {
                const errorDetail = await response.json().catch(() => ({ detail: 'Unknown Server Error' }));
                throw new Error(`Failed to analyze frame: ${errorDetail.detail}`);
            }

            const data = await response.json();

            setLastActivityTime(Date.now()); 

            // Update mutable ref with the *entire* state returned by the API
            sessionStateRef.current = data.state;
            
            // If the API auto-detected a side, update our local state to reflect it
            if (data.state.analysis_side && analysisSide === 'auto') {
                setAnalysisSide(data.state.analysis_side);
            }


            setReps(data.reps);
            setFeedback(data.feedback);
            setAccuracy(data.accuracy_score);
            setDrawingData({
                landmarks: data.drawing_landmarks,
                angleData: {
                    angle: data.current_angle,
                    A: data.angle_coords.A,
                    B: data.angle_coords.B,
                    C: data.angle_coords.C,
                }
            });


            if (data.reps >= exercise.target_reps) {
                stopSession(false, false);
            }
        } catch (err) {
            console.error('Analysis error:', err);
            setError('Connection or Analysis Error. Check backend console.');
            setDrawingData(null);
        }
    };

    // Modified stopSession to accept shouldSave and shouldCompletePage flags
    const stopSession = (shouldSave: boolean, shouldCompletePage: boolean) => {
        // Stop the interval
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
        }

        // Stop camera tracks
        if (videoRef.current && videoRef.current.srcObject) {
            const stream = videoRef.current.srcObject as MediaStream;
            stream.getTracks().forEach((track) => track.stop());
            videoRef.current.srcObject = null;
        }

        if (shouldSave) {
            saveSessionResult(sessionStateRef.current.reps, accuracy, shouldCompletePage);
        }
        
        if (shouldCompletePage) {
             sessionStateRef.current = { reps: 0, stage: 'down', angle: 0, last_rep_time: 0 };
        }
       
        setDrawingData(null); 
        setIsActive(false);

        if (shouldCompletePage) {
            onComplete(); 
        }
    };

    const startCamera = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480 },
            });

            if (videoRef.current) {
                videoRef.current.srcObject = stream;
            }

            setIsActive(true);
            setError('');
            setLastActivityTime(Date.now()); 

            sessionStateRef.current = { reps: 0, stage: 'down', angle: 0, last_rep_time: 0 };
            setReps(0);
            setFeedback([]);

            intervalRef.current = setInterval(() => {
                captureAndAnalyze();
            }, 500); 
        } catch (err) {
            setError('Failed to access camera. Please grant camera permissions.');
        }
    };

    // Function to handle the successful completion of a set
    const handleSetCompletion = () => {
        saveSessionResult(reps, accuracy, false); 

        const nextSetsCompleted = setsCompleted + 1;
        
        if (nextSetsCompleted >= exercise.sets) {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
            if (videoRef.current && videoRef.current.srcObject) {
                const stream = videoRef.current.srcObject as MediaStream;
                stream.getTracks().forEach((track) => track.stop());
                videoRef.current.srcObject = null;
            }
            setIsActive(false);
            
            setSetsCompleted(nextSetsCompleted);
            setShowCompletionModal(true); 
            
        } else {
            setSetsCompleted(nextSetsCompleted);
            setReps(0);
            setFeedback([]);
            sessionStateRef.current = { reps: 0, stage: 'down', angle: 0, last_rep_time: 0 };
            startCamera(); 
        }
    };

    const getFeedbackColor = (type: string) => {
        switch (type) {
            case 'correction': return 'bg-yellow-50 border-yellow-200 text-yellow-800';
            case 'encouragement': return 'bg-green-50 border-green-200 text-green-800';
            case 'warning': return 'bg-red-50 border-red-200 text-red-800';
            default: return 'bg-gray-50 border-gray-200 text-gray-800';
        }
    };
    
    // Utility for changing side
    const handleSideChange = (side: 'auto' | 'left' | 'right') => {
        setAnalysisSide(side);
        // Restart session to clear any ongoing calibration that might be stuck
        if (isActive) {
            stopSession(false, false); 
            setTimeout(startCamera, 500); // Restart analysis after a slight delay
        }
    };

    // --- Render Side Toggle UI ---
    const SideToggleButton = (
        <div className="flex items-center space-x-2 bg-gray-100 p-2 rounded-xl shadow-inner">
            <span className="text-sm font-medium text-gray-700">Analyze Side:</span>
            
            {/* Auto Button */}
            <button
                onClick={() => handleSideChange('auto')}
                className={`px-3 py-1 rounded-lg text-sm font-semibold transition ${
                    analysisSide === 'auto' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-blue-50'
                }`}
            >
                Auto
            </button>
            
            {/* Left Button */}
            <button
                onClick={() => handleSideChange('left')}
                className={`px-3 py-1 rounded-lg text-sm font-semibold transition ${
                    analysisSide === 'left' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-blue-50'
                }`}
            >
                Left
            </button>
            
            {/* Right Button */}
            <button
                onClick={() => handleSideChange('right')}
                className={`px-3 py-1 rounded-lg text-sm font-semibold transition ${
                    analysisSide === 'right' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-blue-50'
                }`}
            >
                Right
            </button>
        </div>
    );
    // ---------------------------

    // --- Final Completion Modal Component ---
    if (showCompletionModal) {
        return (
            <div className="fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center z-50 p-4">
                <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md text-center transform transition-all duration-300 scale-100">
                    <Award className="w-16 h-16 text-yellow-500 mx-auto mb-4 animate-bounce" />
                    <h2 className="text-3xl font-bold text-green-700 mb-2">
                        🎉 HURRAYYY! EXERCISE COMPLETE! 🎉
                    </h2>
                    <p className="text-gray-700 mb-6">
                        You successfully finished all **{exercise.sets} sets** of **{exercise.name}**!
                        Your discipline is a key step toward recovery.
                    </p>
                    <div className="bg-green-50 rounded-xl p-4 mb-6">
                        <p className="font-semibold text-lg text-green-800">
                            Total Sets Completed: {setsCompleted} / {exercise.sets}
                        </p>
                    </div>
                    <button
                        onClick={onComplete}
                        className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-all"
                    >
                        Return to Dashboard
                    </button>
                </div>
            </div>
        );
    }
    // ------------------------------------


    return (
        <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-blue-50 py-8">
            <div className="max-w-7xl mx-auto px-4">
                <div className="bg-white rounded-2xl shadow-xl p-8">
                    <div className="flex items-center justify-between mb-8">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900 mb-2">
                                {exercise.name} (Set {setsCompleted + 1} of {exercise.sets})
                            </h1>
                            <p className="text-gray-600">{exercise.description}</p>
                            {/* NEW: Display the side toggle next to the exercise title */}
                            <div className="mt-2">{SideToggleButton}</div>
                        </div>
                        <button
                            onClick={() => {
                                stopSession(false, true); 
                            }} 
                            className="bg-gray-100 text-gray-700 px-6 py-3 rounded-lg font-medium hover:bg-gray-200 transition-all"
                        >
                            End Session (Don't Save)
                        </button>
                    </div>

                    <div className="grid lg:grid-cols-2 gap-8">
                        <div>
                            {/* Image/Video Display */}
                            <div className="relative bg-gray-900 rounded-xl overflow-hidden aspect-video">
                                {/* Video element shows the live stream */}
                                <video
                                    ref={videoRef}
                                    autoPlay
                                    playsInline
                                    muted
                                    className="w-full h-full object-cover"
                                />
                                
                                {/* Hidden canvas for capturing frames to send to API */}
                                <canvas ref={hiddenCanvasRef} className="hidden" />

                                {/* Drawing canvas OVERLAY for skeleton and angles */}
                                <canvas
                                    ref={drawingCanvasRef}
                                    className="absolute top-0 left-0 w-full h-full object-cover"
                                />

                                {/* Start/Stop UI overlay */}
                                {!isActive && (
                                    <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-50">
                                        <div className="text-center">
                                            <Camera className="w-16 h-16 text-white mx-auto mb-4" />
                                            <p className="text-white text-lg mb-4">Camera not active</p>
                                            <button
                                                onClick={startCamera}
                                                className="bg-green-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-green-700 transition-all inline-flex items-center"
                                            >
                                                <Play className="w-5 h-5 mr-2" />
                                                Start Camera
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* NEW: GIF Display and Error */}
                            <div className="mt-4">
                                {error && (
                                    <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-center">
                                        <AlertCircle className="w-5 h-5 mr-2" />
                                        {error}
                                    </div>
                                )}
                                {/* Instruction/GIF AREA */}
                                {!isActive && (
                                    <div className="bg-gray-50 rounded-xl p-4 text-center">
                                        <h3 className="font-bold text-gray-800 mb-2">Reference Form</h3>
                                        <p className="text-sm text-gray-600 mb-3">Ensure your body matches the form before starting.</p>
                                        
                                        {/* Placeholder for the GIF */}
                                        <img 
                                            src="standing-shoulder-flexion.gif" 
                                            alt="Shoulder Flexion Exercise GIF" 
                                            className="w-48 h-48 object-contain mx-auto rounded-lg shadow-md"
                                            onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = "https://placehold.co/192x192/4488ff/ffffff?text=EXERCISE+GIF"; }}
                                        />
                                        <p className="text-xs text-gray-500 mt-2">Example: Shoulder Flexion (Side View)</p>
                                    </div>
                                )}
                            </div>

                            {isActive && (
                                <button
                                    onClick={() => stopSession(true, true)}
                                    className="mt-4 w-full bg-red-600 text-white py-3 rounded-lg font-medium hover:bg-red-700 transition-all inline-flex items-center justify-center"
                                >
                                    <StopCircle className="w-5 h-5 mr-2" />
                                    Stop Session & Save
                                </button>
                            )}
                            <div className="mt-4 text-sm text-gray-500 text-center">
                                {isActive && `Sets: ${setsCompleted} / ${exercise.sets}`}
                                {isActive && reps > 0 && ` | Auto-save if paused for ${PAUSE_TIMEOUT_MS / 1000} seconds`}
                            </div>
                        </div>

                        <div className="space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-blue-50 rounded-xl p-6">
                                    <div className="text-4xl font-bold text-blue-600 mb-2">
                                        {reps}
                                    </div>
                                    <div className="text-sm text-gray-600">
                                        Reps Completed
                                    </div>
                                    <div className="text-xs text-gray-500 mt-1">
                                        Target: {exercise.target_reps}
                                    </div>
                                </div>

                                <div className="bg-green-50 rounded-xl p-6">
                                    <div className="text-4xl font-bold text-green-600 mb-2">
                                        {accuracy.toFixed(0)}%
                                    </div>
                                    <div className="text-sm text-gray-600">
                                        Accuracy Score
                                    </div>
                                </div>
                            </div>

                            <div className="bg-gray-50 rounded-xl p-6">
                                <h3 className="text-lg font-bold text-gray-900 mb-4">
                                    Exercise Details
                                </h3>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Target Reps:</span>
                                        <span className="font-medium">{exercise.target_reps}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Sets:</span>
                                        <span className="font-medium">{setsCompleted} / {exercise.sets}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Rest Time:</span>
                                        <span className="font-medium">{exercise.rest_seconds}s</span>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                                <h3 className="text-lg font-bold text-gray-900 mb-4">
                                    Real-Time Feedback
                                </h3>
                                <div className="space-y-3">
                                    {feedback.length > 0 ? (
                                        feedback.map((item, index) => (
                                            <div
                                                key={index}
                                                className={`px-4 py-3 rounded-lg border ${getFeedbackColor(item.type)}`}
                                            >
                                                {item.message}
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-gray-500 text-sm text-center py-4">
                                            {isActive ? 'Position yourself in front of the camera...' : 'Start the session to receive feedback'}
                                        </div>
                                    )}
                                </div>
                            </div>

                            {reps >= exercise.target_reps && setsCompleted < exercise.sets && (
                                <div className="bg-green-50 border-2 border-green-200 rounded-xl p-6 text-center">
                                    <div className="text-2xl font-bold text-green-800 mb-2">
                                        YES! Set {setsCompleted + 1} Complete!
                                    </div>
                                    <p className="text-green-700 mb-4">
                                        Great job! Take a {exercise.rest_seconds} second rest before Set {setsCompleted + 2}.
                                    </p>
                                    <button
                                        onClick={handleSetCompletion}
                                        className="bg-green-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-green-700 transition-all"
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
