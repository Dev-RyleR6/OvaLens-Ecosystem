import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

// Input sanitizer: strips dangerous script/HTML tags and trims whitespace
const sanitize = (val: string): string => {
  return val.replace(/<[^>]*>?/gm, '').trim();
};

const isValidEmail = (email: string): boolean => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
};

const MAX_FAILED_ATTEMPTS = 5;
const LOCKOUT_SECONDS = 30;

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();

  const [email, setEmail] = useState(() => localStorage.getItem('ovalens_remembered_email') || '');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Rate Limiting / Lockout State
  const [failedAttempts, setFailedAttempts] = useState(() => {
    const saved = sessionStorage.getItem('ovalens_attempts');
    return saved ? parseInt(saved, 10) : 0;
  });
  const [lockoutTimer, setLockoutTimer] = useState<number>(0);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  // Lockout countdown
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (lockoutTimer > 0) {
      timer = setInterval(() => {
        setLockoutTimer((prev) => {
          if (prev <= 1) {
            setFailedAttempts(0);
            sessionStorage.removeItem('ovalens_attempts');
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [lockoutTimer]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (lockoutTimer > 0 || isLoading) return;

    setErrorMessage(null);

    // Silent input sanitization
    const cleanEmail = sanitize(email).toLowerCase();
    const cleanPassword = password.trim();

    if (!cleanEmail || !isValidEmail(cleanEmail)) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }

    if (!cleanPassword) {
      setErrorMessage('Please enter your password.');
      return;
    }

    setIsLoading(true);

    try {
      await login({ email: cleanEmail, password: cleanPassword });

      if (rememberMe) {
        localStorage.setItem('ovalens_remembered_email', cleanEmail);
      } else {
        localStorage.removeItem('ovalens_remembered_email');
      }

      setFailedAttempts(0);
      sessionStorage.removeItem('ovalens_attempts');

      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch (err: any) {
      const attempts = failedAttempts + 1;
      setFailedAttempts(attempts);
      sessionStorage.setItem('ovalens_attempts', attempts.toString());

      if (attempts >= MAX_FAILED_ATTEMPTS) {
        setLockoutTimer(LOCKOUT_SECONDS);
        setErrorMessage(`Too many failed attempts. Please try again in ${LOCKOUT_SECONDS} seconds.`);
      } else {
        setErrorMessage(
          err.response?.data?.detail || 'Invalid email or password.'
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const setDemoAccount = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-sm bg-white border border-[#E2E8F0] rounded-xl shadow-xs p-7 space-y-6">
        {/* Simple Brand Header */}
        <div className="text-center space-y-1">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-[#800000] text-white font-bold text-sm mb-2 shadow-xs">
            FU
          </div>
          <h1 className="text-lg font-bold text-[#0F172A]">OvaLens Hatchery</h1>
          <p className="text-xs text-slate-500">Sign in to your account</p>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs font-medium text-red-800 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
            <span className="leading-snug">{errorMessage}</span>
          </div>
        )}

        {/* Lockout Notice */}
        {lockoutTimer > 0 && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs font-medium text-amber-900 text-center">
            Account temporarily locked. Retry in <strong className="font-mono">{lockoutTimer}s</strong>.
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-700">Email</label>
            <input
              type="email"
              required
              disabled={lockoutTimer > 0 || isLoading}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@foundationu.com"
              autoComplete="email"
              className="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-[#800000] focus:ring-1 focus:ring-[#800000] disabled:bg-slate-50"
            />
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-700">Password</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                disabled={lockoutTimer > 0 || isLoading}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                className="w-full h-9 pl-3 pr-9 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-[#800000] focus:ring-1 focus:ring-[#800000] disabled:bg-slate-50"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between text-xs text-slate-600">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-3.5 h-3.5 accent-[#800000] rounded"
              />
              <span>Remember me</span>
            </label>
          </div>

          <button
            type="submit"
            disabled={lockoutTimer > 0 || isLoading}
            className="w-full h-9 bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-bold rounded-lg shadow-xs transition-colors cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <span>Sign In</span>
            )}
          </button>
        </form>

        {/* Subtle Demo Credentials */}
        <div className="pt-3 border-t border-slate-100 text-center">
          <p className="text-[11px] text-slate-400 mb-1.5">Demo accounts:</p>
          <div className="flex justify-center gap-2 text-xs">
            <button
              type="button"
              onClick={() => setDemoAccount('admin@foundationu.com', 'admin123')}
              className="text-[#800000] hover:underline font-medium cursor-pointer"
            >
              Admin
            </button>
            <span className="text-slate-300">•</span>
            <button
              type="button"
              onClick={() => setDemoAccount('operator@foundationu.com', 'operator123')}
              className="text-slate-600 hover:underline font-medium cursor-pointer"
            >
              Operator
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
