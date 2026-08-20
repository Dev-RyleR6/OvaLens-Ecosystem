import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Eye,
  EyeOff,
  AlertCircle,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  UserCheck,
  Loader2,
  Sparkles
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const sanitize = (val: string): string => {
  return val.replace(/<[^>]*>?/gm, '').trim();
};

const isValidEmail = (email: string): boolean => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
};

const MAX_FAILED_ATTEMPTS = 5;
const LOCKOUT_SECONDS = 30;

type AuthStep = 'idle' | 'verifying' | 'syncing' | 'success';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();

  const [email, setEmail] = useState(() => localStorage.getItem('ovalens_remembered_email') || '');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [authStep, setAuthStep] = useState<AuthStep>('idle');
  const [isExiting, setIsExiting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [hasErrorShake, setHasErrorShake] = useState(false);

  const [selectedRole, setSelectedRole] = useState<'admin' | 'operator' | null>(null);

  const [failedAttempts, setFailedAttempts] = useState(() => {
    const saved = sessionStorage.getItem('ovalens_attempts');
    return saved ? parseInt(saved, 10) : 0;
  });
  const [lockoutTimer, setLockoutTimer] = useState<number>(0);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && authStep === 'idle') {
      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, authStep, navigate, location]);

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
    if (lockoutTimer > 0 || authStep !== 'idle') return;

    setErrorMessage(null);
    setHasErrorShake(false);

    const cleanEmail = sanitize(email).toLowerCase();
    const cleanPassword = password.trim();

    if (!cleanEmail || !isValidEmail(cleanEmail)) {
      setErrorMessage('Please enter a valid email address.');
      triggerErrorShake();
      return;
    }

    if (!cleanPassword) {
      setErrorMessage('Please enter your password.');
      triggerErrorShake();
      return;
    }

    // Step 1: Verifying credentials
    setAuthStep('verifying');

    try {
      // Small intentional delay for smooth verification feedback
      await new Promise((res) => setTimeout(res, 400));
      setAuthStep('syncing');

      await login({ email: cleanEmail, password: cleanPassword });

      if (rememberMe) {
        localStorage.setItem('ovalens_remembered_email', cleanEmail);
      } else {
        localStorage.removeItem('ovalens_remembered_email');
      }

      setFailedAttempts(0);
      sessionStorage.removeItem('ovalens_attempts');

      // Step 3: Success state with smooth transition
      setAuthStep('success');
      await new Promise((res) => setTimeout(res, 500));

      // Trigger smooth exit fade
      setIsExiting(true);
      await new Promise((res) => setTimeout(res, 350));

      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch (err: any) {
      const attempts = failedAttempts + 1;
      setFailedAttempts(attempts);
      sessionStorage.setItem('ovalens_attempts', attempts.toString());

      setAuthStep('idle');
      triggerErrorShake();

      if (attempts >= MAX_FAILED_ATTEMPTS) {
        setLockoutTimer(LOCKOUT_SECONDS);
        setErrorMessage(`Too many failed attempts. Account locked for ${LOCKOUT_SECONDS}s.`);
      } else {
        setErrorMessage(
          err.response?.data?.detail || 'Invalid email or password. Please check your credentials.'
        );
      }
    }
  };

  const triggerErrorShake = () => {
    setHasErrorShake(true);
    setTimeout(() => setHasErrorShake(false), 400);
  };

  const selectRoleAccount = (role: 'admin' | 'operator') => {
    if (authStep !== 'idle') return;
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
    <div className="min-h-screen bg-[#0F172A] text-slate-100 flex flex-col justify-center items-center p-4 font-sans selection:bg-[#800000] selection:text-white relative overflow-hidden">
      
      {/* Background Accent Grid */}
      <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] opacity-40 pointer-events-none" />

      <div
        className={`w-full max-w-md relative z-10 transition-all duration-400 ease-out ${
          isExiting ? 'opacity-0 scale-95 translate-y-2' : 'opacity-100 scale-100 translate-y-0'
        }`}
      >
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#800000] to-[#5C0000] flex items-center justify-center text-white font-black text-2xl shadow-xl mb-3 ring-4 ring-[#800000]/25 transition-transform hover:scale-105">
            FU
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            OvaLens
            <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#800000]/20 text-red-300 border border-[#800000]/40">
              v2.0
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">Hatchery Candling & Edge Analytics</p>
        </div>

        {/* Main Authentication Card */}
        <div
          className={`bg-[#1E293B] border border-[#334155] rounded-2xl shadow-2xl overflow-hidden transition-all duration-200 ${
            hasErrorShake ? 'animate-shake' : ''
          }`}
        >
          {/* Animated Scanning Progress Bar during Authentication */}
          {authStep !== 'idle' && (
            <div className="h-1 w-full bg-slate-800 overflow-hidden relative">
              <div
                className={`h-full transition-all duration-300 ${
                  authStep === 'success'
                    ? 'w-full bg-[#357a38]'
                    : 'w-1/2 bg-[#800000] animate-scan-line'
                }`}
              />
            </div>
          )}

          <div className="p-7 sm:p-8">
            {/* Quick Role Select / Onboarding */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2.5">
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Credentials
                </label>
                <span className="text-[10px] text-slate-500 font-medium">Quick switch</span>
              </div>

              <div className="grid grid-cols-2 gap-2.5">
                {/* Admin Option */}
                <button
                  type="button"
                  disabled={authStep !== 'idle'}
                  onClick={() => selectRoleAccount('admin')}
                  className={`p-3 rounded-xl border text-left transition-all duration-150 flex flex-col justify-between cursor-pointer group ${
                    selectedRole === 'admin' || email === 'admin@foundationu.com'
                      ? 'bg-[#800000]/20 border-[#800000] text-white shadow-sm ring-1 ring-[#800000]/40'
                      : 'bg-[#0F172A]/60 border-[#334155] text-slate-400 hover:border-slate-500 hover:text-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between w-full mb-1">
                    <ShieldCheck
                      className={`w-4 h-4 transition-colors ${
                        selectedRole === 'admin' || email === 'admin@foundationu.com'
                          ? 'text-red-400'
                          : 'text-slate-500 group-hover:text-slate-300'
                      }`}
                    />
                    {(selectedRole === 'admin' || email === 'admin@foundationu.com') && (
                      <CheckCircle2 className="w-3.5 h-3.5 text-red-400" />
                    )}
                  </div>
                  <div>
                    <span className="font-semibold text-xs text-white block">Administrator</span>
                    <span className="text-[10px] text-slate-400">Full Access</span>
                  </div>
                </button>

                {/* Operator Option */}
                <button
                  type="button"
                  disabled={authStep !== 'idle'}
                  onClick={() => selectRoleAccount('operator')}
                  className={`p-3 rounded-xl border text-left transition-all duration-150 flex flex-col justify-between cursor-pointer group ${
                    selectedRole === 'operator' || email === 'operator@foundationu.com'
                      ? 'bg-[#357a38]/20 border-[#357a38] text-white shadow-sm ring-1 ring-[#357a38]/40'
                      : 'bg-[#0F172A]/60 border-[#334155] text-slate-400 hover:border-slate-500 hover:text-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between w-full mb-1">
                    <UserCheck
                      className={`w-4 h-4 transition-colors ${
                        selectedRole === 'operator' || email === 'operator@foundationu.com'
                          ? 'text-emerald-400'
                          : 'text-slate-500 group-hover:text-slate-300'
                      }`}
                    />
                    {(selectedRole === 'operator' || email === 'operator@foundationu.com') && (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    )}
                  </div>
                  <div>
                    <span className="font-semibold text-xs text-white block">Operator</span>
                    <span className="text-[10px] text-slate-400">Conveyor Station</span>
                  </div>
                </button>
              </div>
            </div>

            {/* Error Message */}
            {errorMessage && (
              <div className="mb-5 p-3.5 bg-red-950/60 border border-red-900/80 rounded-xl text-xs text-red-200 flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <span className="leading-snug">{errorMessage}</span>
              </div>
            )}

            {/* Security Lockout Notice */}
            {lockoutTimer > 0 && (
              <div className="mb-5 p-3.5 bg-amber-950/60 border border-amber-900/80 rounded-xl text-xs text-amber-200 text-center">
                Security lockout active. Try again in{' '}
                <strong className="font-mono text-amber-300">{lockoutTimer}s</strong>.
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  disabled={lockoutTimer > 0 || authStep !== 'idle'}
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setSelectedRole(null);
                  }}
                  placeholder="name@foundationu.com"
                  autoComplete="email"
                  className="w-full h-10 px-3.5 text-xs bg-[#0F172A] border border-[#334155] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/20 transition-all disabled:opacity-50 font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    disabled={lockoutTimer > 0 || authStep !== 'idle'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete="current-password"
                    className="w-full h-10 pl-3.5 pr-10 text-xs bg-[#0F172A] border border-[#334155] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-[#800000] focus:ring-2 focus:ring-[#800000]/20 transition-all disabled:opacity-50 font-medium"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 cursor-pointer p-1 transition-colors"
                    tabIndex={-1}
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-3.5 h-3.5 accent-[#800000] bg-slate-900 border-slate-700 rounded cursor-pointer"
                  />
                  <span className="text-xs font-medium text-slate-400 hover:text-slate-300">
                    Remember me
                  </span>
                </label>

                <span className="text-[10px] text-slate-500 font-mono">JWT Bearer</span>
              </div>

              {/* Sign In Button with Dynamic Multi-Stage Transition */}
              <button
                type="submit"
                disabled={lockoutTimer > 0 || authStep !== 'idle'}
                className={`w-full h-11 mt-2 text-xs font-bold rounded-xl transition-all duration-200 cursor-pointer disabled:opacity-60 flex items-center justify-center gap-2 shadow-lg btn-press ${
                  authStep === 'success'
                    ? 'bg-[#357a38] text-white shadow-emerald-900/30'
                    : 'bg-[#800000] hover:bg-[#6b0000] active:bg-[#520000] text-white shadow-red-950/40'
                }`}
              >
                {authStep === 'verifying' && (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-red-200" />
                    <span>Verifying Credentials...</span>
                  </>
                )}

                {authStep === 'syncing' && (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-red-200" />
                    <span>Synchronizing Session...</span>
                  </>
                )}

                {authStep === 'success' && (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-white animate-bounce" />
                    <span>Access Granted — Opening...</span>
                  </>
                )}

                {authStep === 'idle' && (
                  <>
                    <span>Sign In to Hatchery</span>
                    <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 text-center flex flex-col items-center gap-1">
          <p className="text-[11px] text-slate-500 font-medium">
            Foundation University Capstone Project
          </p>
          <div className="flex items-center gap-1.5 text-[10px] font-semibold text-slate-600 uppercase tracking-widest">
            <Sparkles className="w-2.5 h-2.5 text-[#800000]" />
            <span>Team DevIn</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
