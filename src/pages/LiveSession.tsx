import React, { useRef, useState, useEffect } from 'react';
import { Camera, StopCircle, Play, AlertCircle, Award } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

// --- INTERFACE DEFINITIONS ---
interface Exercise { name: string; description: string; target_reps: number; sets: number; rest_seconds: number; }
interface ExercisePlan { ailment: string; exercises: Exercise[]; }
interface LiveSessionProps { plan: ExercisePlan; exercise: Exercise; onComplete: () => void; }
interface FeedbackItem { type: 'correction' | 'encouragement' | 'warning'; message: string; }
interface Landmark { x: number; y: number; visibility: number; }
interface Coordinate { x: number; y: number; }
interface DrawingData { landmarks: Landmark[]; angleData?: { angle: number; A: Coordinate; B: Coordinate; C: Coordinate } }

const POSE_CONNECTIONS: [number, number][] = [
    [11,12],[11,13],[13,15],[15,17],[15,19],[15,21],[17,19],[12,14],[14,16],[16,18],[16,20],[16,22],
    [11,23],[12,24],[23,24],[23,25],[24,26],[25,27],[26,28],[27,29],[28,30],[29,31],[30,32],[27,31],[28,32]
];

const drawLandmarks = (ctx: CanvasRenderingContext2D, drawingData: DrawingData, width: number, height: number) => {
    ctx.clearRect(0,0,width,height);
    const { landmarks, angleData } = drawingData;
    ctx.lineWidth = 4;

    ctx.strokeStyle = 'rgba(76, 175, 80, 0.9)';
    POSE_CONNECTIONS.forEach(([i,j])=>{
        const p1 = landmarks[i]; const p2 = landmarks[j];
        if(p1?.visibility>0.6 && p2?.visibility>0.6){
            ctx.beginPath(); ctx.moveTo(p1.x*width,p1.y*height); ctx.lineTo(p2.x*width,p2.y*height); ctx.stroke();
        }
    });

    ctx.fillStyle = 'white';
    landmarks.forEach(p=>{
        if(p.visibility>0.6){ctx.beginPath(); ctx.arc(p.x*width,p.y*height,6,0,2*Math.PI); ctx.fill();}
    });

    if(angleData && angleData.angle>0){
        const { angle,A,B,C } = angleData;
        const center = { x:B.x*width, y:B.y*height };
        const pA = { x:A.x*width, y:A.y*height };
        const pC = { x:C.x*width, y:C.y*height };
        let start = Math.atan2(pA.y-center.y,pA.x-center.x); if(start<0) start+=2*Math.PI;
        let end = Math.atan2(pC.y-center.y,pC.x-center.x); if(end<0) end+=2*Math.PI;
        if(start>end)[start,end]=[end,start];
        ctx.strokeStyle = '#FFC107'; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(center.x,center.y,40,start,end); ctx.stroke();
        ctx.fillStyle='white'; ctx.strokeStyle='black'; ctx.lineWidth=2; ctx.font='bold 24px Arial';
        const textX=center.x+10, textY=center.y-10; ctx.strokeText(${angle.toFixed(0)}°,textX,textY); ctx.fillText(${angle.toFixed(0)}°,textX,textY);
    }
};


export const LiveSession: React.FC<LiveSessionProps> = ({ exercise, onComplete }) => {
    const { user } = useAuth();
    const videoRef = useRef<HTMLVideoElement>(null);
    const hiddenCanvasRef = useRef<HTMLCanvasElement>(null);
    const drawingCanvasRef = useRef<HTMLCanvasElement>(null);
    const sessionStateRef = useRef<any>({ reps:0, stage:'down', angle:0, last_rep_time:0 });

    const [isActive,setIsActive] = useState(false);
    const [reps,setReps] = useState(0);
    const [feedback,setFeedback] = useState<FeedbackItem[]>([]);
    const [accuracy,setAccuracy] = useState(0);
    const [error,setError] = useState('');
    const [drawingData,setDrawingData] = useState<DrawingData | null>(null);
    const [analysisSide,setAnalysisSide] = useState<'auto'|'left'|'right'>('auto');
    const [setsCompleted,setSetsCompleted] = useState(0);
    const [showCompletionModal,setShowCompletionModal] = useState(false);
    const [lastActivityTime,setLastActivityTime] = useState(Date.now());
    const intervalRef = useRef<NodeJS.Timeout|null>(null);
    const PAUSE_TIMEOUT_MS = 5000;

    // --- AUDIO FEEDBACK ---
    const audioMap: { [key: string]: HTMLAudioElement } = {
        "No pose detected. Adjust your camera view.": new Audio("/audio/no_pose.mp3"),
        "I can't see you clearly. Please adjust your position.": new Audio("/audio/low_visibility.mp3"),
        "Please turn sideways or expose one full side.": new Audio("/audio/side_not_visible.mp3"),
        "Incomplete return to starting position. Try again.": new Audio("/audio/incomplete_return.mp3"),
        "Slow down! Move with control.": new Audio("/audio/slow_movement.mp3"),
        "Hold the contracted position at the top.": new Audio("/audio/hold_top.mp3"),
        "Go deeper for a full repetition.": new Audio("/audio/go_deeper.mp3"),
        "Push further to the maximum range.": new Audio("/audio/push_max.mp3"),
        "Return fully to the starting position.": new Audio("/audio/return_full.mp3"),
        "Ready to start the next repetition.": new Audio("/audio/next_rep.mp3"),
        "Controlled movement upward.": new Audio("/audio/controlled_up.mp3"),
        "Calibrating range. Move fully from start to finish position.": new Audio("/audio/calibrating.mp3"),
        "Full repetition completed! Well done.": new Audio("/audio/full_rep.mp3"),
        "Partial repetition counted. Complete the movement.": new Audio("/audio/partial_rep.mp3")
    };

    useEffect(()=>{
        if(feedback.length===0) return;
        const latestMessage = feedback[feedback.length-1].message;
        if(audioMap[latestMessage]){
            audioMap[latestMessage].play().catch(err=>console.warn("Audio play error:",err));
        }
    }, [feedback]);
    // ------------------

    const EXERCISE_GIF_MAP: { [key:string]:string } = {
        "shoulder flexion": "/standing-shoulder-flexion.gif",
        "shoulder abduction": "/standing-shoulder-abduction.gif",
        "elbow flexion": "/seated-elbow-flexion.gif",
        "elbow extension": "/gifs/seated-elbow-extension.gif",
        "shoulder internal rotation": "/gifs/shoulder-internal-rotation.gif",
        "knee flexion": "/gifs/supine-knee-flexion.gif",
        "ankle dorsiflexion": "/gifs/seated-ankle-dorsiflexion.gif",
        "wrist flexion": "/gifs/seated-wrist-flexion.gif",
    };
    const exerciseKey = exercise.name.toLowerCase();
    const gifSrc = EXERCISE_GIF_MAP[exerciseKey] || "/gifs/default-exercise-guide.gif";
    const gifDisplayName = exercise.name;
    const gifPlaceholderText = "GIF Not Found";

    // --- START CAMERA ---
    const startCamera = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video:{ width:640, height:480 }});
            if(videoRef.current) videoRef.current.srcObject = stream;
            setIsActive(true); setError(''); setLastActivityTime(Date.now());
            sessionStateRef.current={ reps:0, stage:'down', angle:0, last_rep_time:0 }; setReps(0); setFeedback([]);
            intervalRef.current = setInterval(()=>captureAndAnalyze(), 500);
        } catch(err){ setError('Failed to access camera. Please grant camera permissions.'); }
    };

    // --- STOP SESSION ---
    const stopSession = (shouldSave:boolean, shouldCompletePage:boolean) => {
        if(intervalRef.current){ clearInterval(intervalRef.current); intervalRef.current=null; }
        if(videoRef.current && videoRef.current.srcObject){
            (videoRef.current.srcObject as MediaStream).getTracks().forEach(track=>track.stop());
            videoRef.current.srcObject=null;
        }
        if(shouldSave) saveSessionResult(sessionStateRef.current.reps,accuracy,shouldCompletePage);
        if(shouldCompletePage) sessionStateRef.current={ reps:0, stage:'down', angle:0, last_rep_time:0 };
        setDrawingData(null); setIsActive(false);
        if(shouldCompletePage) onComplete();
    };

    // --- SAVE SESSION ---
    const saveSessionResult = async (finalReps:number, finalAccuracy:number, isAutoSave:boolean) => {
        if(!user?.id) return;
        if(finalReps===0) return;
        try{
            const response = await fetch('https://exercise-7edj.onrender.com/api/save_session',{
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({ user_id:user.id, exercise_name:exercise.name, reps_completed:finalReps, accuracy_score:finalAccuracy })
            });
            if(!response.ok){ const errorDetail=await response.json().catch(()=>({ detail:'Unknown Save Error'})); console.error('Failed to save session:', response.status, errorDetail.detail); }
        }catch(err){ console.error('Network error while saving session:',err); }
    };

    // --- CAPTURE & ANALYZE FRAME ---
    const captureAndAnalyze = async () => {
        if(!videoRef.current || !hiddenCanvasRef.current || showCompletionModal) return;
        const canvas = hiddenCanvasRef.current;
        const video = videoRef.current;
        canvas.width = video.videoWidth; canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d'); if(!ctx) return;
        ctx.drawImage(video,0,0,canvas.width,canvas.height);
        const frameData = canvas.toDataURL('image/jpeg',0.8);
        const latestState = sessionStateRef.current;
        const stateToSend = {...latestState, analysis_side: analysisSide==='auto'?null:analysisSide};
        try{
            const response = await fetch('https://exercise-7edj.onrender.com/api/analyze_frame',{
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({ frame:frameData, exercise_name:exercise.name, previous_state:stateToSend })
            });
            if(!response.ok){ const errorDetail=await response.json().catch(()=>({detail:'Unknown Server Error'})); throw new Error(Failed to analyze frame: ${errorDetail.detail});}
            const data = await response.json();
            setLastActivityTime(Date.now());
            sessionStateRef.current = data.state;
            if(data.state.analysis_side && analysisSide==='auto') setAnalysisSide(data.state.analysis_side);
            setReps(data.reps); setFeedback(data.feedback); setAccuracy(data.accuracy_score);
            setDrawingData({ landmarks:data.drawing_landmarks, angleData:{ angle:data.current_angle, A:data.angle_coords.A, B:data.angle_coords.B, C:data.angle_coords.C }});
            if(data.reps>=exercise.target_reps) stopSession(false,false);
        }catch(err){ console.error('Analysis error:',err); setError('Connection or Analysis Error.'); setDrawingData(null);}
    };

    // --- DRAWING EFFECT ---
    useEffect(()=>{
        if(drawingData && drawingCanvasRef.current && isActive){
            const canvas=drawingCanvasRef.current;
            const ctx=canvas.getContext('2d'); const video=videoRef.current;
            if(ctx && video){ canvas.width=video.videoWidth; canvas.height=video.videoHeight; drawLandmarks(ctx,drawingData,canvas.width,canvas.height); }
        }else if(drawingCanvasRef.current) drawingCanvasRef.current.getContext('2d')?.clearRect(0,0,drawingCanvasRef.current.width,drawingCanvasRef.current.height);
    },[drawingData,isActive]);

    useEffect(()=>{ return ()=>{ stopSession(false,false); }; },[]);

    // --- RENDER ---
    return (
        <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-blue-50 py-8">
            <div className="max-w-7xl mx-auto px-4">
                <div className="bg-white rounded-2xl shadow-xl p-8">
                    <div className="flex items-center justify-between mb-8">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900 mb-2">
                                {exercise.name} (Set {setsCompleted+1} of {exercise.sets})
                            </h1>
                            <p className="text-gray-600">{exercise.description}</p>
                        </div>
                        <button onClick={()=>stopSession(false,true)} className="bg-gray-100 text-gray-700 px-6 py-3 rounded-lg font-medium hover:bg-gray-200 transition-all">End Session</button>
                    </div>

                    <div className="grid lg:grid-cols-2 gap-8">
                        <div>
                            <div className="relative bg-gray-900 rounded-xl overflow-hidden aspect-video">
                                <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover"/>
                                <canvas ref={hiddenCanvasRef} className="hidden"/>
                                <canvas ref={drawingCanvasRef} className="absolute top-0 left-0 w-full h-full object-cover"/>
                                {!isActive && <div className="absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-50">
                                    <div className="text-center">
                                        <Camera className="w-16 h-16 text-white mx-auto mb-4"/>
                                        <p className="text-white text-lg mb-4">Camera not active</p>
                                        <button onClick={startCamera} className="bg-green-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-green-700 transition-all inline-flex items-center">
                                            <Play className="w-5 h-5 mr-2"/> Start Camera
                                        </button>
                                    </div>
                                </div>}
                            </div>

                            <div className="mt-4 bg-gray-50 rounded-xl p-4 text-center">
                                <h3 className="font-bold text-gray-800 mb-2">Reference Form</h3>
                                <p className="text-sm text-gray-600 mb-3">Ensure your body matches the form while exercising.</p>
                                <img src={gifSrc} alt={gifDisplayName} className="w-48 h-48 object-contain mx-auto rounded-lg shadow-md"
                                    onError={(e)=>{ e.currentTarget.onerror=null; e.currentTarget.src=https://placehold.co/192x192/FF6347/ffffff?text=${gifPlaceholderText}; }}/>
                                <p className="text-xs text-gray-500 mt-2">Example: {gifDisplayName}</p>
                            </div>
                        </div>

                        <div className="space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-blue-50 rounded-xl p-6 text-center">
                                    <div className="text-4xl font-bold text-blue-600 mb-2">{reps}</div>
                                    <div className="text-sm text-gray-600">Reps Completed</div>
                                    <div className="text-xs text-gray-500 mt-1">Target: {exercise.target_reps}</div>
                                </div>
                                <div className="bg-green-50 rounded-xl p-6 text-center">
                                    <div className="text-4xl font-bold text-green-600 mb-2">{accuracy.toFixed(0)}%</div>
                                    <div className="text-sm text-gray-600">Accuracy</div>
                                </div>
                            </div>

                            <div className="bg-yellow-50 rounded-xl p-6">
                                <h4 className="font-semibold text-yellow-800 mb-2">Feedback</h4>
                                <ul className="space-y-2">
                                    {feedback.slice(-5).map((f,i)=>(
                                        <li key={i} className={flex items-center ${f.type==='warning'?'text-red-600':f.type==='encouragement'?'text-green-600':'text-yellow-700'}}>
                                            {f.type==='warning'?<AlertCircle className="w-5 h-5 mr-2"/>:<Award className="w-5 h-5 mr-2"/>}{f.message}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>

                    {error && <p className="mt-4 text-red-600 font-medium text-center">{error}</p>}
                </div>
            </div>
        </div>
    );
};