import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Activity, Mail, Lock } from 'lucide-react'; // Added Mail and Lock icons

interface LoginProps {
  onToggleMode: () => void;
}

export const Login: React.FC<LoginProps> = ({ onToggleMode }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signIn } = useAuth();

  const handleSubmit = async (e: React.FormFormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const { error: authError } = await signIn(email, password); // Renamed error to authError

    if (authError) {
      setError(authError.message || 'Failed to sign in');
    }

    setLoading(false);
  };

  return (
    // 1. AESTHETIC BACKGROUND & DEPTH: Darker, rich gradient with pseudo-elements for abstract shapes
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center p-4 bg-gray-900 font-sans">
      
      {/* Abstract Background Elements for depth and color */}
      <div className="absolute top-0 left-0 w-80 h-80 bg-teal-500 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
      <div className="absolute top-1/2 right-0 w-80 h-80 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
      <div className="absolute bottom-0 left-1/4 w-80 h-80 bg-indigo-500 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>

      {/* Tailwind animation configuration (requires adding to your tailwind.config.js):
          // module.exports = { theme: { extend: { animation: { 'blob': 'blob 7s infinite', }, keyframes: { blob: { '0%, 100%': { transform: 'translate(0px, 0px) scale(1)' }, '33%': { transform: 'translate(30px, -50px) scale(1.1)' }, '66%': { transform: 'translate(-20px, 20px) scale(0.9)' }, }, }, }, }, ... } 
      */}

      {/* 2. GLASS MORPHISM CARD CONTAINER */}
      <div className="relative max-w-md w-full bg-white/10 backdrop-blur-lg border border-white/20 rounded-3xl shadow-[0_25px_50px_-12px_rgba(0,0,0,0.5)] p-10 z-10 transform hover:scale-[1.02] transition-transform duration-500">
        
        {/* ICON CONTAINER */}
        <div className="flex items-center justify-center mb-8">
          {/* Subtle 3D effect on the icon wrapper */}
          <div className="bg-gradient-to-r from-blue-500 to-indigo-600 p-4 rounded-full shadow-[0_0_15px_rgba(66,153,225,0.8)] transform hover:rotate-6 transition-transform duration-300">
            <Activity className="w-8 h-8 text-white" />
          </div>
        </div>

        {/* TYPOGRAPHY */}
        <h1 className="text-4xl font-extrabold text-white text-center mb-2 tracking-wide">
          Welcome Back
        </h1>
        <p className="text-center text-gray-300 mb-10 font-light italic">
          Sign in to continue your rehabilitation journey
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* ERROR MESSAGE */}
          {error && (
            <div className="bg-red-900/40 border border-red-700 text-red-300 px-4 py-3 rounded-lg text-sm transition-all shadow-md">
              {error}
            </div>
          )}

          {/* EMAIL INPUT GROUP */}
          <div>
            <label htmlFor="email" className="block text-sm font-semibold text-gray-200 mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-indigo-300" />
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                // Neumorphic/Glass input style
                className="w-full pl-12 pr-4 py-3 rounded-xl bg-white/5 border border-white/20 text-white placeholder-gray-400 focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-all shadow-inner-custom"
                placeholder="you@example.com"
                required
              />
            </div>
          </div>

          {/* PASSWORD INPUT GROUP */}
          <div>
            <label htmlFor="password" className="block text-sm font-semibold text-gray-200 mb-2">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-indigo-300" />
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                // Neumorphic/Glass input style
                className="w-full pl-12 pr-4 py-3 rounded-xl bg-white/5 border border-white/20 text-white placeholder-gray-400 focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-all shadow-inner-custom"
                placeholder="••••••••"
                required
              />
            </div>
          </div>

          {/* SUBMIT BUTTON */}
          <button
            type="submit"
            disabled={loading}
            // Aggressive gradient and shadow for emphasis
            className="w-full bg-gradient-to-r from-teal-500 to-green-600 text-white py-3 rounded-xl font-bold text-lg tracking-wider shadow-lg shadow-teal-500/50 hover:from-teal-600 hover:to-green-700 focus:ring-4 focus:ring-teal-300 transition-all duration-300 transform hover:translate-y-[-1px] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Signing In...' : 'Access My Plan'}
          </button>
        </form>

        {/* TOGGLE MODE LINK */}
        <div className="mt-8 text-center">
          <p className="text-gray-400">
            Don't have an account?{' '}
            <button
              onClick={onToggleMode}
              className="text-indigo-400 font-bold hover:text-indigo-300 transition-colors underline underline-offset-4 decoration-indigo-400/50 hover:decoration-indigo-300"
            >
              Join Our Program
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

// NOTE: To get the full aesthetic effect (like the animated blobs), 
// you need to add the 'animation-blob' and 'shadow-inner-custom' utility 
// styles to your project's main CSS file or tailwind.config.js.
