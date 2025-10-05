import React, { useState, useEffect, useMemo } from 'react';
import { Clock, TrendingUp, AlertTriangle, Activity } from 'lucide-react';

// --- Configuration ---
const BACKEND_URL = 'https://exercise-7edj.onrender.com';

// The injury types correspond to the one-hot encoded columns in your backend model
const INJURY_OPTIONS = [
    { label: "Ankle Injury", value: "Ankle injury" },
    { label: "Back Injury", value: "Back injury" },
    { label: "Calf Injury", value: "Calf injury" },
    { label: "Knee Injury", value: "Knee injury" },
    { label: "Shoulder Injury", value: "Shoulder injury" },
    { label: "Hamstring Strain", value: "Hamstring strain" },
    { label: "Groin Injury", value: "Groin injury" },
    { label: "Illness (Ill)", value: "Ill" },
    { label: "Foot Injury", value: "Foot injury" },
    { label: "Knee Surgery", value: "Knee surgery" },
    { label: "Minor Bruise", value: "bruise" },
    { label: "Muscle Injury", value: "muscle injury" },
];

const initialInput = {
    Age: 30,
    Health_Score: 7.5,
    Physio_adherence: 0.8,
    Complication_count: 0,
    Inflammation_marker: 1.5,
    Previous_injury: 0,
    Injury_Type: INJURY_OPTIONS[0].value,
};

// =========================================================================
// Recovery Predictor Component
// =========================================================================

const RecoveryPredictor = () => {
    const [input, setInput] = useState(initialInput);
    const [prediction, setPrediction] = useState<number | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value, type } = e.target;
        
        let processedValue: string | number | boolean = value;

        if (type === 'number') {
            // Convert to number for float/int fields
            processedValue = parseFloat(value) || 0;
            if (name === 'Complication_count' || name === 'Previous_injury') {
                processedValue = parseInt(value) || 0;
            }
        }
        if (type === 'checkbox') {
            processedValue = (e.target as HTMLInputElement).checked ? 1 : 0;
        }

        setInput(prev => ({ ...prev, [name]: processedValue }));
    };

    const handlePrediction = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setPrediction(null);
        setLoading(true);

        // Basic validation for required numerical fields
        if (!input.Age || !input.Health_Score || !input.Physio_adherence) {
            setError("Please fill out all required fields (Age, Health Score, Adherence).");
            setLoading(false);
            return;
        }

        try {
            const payload = {
                Age: input.Age,
                Health_Score: input.Health_Score,
                Physio_adherence: input.Physio_adherence,
                Complication_count: input.Complication_count,
                Inflammation_marker: input.Inflammation_marker,
                Previous_injury: input.Previous_injury,
                Injury_Type: input.Injury_Type,
            };

            const response = await fetch(`${BACKEND_URL}/api/predict_recovery`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown Server Error' }));
                throw new Error(errorData.detail || 'Prediction failed due to server error.');
            }

            const data = await response.json();
            setPrediction(data.median_recovery_days);

        } catch (err: any) {
            console.error("Prediction Error:", err);
            setError(err.message || "Failed to get prediction. Check server connection.");
        } finally {
            setLoading(false);
        }
    };

    const inputClasses = "w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 transition duration-150";
    const labelClasses = "block text-sm font-medium text-gray-700 mb-1";

    return (
        <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
                <div className="bg-white rounded-3xl shadow-2xl p-8 border-t-8 border-indigo-500">
                    <div className="flex items-center space-x-4 mb-8">
                        <Activity className="w-8 h-8 text-indigo-600" />
                        <h1 className="text-3xl font-bold text-gray-900">Recovery Time Predictor (CPH Model)</h1>
                    </div>
                    <p className="text-gray-600 mb-8">
                        Enter the patient's current metrics to estimate the median time required for full recovery, based on the Cox Proportional Hazards model.
                    </p>

                    <form onSubmit={handlePrediction} className="space-y-6">
                        
                        {/* Error Display */}
                        {error && (
                            <div className="bg-red-50 border border-red-300 text-red-700 p-4 rounded-lg flex items-center">
                                <AlertTriangle className="w-5 h-5 mr-3"/> {error}
                            </div>
                        )}

                        {/* --- Input Grid --- */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            
                            {/* Age */}
                            <div>
                                <label htmlFor="Age" className={labelClasses}>Age (Years)</label>
                                <input
                                    type="number"
                                    id="Age"
                                    name="Age"
                                    value={input.Age}
                                    onChange={handleChange}
                                    className={inputClasses}
                                    min="1" max="100" step="1"
                                    required
                                />
                            </div>

                            {/* Health_Score */}
                            <div>
                                <label htmlFor="Health_Score" className={labelClasses}>Health Score (0.0 - 10.0)</label>
                                <input
                                    type="number"
                                    id="Health_Score"
                                    name="Health_Score"
                                    value={input.Health_Score}
                                    onChange={handleChange}
                                    className={inputClasses}
                                    min="0" max="10" step="0.1"
                                    required
                                />
                            </div>

                            {/* Physio_adherence */}
                            <div>
                                <label htmlFor="Physio_adherence" className={labelClasses}>Physio Adherence (0.0 - 1.0)</label>
                                <input
                                    type="number"
                                    id="Physio_adherence"
                                    name="Physio_adherence"
                                    value={input.Physio_adherence}
                                    onChange={handleChange}
                                    className={inputClasses}
                                    min="0" max="1" step="0.01"
                                    required
                                />
                            </div>

                             {/* Inflammation_marker */}
                             <div>
                                <label htmlFor="Inflammation_marker" className={labelClasses}>Inflammation Marker Score</label>
                                <input
                                    type="number"
                                    id="Inflammation_marker"
                                    name="Inflammation_marker"
                                    value={input.Inflammation_marker}
                                    onChange={handleChange}
                                    className={inputClasses}
                                    min="0" step="0.1"
                                    required
                                />
                            </div>

                            {/* Complication_count */}
                            <div>
                                <label htmlFor="Complication_count" className={labelClasses}>Complication Count</label>
                                <input
                                    type="number"
                                    id="Complication_count"
                                    name="Complication_count"
                                    value={input.Complication_count}
                                    onChange={handleChange}
                                    className={inputClasses}
                                    min="0" step="1"
                                    required
                                />
                            </div>

                            {/* Injury_Type */}
                            <div>
                                <label htmlFor="Injury_Type" className={labelClasses}>Current Injury Type</label>
                                <select
                                    id="Injury_Type"
                                    name="Injury_Type"
                                    value={input.Injury_Type}
                                    onChange={handleChange}
                                    className={inputClasses}
                                    required
                                >
                                    {INJURY_OPTIONS.map(option => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Previous_injury (Checkbox style) */}
                            <div className="md:col-span-2 flex items-center pt-2">
                                <input
                                    type="checkbox"
                                    id="Previous_injury"
                                    name="Previous_injury"
                                    checked={input.Previous_injury === 1}
                                    onChange={(e) => setInput(prev => ({...prev, Previous_injury: e.target.checked ? 1 : 0}))}
                                    className="h-5 w-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                                />
                                <label htmlFor="Previous_injury" className="ml-3 text-sm font-medium text-gray-700">
                                    Patient has a history of Previous Injury
                                </label>
                            </div>

                        </div>

                        {/* Submit Button */}
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 transition-all shadow-lg flex items-center justify-center disabled:opacity-50"
                        >
                            {loading ? (
                                <>
                                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Predicting...
                                </>
                            ) : (
                                <>
                                    <Clock className="w-5 h-5 mr-2" /> Predict Median Recovery Time
                                </>
                            )}
                        </button>
                    </form>

                    {/* --- Prediction Result --- */}
                    {prediction !== null && (
                        <div className="mt-8 bg-green-50 border-l-4 border-green-500 p-6 rounded-xl shadow-md transition-opacity duration-500">
                            <div className="flex items-center space-x-3">
                                <TrendingUp className="w-8 h-8 text-green-700"/>
                                <h3 className="text-xl font-bold text-green-800">Prediction Result</h3>
                            </div>
                            <p className="mt-4 text-3xl font-extrabold text-gray-900">
                                <span className="text-green-600">{prediction}</span> Days
                            </p>
                            <p className="text-sm text-gray-600 mt-1">
                                This is the estimated time for 50% probability of full recovery.
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default RecoveryPredictor;
