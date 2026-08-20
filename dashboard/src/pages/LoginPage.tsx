import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Lock,
  Mail,
  Eye,
  EyeOff,
  ShieldCheck,
  Building,
  CheckCircle2,
  AlertCircle,
  KeyRound,
  UserCheck,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();

  const [email, setEmail] = useState('admin@foundationu.com');
  const [password, setPassword] = useState('admin123');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // If already authenticated, redirect to overview
  React.useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsLoading(true);

    try {
      await login({ email, password });
      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch (err: any) {
      setErrorMessage(
        err.response?.data?.detail || 'Authentication failed. Please check your email and password.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFill = (role: 'ADMIN' | 'OPERATOR') => {
    if (role === 'ADMIN') {
      setEmail('admin@foundationu.com');
      setPassword('admin123');
    } else {
      setEmail('operator@foundationu.com');
      setPassword('operator123');
    }
  };

  return (
    <div className="min-h-screen w-screen bg-[#F8FAFC] flex flex-col justify-center items-center p-4 font-sans text-[#0F172A]">
      {/* Container Box */}
      <div className="w-full max-w-md bg-white border border-[#E2E8F0] rounded-2xl shadow-sm overflow-hidden space-y-6 p-8">
        {/* Header Branding */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#800000] text-white shadow-xs">
            <ShieldCheck className="w-6 h-6" />
          </div>

          <div>
            <span className="text-[10px] font-extrabold tracking-widest text-[#800000] uppercase block">
              Foundation University
            </span>
            <h1 className="text-xl font-black text-[#0F172A] tracking-tight">
              OvaLens Hatchery System
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Automated Duck Egg Candling & Sorting Ecosystem
            </p>
          </div>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs font-semibold text-red-800 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 block">
              Institutional Email
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="operator@foundationu.com"
                className="w-full h-10 pl-9 pr-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-[#800000] focus:ring-1 focus:ring-[#800000] transition-colors"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 block">
              Security Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full h-10 pl-9 pr-10 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-[#800000] focus:ring-1 focus:ring-[#800000] transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full h-10 bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-bold rounded-lg shadow-xs transition-colors cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <KeyRound className="w-4 h-4" />
            <span>{isLoading ? 'Verifying Credentials...' : 'Sign In to Hatchery Control'}</span>
          </button>
        </form>

        {/* Quick Demo Credentials Fill for Capstone Defense */}
        <div className="pt-4 border-t border-slate-100 space-y-2.5">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block text-center">
            Defense Demonstration Accounts
          </span>

          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleQuickFill('ADMIN')}
              className="p-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-left transition-colors cursor-pointer group"
            >
              <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-800 group-hover:text-[#800000]">
                <UserCheck className="w-3.5 h-3.5 text-[#800000]" />
                <span>Admin / Researcher</span>
              </div>
              <span className="text-[10px] text-slate-500 block font-mono">admin@foundationu.com</span>
            </button>

            <button
              type="button"
              onClick={() => handleQuickFill('OPERATOR')}
              className="p-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-left transition-colors cursor-pointer group"
            >
              <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-800 group-hover:text-[#800000]">
                <UserCheck className="w-3.5 h-3.5 text-emerald-700" />
                <span>Shift Operator</span>
              </div>
              <span className="text-[10px] text-slate-500 block font-mono">operator@foundationu.com</span>
            </button>
          </div>
        </div>

        {/* Institutional Footer */}
        <div className="pt-2 text-center text-[10px] text-slate-400">
          Dumaguete City, Negros Oriental • Secured with JWT & Bcrypt
        </div>
      </div>
    </div>
  );
};
