import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Activity, ArrowRight, User, Ruler, Scale, Heart, Leaf, CheckCircle2 } from 'lucide-react';

interface RegisterProps {
    onToggleMode: () => void;
}

const INJURY_OPTIONS = [
    'Shoulder Injury',
    'Leg/Knee Injury',
    'Elbow Injury',
    'Wrist Injury',
    'Other/General',
];

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

    const [step, setStep] = useState(1);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    const [name, setName] = useState('');
    const [age, setAge] = useState<number | ''>('');
    const [sex, setSex] = useState<'Male' | 'Female' | 'Other'>('Male');
    const [heightCm, setHeightCm] = useState<number | ''>('');
    const [weightKg, setWeightKg] = useState<number | ''>('');
    const [injuryType, setInjuryType] = useState(INJURY_OPTIONS[0]);
    const [dietaryPreference, setDietaryPreference] = useState(DIETARY_OPTIONS[0]);

    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleFinalSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        if (!name || !age || !heightCm || !weightKg || age <= 0 || heightCm <= 0 || weightKg <= 0) {
            setError('Please fill in all profile fields with valid data.');
            setLoading(false);
            return;
        }

        const { error: signUpError } = await signUp(email, password);

        if (signUpError) {
            setError(signUpError.message || 'Failed to create account');
            setLoading(false);
            return;
        }

        console.log("User Profile Data Collected:", {
            name, age, sex, heightCm, weightKg, injuryType, dietaryPreference
        });

        setSuccess(true);
        setLoading(false);
        setTimeout(onToggleMode, 2000);
    };

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

        setStep(2);
    };

    const RenderStep1 = () => (
        <form onSubmit={handleStep1Submit} className="space-y-6">
            <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Create Your Account</h2>
                <p className="text-gray-600">Start by setting up your secure credentials</p>
            </div>

            <div className="space-y-5">
                <div>
                    <label htmlFor="email" className="block text-sm font-semibold text-gray-700 mb-2">
                        Email Address
                    </label>
                    <input
                        id="email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full px-4 py-3.5 rounded-xl border-2 border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-gray-50 hover:bg-white"
                        placeholder="you@example.com"
                        required
                    />
                </div>

                <div>
                    <label htmlFor="password" className="block text-sm font-semibold text-gray-700 mb-2">
                        Password
                    </label>
                    <input
                        id="password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full px-4 py-3.5 rounded-xl border-2 border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-gray-50 hover:bg-white"
                        placeholder="••••••••"
                        required
                    />
                    <p className="text-xs text-gray-500 mt-1.5">At least 6 characters</p>
                </div>

                <div>
                    <label htmlFor="confirmPassword" className="block text-sm font-semibold text-gray-700 mb-2">
                        Confirm Password
                    </label>
                    <input
                        id="confirmPassword"
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="w-full px-4 py-3.5 rounded-xl border-2 border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-gray-50 hover:bg-white"
                        placeholder="••••••••"
                        required
                    />
                </div>
            </div>

            <button
                type="submit"
                className="w-full bg-gradient-to-r from-blue-600 to-blue-700 text-white py-4 rounded-xl font-semibold hover:from-blue-700 hover:to-blue-800 focus:ring-4 focus:ring-blue-200 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 flex items-center justify-center group"
            >
                Continue to Profile
                <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
            </button>
        </form>
    );

    const RenderStep2 = () => (
        <form onSubmit={handleFinalSubmit} className="space-y-6">
            <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Build Your Digital Twin</h2>
                <p className="text-gray-600">Help us personalize your rehabilitation journey</p>
            </div>

            <div className="space-y-5">
                <div>
                    <label htmlFor="name" className="block text-sm font-semibold text-gray-700 mb-2">
                        Full Name
                    </label>
                    <div className="relative">
                        <User className="w-5 h-5 text-gray-400 absolute left-4 top-1/2 transform -translate-y-1/2" />
                        <input
                            id="name"
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="w-full pl-12 pr-4 py-3.5 rounded-xl border-2 border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-gray-50 hover:bg-white"
                            placeholder="Alex Johnson"
                            required
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label htmlFor="age" className="block text-sm font-semibold text-gray-700 mb-2">
                            Age
                        </label>
                        <div className="relative">
                            <Heart className="w-5 h-5 text-gray-400 absolute left-4 top-1/2 transform -translate-y-1/2" />
                            <input
                                id="age"
                                type="number"
                                value={age}
                                onChange={(e) => setAge(parseInt(e.target.value) || '')}
                                className="w-full pl-12 pr-4 py-3.5 rounded-xl border-2 border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-gray-50 hover:bg-white"
                                placeholder="25"
                                min="10"
                                required
                            />
                        </div>
                    </div>

                    <div>
                        <label htmlFor="sex" className="block text-sm font-semibold text-gray-700 mb-2">
                            Sex
                        </label>
                        <select
                            id="sex"
                            value={sex}
                            onChange={(e) => setSex(e.target.value as 'Male' | 'Female' | 'Other')}
                            className="w-full px-4 py-3.5 rounded-xl border-2 border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all appearance-none bg-gray-50 hover:bg-white"
                            required
                        >
                            <option value="Male">Male</option>
                            <option value="Female">Female</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label htmlFor="height" className="block text-sm font-semibold text-gray-700 mb-2">
                            Height (cm)
                        </label>
                        <div className="relative">
                            <Ruler className="w-5 h-5 text-gray-400 absolute left-4 top-1/2 transform -translate-y-1/2" />
                            <input
                                id="height"
                                type="number"
                                value={heightCm}
                                onChange={(e) => setHeightCm(parseInt(e.target.value) || '')}
                                className="w-full pl-12 pr-4 py-3.5 rounded-xl border-2 border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-gray-50 hover:bg-white"
                                placeholder="170"
                                min="50"
                                required
                            />
                        </div>
                    </div>

                    <div>
                        <label htmlFor="weight" className="block text-sm font-semibold text-gray-700 mb-2">
                            Weight (kg)
                        </label>
                        <div className="relative">
                            <Scale className="w-5 h-5 text-gray-400 absolute left-4 top-1/2 transform -translate-y-1/2" />
                            <input
                                id="weight"
                                type="number"
                                value={weightKg}
                                onChange={(e) => setWeightKg(parseInt(e.target.value) || '')}
                                className="w-full pl-12 pr-4 py-3.5 rounded-xl border-2 border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-gray-50 hover:bg-white"
                                placeholder="70"
                                min="10"
                                required
                            />
                        </div>
                    </div>
                </div>

                <div>
                    <label htmlFor="dietaryPreference" className="block text-sm font-semibold text-gray-700 mb-2">
                        Dietary Preference
                    </label>
                    <div className="relative">
                        <Leaf className="w-5 h-5 text-gray-400 absolute left-4 top-1/2 transform -translate-y-1/2 pointer-events-none" />
                        <select
                            id="dietaryPreference"
                            value={dietaryPreference}
                            onChange={(e) => setDietaryPreference(e.target.value)}
                            className="w-full pl-12 pr-4 py-3.5 rounded-xl border-2 border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all appearance-none bg-gray-50 hover:bg-white"
                            required
                        >
                            {DIETARY_OPTIONS.map(option => (
                                <option key={option} value={option}>{option}</option>
                            ))}
                        </select>
                    </div>
                </div>

                <div>
                    <label htmlFor="injuryType" className="block text-sm font-semibold text-gray-700 mb-2">
                        Primary Injury Focus
                    </label>
                    <select
                        id="injuryType"
                        value={injuryType}
                        onChange={(e) => setInjuryType(e.target.value)}
                        className="w-full px-4 py-3.5 rounded-xl border-2 border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all appearance-none bg-gray-50 hover:bg-white"
                        required
                    >
                        {INJURY_OPTIONS.map(option => (
                            <option key={option} value={option}>{option}</option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="space-y-3">
                <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-gradient-to-r from-green-600 to-emerald-600 text-white py-4 rounded-xl font-semibold hover:from-green-700 hover:to-emerald-700 focus:ring-4 focus:ring-green-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 flex items-center justify-center group"
                >
                    {loading ? (
                        <>
                            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                            Creating Your Profile...
                        </>
                    ) : (
                        <>
                            Complete Registration
                            <CheckCircle2 className="w-5 h-5 ml-2 group-hover:scale-110 transition-transform" />
                        </>
                    )}
                </button>

                <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="w-full text-gray-600 py-3 rounded-xl font-medium hover:bg-gray-100 transition-all"
                >
                    Back to Credentials
                </button>
            </div>
        </form>
    );

    return (
        <div className="min-h-screen relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-emerald-50"></div>

            <div className="absolute inset-0 opacity-30">
                <div className="absolute top-0 left-0 w-96 h-96 bg-blue-400 rounded-full mix-blend-multiply filter blur-3xl animate-blob"></div>
                <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-400 rounded-full mix-blend-multiply filter blur-3xl animate-blob animation-delay-2000"></div>
                <div className="absolute bottom-0 left-1/2 w-96 h-96 bg-teal-400 rounded-full mix-blend-multiply filter blur-3xl animate-blob animation-delay-4000"></div>
            </div>

            <div className="relative min-h-screen flex items-center justify-center p-4 py-12">
                <div className="max-w-md w-full">
                    <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl p-10 border border-white/20">
                        <div className="flex items-center justify-center mb-8">
                            <div className="relative">
                                <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-emerald-600 rounded-2xl blur-lg opacity-50"></div>
                                <div className="relative bg-gradient-to-r from-blue-600 to-emerald-600 p-4 rounded-2xl shadow-lg">
                                    <Activity className="w-10 h-10 text-white" />
                                </div>
                            </div>
                        </div>

                        <div className="text-center mb-8">
                            <h1 className="text-4xl font-extrabold bg-gradient-to-r from-blue-600 to-emerald-600 bg-clip-text text-transparent mb-3">
                                Digital Twin Setup
                            </h1>
                            <p className="text-gray-600 text-sm">
                                {step === 1 ? 'Begin your personalized rehabilitation journey' : 'Almost there! Complete your profile'}
                            </p>
                        </div>

                        <div className="mb-8 flex justify-center items-center space-x-3">
                            <div className="flex items-center">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all ${
                                    step >= 1 ? 'bg-blue-600 text-white shadow-lg' : 'bg-gray-200 text-gray-500'
                                }`}>
                                    1
                                </div>
                                <div className={`ml-2 text-sm font-medium ${step >= 1 ? 'text-blue-600' : 'text-gray-400'}`}>
                                    Credentials
                                </div>
                            </div>
                            <div className={`w-16 h-1 rounded-full transition-all ${step >= 2 ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
                            <div className="flex items-center">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all ${
                                    step >= 2 ? 'bg-emerald-600 text-white shadow-lg' : 'bg-gray-200 text-gray-500'
                                }`}>
                                    2
                                </div>
                                <div className={`ml-2 text-sm font-medium ${step >= 2 ? 'text-emerald-600' : 'text-gray-400'}`}>
                                    Profile
                                </div>
                            </div>
                        </div>

                        {error && (
                            <div className="bg-red-50 border-2 border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm mb-6 font-medium flex items-center shadow-sm">
                                <div className="w-2 h-2 bg-red-500 rounded-full mr-3 animate-pulse"></div>
                                {error}
                            </div>
                        )}

                        {success && (
                            <div className="bg-emerald-50 border-2 border-emerald-200 text-emerald-700 px-4 py-3 rounded-xl text-sm mb-6 font-medium flex items-center shadow-sm">
                                <CheckCircle2 className="w-5 h-5 mr-2" />
                                Profile created! Redirecting to sign in...
                            </div>
                        )}

                        {step === 1 && RenderStep1()}
                        {step === 2 && RenderStep2()}

                        <div className="mt-8 text-center pt-6 border-t border-gray-200">
                            <p className="text-gray-600 text-sm">
                                Already have an account?{' '}
                                <button
                                    onClick={onToggleMode}
                                    className="font-semibold bg-gradient-to-r from-blue-600 to-emerald-600 bg-clip-text text-transparent hover:from-blue-700 hover:to-emerald-700 transition-all"
                                >
                                    Sign in now
                                </button>
                            </p>
                        </div>
                    </div>

                    <div className="text-center mt-6 text-xs text-gray-500">
                        By registering, you agree to our Terms of Service and Privacy Policy
                    </div>
                </div>
            </div>

            <style>{`
                @keyframes blob {
                    0%, 100% { transform: translate(0, 0) scale(1); }
                    33% { transform: translate(30px, -50px) scale(1.1); }
                    66% { transform: translate(-20px, 20px) scale(0.9); }
                }
                .animate-blob {
                    animation: blob 7s infinite;
                }
                .animation-delay-2000 {
                    animation-delay: 2s;
                }
                .animation-delay-4000 {
                    animation-delay: 4s;
                }
            `}</style>
        </div>
    );
};
