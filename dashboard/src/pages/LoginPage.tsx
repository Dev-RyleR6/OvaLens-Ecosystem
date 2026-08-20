import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

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
        setErrorMessage(`Too many failed attempts. Account locked for ${LOCKOUT_SECONDS}s.`);
      } else {
        setErrorMessage(
          err.response?.data?.detail || 'Invalid email or password. Please try again.'
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const fillCredentials = (role: 'admin' | 'operator') => {
    setErrorMessage(null);
    if (role === 'admin') {
      setEmail('admin@foundationu.com');
      setPassword('admin123');
    } else {
      setEmail('operator@foundationu.com');
      setPassword('operator123');
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col justify-center items-center px-4 py-12 font-sans text-[#0F172A]">
      <div className="w-full max-w-sm">
        
        {/* University / Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#800000] text-white font-bold text-lg mb-3 shadow-xs">
            FU
          </div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">OvaLens Hatchery</h1>
          <p className="text-xs text-slate-500 mt-1">Foundation University Duck Egg Management</p>
        </div>

        {/* Login Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          
          {/* Demo Accounts Quick-Select */}
          <div className="mb-5 pb-4 border-b border-slate-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-700">Test Accounts</span>
              <span className="text-[11px] text-slate-400">Click to fill</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => fillCredentials('admin')}
                className="py-1.5 px-3 text-xs font-medium rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 hover:border-slate-300 text-slate-700 transition-colors text-center cursor-pointer"
              >
                Admin
              </button>
              <button
                type="button"
                onClick={() => fillCredentials('operator')}
                className="py-1.5 px-3 text-xs font-medium rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 hover:border-slate-300 text-slate-700 transition-colors text-center cursor-pointer"
              >
                Operator
              </button>
            </div>
          </div>

          {/* Error Message */}
          {errorMessage && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Lockout Notice */}
          {lockoutTimer > 0 && (
            <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 text-center">
              Account locked. Please wait <strong>{lockoutTimer}s</strong>.
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">
                Email address
              </label>
              <input
                type="email"
                required
                disabled={lockoutTimer > 0 || isLoading}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@foundationu.com"
                autoComplete="email"
                className="w-full h-10 px-3 text-sm bg-white border border-slate-300 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/10 transition-colors disabled:bg-slate-50 disabled:text-slate-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  disabled={lockoutTimer > 0 || isLoading}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className="w-full h-10 pl-3 pr-10 text-sm bg-white border border-slate-300 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/10 transition-colors disabled:bg-slate-50 disabled:text-slate-500"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between pt-0.5">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 accent-[#800000] rounded cursor-pointer"
                />
                <span className="text-xs text-slate-600">Remember me</span>
              </label>
            </div>

            <button
              type="submit"
              disabled={lockoutTimer > 0 || isLoading}
              className="w-full h-10 bg-[#800000] hover:bg-[#660000] active:bg-[#4d0000] text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer mt-2"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                'Sign In'
              )}
            </button>
          </form>
        </div>

        {/* Institutional Footer */}
        <div className="mt-6 text-center text-xs text-slate-400">
          Foundation University • Team DevIn
        </div>

      </div>
    </div>
  );
};

export default LoginPage;
