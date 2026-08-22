import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Eye, EyeOff, AlertCircle, Check, Loader2, Shield, User } from 'lucide-react';
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
  const [selectedRole, setSelectedRole] = useState<'admin' | 'operator' | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [shakeError, setShakeError] = useState(false);

  const [failedAttempts, setFailedAttempts] = useState(() => {
    const saved = sessionStorage.getItem('ovalens_attempts');
    return saved ? parseInt(saved, 10) : 0;
  });
  const [lockoutTimer, setLockoutTimer] = useState<number>(0);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !isLoading && !isSuccess) {
      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, isLoading, isSuccess, navigate, location]);

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

  const triggerShake = () => {
    setShakeError(true);
    setTimeout(() => setShakeError(false), 350);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (lockoutTimer > 0 || isLoading || isSuccess) return;

    setErrorMessage(null);

    const cleanEmail = sanitize(email).toLowerCase();
    const cleanPassword = password.trim();

    if (!cleanEmail || !isValidEmail(cleanEmail)) {
      setErrorMessage('Please enter a valid email address.');
      triggerShake();
      return;
    }

    if (!cleanPassword) {
      setErrorMessage('Please enter your password.');
      triggerShake();
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

      // Success feedback & smooth exit transition
      setIsSuccess(true);
      await new Promise((res) => setTimeout(res, 400));
      setIsExiting(true);
      await new Promise((res) => setTimeout(res, 250));

      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch (err: any) {
      const attempts = failedAttempts + 1;
      setFailedAttempts(attempts);
      sessionStorage.setItem('ovalens_attempts', attempts.toString());
      triggerShake();

      if (attempts >= MAX_FAILED_ATTEMPTS) {
        setLockoutTimer(LOCKOUT_SECONDS);
        setErrorMessage(`Too many failed attempts. Account locked for ${LOCKOUT_SECONDS}s.`);
      } else if (!err.response) {
        setErrorMessage('Cannot connect to OvaLens Backend API (http://localhost:8000). Please check if python uvicorn server is running.');
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
    setSelectedRole(role);
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
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col justify-center items-center px-4 py-12 font-sans text-slate-900 selection:bg-[#800000] selection:text-white">
      <div
        className={`w-full max-w-sm transition-all duration-300 ease-out ${
          isExiting ? 'opacity-0 scale-[0.97] translate-y-1' : 'opacity-100 scale-100 translate-y-0'
        }`}
      >
        {/* University Header */}
        <div className="text-center mb-7">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#800000] text-white font-bold text-lg mb-3 shadow-sm ring-1 ring-[#800000]/10 transition-transform duration-200 hover:scale-105">
            FU
          </div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            OvaLens Hatchery System
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Foundation University Duck Egg Management
          </p>
        </div>

        {/* Card Container */}
        <div
          className={`bg-white border border-slate-200/90 rounded-2xl p-6 sm:p-7 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] transition-all duration-200 ${
            shakeError ? 'animate-shake' : ''
          }`}
        >
          {/* Quick Role Fillers */}
          <div className="mb-5 pb-4 border-b border-slate-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                Demo Accounts
              </span>
              <span className="text-[11px] text-slate-400">Click to fill</span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => fillCredentials('admin')}
                className={`py-2 px-3 text-xs font-medium rounded-xl border text-left transition-all duration-150 flex items-center justify-between cursor-pointer ${
                  selectedRole === 'admin' || email === 'admin@foundationu.com'
                    ? 'border-[#800000]/30 bg-[#800000]/5 text-[#800000] ring-1 ring-[#800000]/10 shadow-xs'
                    : 'border-slate-200 bg-slate-50/70 hover:bg-slate-100/80 text-slate-700 hover:border-slate-300'
                }`}
              >
                <span className="flex items-center gap-1.5 font-semibold">
                  <Shield className="w-3.5 h-3.5 opacity-70" />
                  Admin
                </span>
                {(selectedRole === 'admin' || email === 'admin@foundationu.com') && (
                  <Check className="w-3.5 h-3.5 text-[#800000]" />
                )}
              </button>

              <button
                type="button"
                onClick={() => fillCredentials('operator')}
                className={`py-2 px-3 text-xs font-medium rounded-xl border text-left transition-all duration-150 flex items-center justify-between cursor-pointer ${
                  selectedRole === 'operator' || email === 'operator@foundationu.com'
                    ? 'border-[#357a38]/30 bg-[#357a38]/5 text-[#357a38] ring-1 ring-[#357a38]/10 shadow-xs'
                    : 'border-slate-200 bg-slate-50/70 hover:bg-slate-100/80 text-slate-700 hover:border-slate-300'
                }`}
              >
                <span className="flex items-center gap-1.5 font-semibold">
                  <User className="w-3.5 h-3.5 opacity-70" />
                  Operator
                </span>
                {(selectedRole === 'operator' || email === 'operator@foundationu.com') && (
                  <Check className="w-3.5 h-3.5 text-[#357a38]" />
                )}
              </button>
            </div>
          </div>

          {/* Error Message */}
          {errorMessage && (
            <div className="mb-4 p-3 bg-red-50/90 border border-red-200 rounded-xl text-xs text-red-700 flex items-start gap-2.5 transition-all animate-in fade-in-50 duration-150">
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
              <span className="leading-snug">{errorMessage}</span>
            </div>
          )}

          {/* Lockout Notice */}
          {lockoutTimer > 0 && (
            <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 text-center">
              Account locked. Please wait <strong>{lockoutTimer}s</strong>.
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">
                Email address
              </label>
              <input
                type="email"
                required
                disabled={lockoutTimer > 0 || isLoading || isSuccess}
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setSelectedRole(null);
                }}
                placeholder="name@foundationu.com"
                autoComplete="email"
                className="w-full h-10 px-3.5 text-sm bg-white border border-slate-300 rounded-xl text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-[#800000] focus:ring-4 focus:ring-[#800000]/8 transition-all duration-150 disabled:bg-slate-50 disabled:text-slate-400"
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
                  disabled={lockoutTimer > 0 || isLoading || isSuccess}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className="w-full h-10 pl-3.5 pr-10 text-sm bg-white border border-slate-300 rounded-xl text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-[#800000] focus:ring-4 focus:ring-[#800000]/8 transition-all duration-150 disabled:bg-slate-50 disabled:text-slate-400"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 p-1.5 rounded-lg transition-colors cursor-pointer"
                  tabIndex={-1}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between pt-0.5">
              <label className="flex items-center gap-2 cursor-pointer select-none group">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 accent-[#800000] rounded cursor-pointer transition-colors"
                />
                <span className="text-xs text-slate-600 group-hover:text-slate-900 transition-colors">
                  Remember me
                </span>
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={lockoutTimer > 0 || isLoading || isSuccess}
              className={`w-full h-10 text-white text-sm font-semibold rounded-xl transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer mt-2 shadow-xs active:scale-[0.99] disabled:opacity-60 ${
                isSuccess
                  ? 'bg-[#357a38] shadow-emerald-700/20'
                  : 'bg-[#800000] hover:bg-[#6b0000] active:bg-[#520000] shadow-red-950/20'
              }`}
            >
              {isLoading && (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-white/90" />
                  <span>Signing in...</span>
                </>
              )}

              {isSuccess && (
                <>
                  <Check className="w-4 h-4 text-white" />
                  <span>Signed in</span>
                </>
              )}

              {!isLoading && !isSuccess && <span>Sign In</span>}
            </button>
          </form>
        </div>

        {/* Footer */}
        <div className="mt-6 text-center text-xs text-slate-400">
          Foundation University • Team DevIn
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
