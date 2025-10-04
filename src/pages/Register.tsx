import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Activity, ArrowRight, User, Ruler, Bone, Leaf } from 'lucide-react'; // Added 'Leaf' icon

interface RegisterProps {
    onToggleMode: () => void;
}

// 🎯 Injury Type Options (Matching your API plans)
const INJURY_OPTIONS = [
    'Shoulder Injury',
    'Leg/Knee Injury',
    'Elbow Injury',
    'Wrist Injury',
    'Other/General',
];

// 🎯 DIETARY OPTIONS
const DIETARY_OPTIONS = [
    'None (Omnivore)',
    'Vegetarian',
    'Vegan',
    'Keto',
    'Paleo',
    'Gluten-Free',
    'Other',
];

export const Register: React.FC<RegisterProps> = ({ onToggleMode }) => {
    const { signUp } = useAuth();
    
    // --- STEP 1: LOGIN/BASIC DATA ---
    const [step, setStep] = useState(1);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    
    // --- STEP 2: TWIN DATA ---
    const [name, setName] = useState('');
    const [age, setAge] = useState<number | ''>('');
    const [sex, setSex] = useState<'Male' | 'Female' | 'Other'>('Male');
    const [heightCm, setHeightCm] = useState<number | ''>('');
    const [weightKg, setWeightKg] = useState<number | ''>('');
    const [injuryType, setInjuryType] = useState(INJURY_OPTIONS[0]);
    // ✅ NEW STATE FOR DIETARY PREFERENCE
    const [dietaryPreference, setDietaryPreference] = useState(DIETARY_OPTIONS[0]);

    // --- UI/API State ---
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [loading, setLoading] = useState(false);

    // This function runs after Step 1 is valid, and handles final registration
    const handleFinalSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        // 1. Validate Profile Data
        if (!name || !age || !heightCm || !weightKg || age <= 0 || heightCm <= 0 || weightKg <= 0) {
            setError('Please fill in all profile fields with valid data.');
            setLoading(false);
            return;
        }

        // 2. Mock API Sign Up (Replace with actual backend call if necessary)
        const { error: signUpError } = await signUp(email, password); 

        if (signUpError) {
            setError(signUpError.message || 'Failed to create account');
            setLoading(false);
            return;
        }

        // 3. Mock Saving Profile Data (In a real app, this is a separate POST to your user profile table)
        // For the hackathon, we simply log the data.
        console.log("User Profile Data Collected:", {
            name, age, sex, heightCm, weightKg, injuryType,
            // ✅ Include new field in logged data
            dietaryPreference 
        });


        // 4. Final Success
        setSuccess(true);
        setLoading(false);
        setTimeout(onToggleMode, 2000); // Redirect to login after a moment
    };
    
    // This function handles the initial credential check and moves to Step 2
    const handleStep1Submit = (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccess(false);

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }
        if (password.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }
        
        // Move to the next step
        setStep(2);
    };

    const RenderStep1 = () => (
        <form onSubmit={handleStep1Submit} className="space-y-6">
            <h2 className="text-xl font-bold text-gray-800 border-b pb-2 mb-4">Step 1: Your Credentials</h2>

            {/* Email */}
            <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                    placeholder="you@example.com"
                    required
                />
            </div>

            {/* Password */}
            <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">Password</label>
                <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                    placeholder="••••••••"
                    required
                />
            </div>

            {/* Confirm Password */}
            <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">Confirm Password</label>
                <input
                    id="confirmPassword"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                    placeholder="••••••••"
                    required
                />
            </div>

            <button
                type="submit"
                className="w-full bg-indigo-500 text-white py-3 rounded-lg font-bold hover:bg-indigo-600 focus:ring-4 focus:ring-indigo-200 transition-all flex items-center justify-center"
            >
                Continue to Profile <ArrowRight className="w-5 h-5 ml-2" />
            </button>
        </form>
    );

    const RenderStep2 = () => (
        <form onSubmit={handleFinalSubmit} className="space-y-6">
            <h2 className="text-xl font-bold text-gray-800 border-b pb-2 mb-4">Step 2: Your Digital Twin Profile</h2>
            
            {/* Name */}
            <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">Name / Nickname</label>
                <div className="flex items-center border border-gray-300 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-green-500 focus-within:border-transparent transition-all">
                    <User className="w-5 h-5 text-gray-400 mx-3" />
                    <input
                        id="name"
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="w-full px-2 py-3 outline-none"
                        placeholder="e.g. Alex"
                        required
                    />
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
                {/* Age */}
                <div>
                    <label htmlFor="age" className="block text-sm font-medium text-gray-700 mb-2">Age</label>
                    <input
                        id="age"
                        type="number"
                        value={age}
                        onChange={(e) => setAge(parseInt(e.target.value) || '')}
                        className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                        placeholder="Years"
                        min="10"
                        required
                    />
                </div>
                
                {/* Sex/Gender */}
                <div>
                    <label htmlFor="sex" className="block text-sm font-medium text-gray-700 mb-2">Sex</label>
                    <select
                        id="sex"
                        value={sex}
                        onChange={(e) => setSex(e.target.value as 'Male' | 'Female' | 'Other')}
                        className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all appearance-none bg-white"
                        required
                    >
                        <option value="Male">Male</option>
                        <option value="Female">Female</option>
                        <option value="Other">Other</option>
                    </select>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
                {/* Height */}
                <div>
                    <label htmlFor="height" className="block text-sm font-medium text-gray-700 mb-2">Height (cm)</label>
                    <div className="flex items-center border border-gray-300 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-green-500 focus-within:border-transparent transition-all">
                        <Ruler className="w-5 h-5 text-gray-400 mx-3" />
                        <input
                            id="height"
                            type="number"
                            value={heightCm}
                            onChange={(e) => setHeightCm(parseInt(e.target.value) || '')}
                            className="w-full px-2 py-3 outline-none"
                            placeholder="cm"
                            min="50"
                            required
                        />
                    </div>
                </div>

                {/* Weight */}
                <div>
                    <label htmlFor="weight" className="block text-sm font-medium text-gray-700 mb-2">Weight (kg)</label>
                    <div className="flex items-center border border-gray-300 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-green-500 focus-within:border-transparent transition-all">
                        <Bone className="w-5 h-5 text-gray-400 mx-3" />
                        <input
                            id="weight"
                            type="number"
                            value={weightKg}
                            onChange={(e) => setWeightKg(parseInt(e.target.value) || '')}
                            className="w-full px-2 py-3 outline-none"
                            placeholder="kg"
                            min="10"
                            required
                        />
                    </div>
                </div>
            </div>
            
            {/* ✅ NEW: Dietary Preference */}
            <div>
                <label htmlFor="dietaryPreference" className="block text-sm font-medium text-gray-700 mb-2">Dietary Preference</label>
                <div className="relative">
                    <Leaf className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                    <select
                        id="dietaryPreference"
                        value={dietaryPreference}
                        onChange={(e) => setDietaryPreference(e.target.value)}
                        className="w-full px-10 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all appearance-none bg-white"
                        required
                    >
                        {DIETARY_OPTIONS.map(option => (
                            <option key={option} value={option}>{option}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Injury Type */}
            <div>
                <label htmlFor="injuryType" className="block text-sm font-medium text-gray-700 mb-2">Injury/Rehab Focus</label>
                <select
                    id="injuryType"
                    value={injuryType}
                    onChange={(e) => setInjuryType(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all appearance-none bg-white"
                    required
                >
                    {INJURY_OPTIONS.map(option => (
                        <option key={option} value={option}>{option}</option>
                    ))}
                </select>
            </div>

            <button
                type="submit"
                disabled={loading}
                className="w-full bg-green-600 text-white py-3 rounded-lg font-bold hover:bg-green-700 focus:ring-4 focus:ring-green-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
                {loading ? 'Finalizing Profile...' : 'Complete Registration'}
            </button>
            <button
                type="button"
                onClick={() => setStep(1)}
                className="w-full text-indigo-500 py-2 rounded-lg font-medium hover:text-indigo-600 transition-colors"
            >
                &larr; Back to Credentials
            </button>
        </form>
    );

    return (
        // 🎨 Aesthetic BG gradient and rounded card
        <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-teal-50 flex items-center justify-center p-4">
            <div className="max-w-md w-full bg-white rounded-3xl shadow-2xl p-10">
                <div className="flex items-center justify-center mb-6">
                    <div className="bg-green-600 p-4 rounded-xl shadow-lg">
                        <Activity className="w-8 h-8 text-white" />
                    </div>
                </div>

                <h1 className="text-4xl font-extrabold text-center text-gray-900 mb-3">
                    Digital Twin Setup
                </h1>
                <p className="text-center text-gray-600 mb-8">
                    {step === 1 ? 'Create your login credentials.' : 'Tell us about your rehab needs.'}
                </p>

                {/* Progress Indicator */}
                <div className="mb-8 flex justify-center items-center space-x-2">
                    <div className={`w-8 h-2 rounded-full ${step === 1 ? 'bg-indigo-500' : 'bg-gray-300'}`}></div>
                    <div className={`w-8 h-2 rounded-full ${step === 2 ? 'bg-indigo-500' : 'bg-gray-300'}`}></div>
                </div>

                {/* Status Messages */}
                {error && (
                    <div className="bg-red-100 border border-red-400 text-red-800 px-4 py-3 rounded-xl text-sm mb-6 font-medium">
                        {error}
                    </div>
                )}
                {success && (
                    <div className="bg-green-100 border border-green-400 text-green-800 px-4 py-3 rounded-xl text-sm mb-6 font-medium">
                        Account and profile created successfully! Redirecting to sign in...
                    </div>
                )}

                {/* Conditional Step Rendering */}
                {step === 1 && RenderStep1()}
                {step === 2 && RenderStep2()}

                <div className="mt-8 text-center border-t pt-6">
                    <p className="text-gray-600">
                        Already set up?{' '}
                        <button
                            onClick={onToggleMode}
                            className="text-indigo-600 font-bold hover:text-indigo-700 transition-colors"
                        >
                            Sign in now
                        </button>
                    </p>
                </div>
            </div>
        </div>
    );
};
