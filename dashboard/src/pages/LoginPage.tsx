import React, { useState, useEffect, useCallback } from 'react';
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
  Clock,
  ShieldAlert,
  HelpCircle,
  XCircle,
  Radio,
  Server,
  Zap,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

// Input sanitizer: strips script/HTML tags and trims whitespace
const sanitizeInput = (input: string): string => {
  return input.replace(/<[^>]*>?/gm, '').trim();
};

// RFC 5322 standard email validation regex
const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return emailRegex.test(email);
};

// Subtle Web Audio acoustic feedback for UI interactions
const playUiClick = () => {
  try {
    const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(640, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.04, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.04);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.04);
  } catch {
    // Audio Context might require prior interaction
  }
};

const MAX_FAILED_ATTEMPTS = 5;
const LOCKOUT_DURATION_SECONDS = 30;

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();

  // Form State
  const [email, setEmail] = useState(() => localStorage.getItem('ovalens_remembered_email') || 'admin@foundationu.com');
  const [password, setPassword] = useState('admin123');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [capsLockActive, setCapsLockActive] = useState(false);

  // Security & Rate Limiting State
  const [failedAttempts, setFailedAttempts] = useState(() => {
    const saved = sessionStorage.getItem('ovalens_failed_attempts');
    return saved ? parseInt(saved, 10) : 0;
  });
  const [lockoutTimer, setLockoutTimer] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  // Lockout Countdown Timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (lockoutTimer > 0) {
      interval = setInterval(() => {
        setLockoutTimer((prev) => {
          if (prev <= 1) {
            setFailedAttempts(0);
            sessionStorage.removeItem('ovalens_failed_attempts');
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [lockoutTimer]);

  // Keyboard Caps Lock Detection
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.getModifierState) {
      setCapsLockActive(e.getModifierState('CapsLock'));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (lockoutTimer > 0) return;

    setErrorMessage(null);

    // 1. Client-Side Input Sanitization
    const sanitizedEmail = sanitizeInput(email).toLowerCase();
    const sanitizedPassword = password.trim();

    // 2. Strict Format Validations
    if (!isValidEmail(sanitizedEmail)) {
      setErrorMessage('Please enter a valid institutional email address.');
      return;
    }

    if (sanitizedPassword.length < 6) {
      setErrorMessage('Security password must contain at least 6 characters.');
      return;
    }

    setIsLoading(true);

    try {
      await login({ email: sanitizedEmail, password: sanitizedPassword });
      
      // Save Remember Me preference
      if (rememberMe) {
        localStorage.setItem('ovalens_remembered_email', sanitizedEmail);
      } else {
        localStorage.removeItem('ovalens_remembered_email');
      }

      // Reset Security Counters on Success
      setFailedAttempts(0);
      sessionStorage.removeItem('ovalens_failed_attempts');

      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch (err: any) {
      const newAttempts = failedAttempts + 1;
      setFailedAttempts(newAttempts);
      sessionStorage.setItem('ovalens_failed_attempts', newAttempts.toString());

      if (newAttempts >= MAX_FAILED_ATTEMPTS) {
        setLockoutTimer(LOCKOUT_DURATION_SECONDS);
        setErrorMessage(
          `Security Alert: Maximum login attempts exceeded. Access locked for ${LOCKOUT_DURATION_SECONDS} seconds.`
        );
      } else {
        const remaining = MAX_FAILED_ATTEMPTS - newAttempts;
        setErrorMessage(
          `Invalid credentials. ${remaining} attempt${remaining > 1 ? 's' : ''} remaining before temporary lockout.`
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFill = useCallback((role: 'ADMIN' | 'OPERATOR') => {
    playUiClick();
    setErrorMessage(null);
    if (role === 'ADMIN') {
      setEmail('admin@foundationu.com');
      setPassword('admin123');
    } else {
      setEmail('operator@foundationu.com');
      setPassword('operator123');
    }
  }, []);

  return (
    <div className="min-h-screen w-screen bg-[#F8FAFC] flex flex-col justify-center items-center p-4 font-sans text-[#0F172A] relative overflow-hidden">
      {/* Top University Stripe Accent */}
      <div className="absolute top-0 left-0 right-0 h-1.5 bg-[#800000]" />

      {/* Main Dual-Panel Auth Card */}
      <div className="w-full max-w-4xl bg-white border border-[#E2E8F0] rounded-2xl shadow-sm overflow-hidden grid grid-cols-1 md:grid-cols-12">
        {/* Left / Main Login Form Pane (7 Cols) */}
        <div className="md:col-span-7 p-6 sm:p-8 space-y-6 flex flex-col justify-between">
          {/* Header Branding */}
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#800000] text-white flex items-center justify-center font-black text-sm tracking-tight shadow-xs flex-shrink-0">
                FU
              </div>
              <div>
                <span className="text-[10px] font-extrabold tracking-widest text-[#800000] uppercase block">
                  Foundation University
                </span>
                <h1 className="text-lg font-black text-[#0F172A] tracking-tight">
                  OvaLens Hatchery System
                </h1>
              </div>
            </div>
            <p className="text-xs text-slate-500 pt-1">
              Automated Duck Egg Candling & Sorting Access Control
            </p>
          </div>

          {/* Lockout Banner */}
          {lockoutTimer > 0 ? (
            <div className="p-4 bg-red-50 border border-red-300 rounded-xl space-y-2 text-xs">
              <div className="flex items-center gap-2 font-bold text-red-900">
                <ShieldAlert className="w-5 h-5 text-red-700 animate-pulse flex-shrink-0" />
                <span>Temporary Security Lockout Active</span>
              </div>
              <p className="text-red-800 text-[11px]">
                Brute-force protection enabled. Please wait until the cooldown timer expires:
              </p>
              <div className="flex items-center justify-between font-mono font-bold text-red-900 bg-red-100/80 px-3 py-1.5 rounded-lg">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-red-700" />
                  Cooldown Remaining:
                </span>
                <span className="text-sm">{lockoutTimer}s</span>
              </div>
            </div>
          ) : (
            /* Error Banner */
            errorMessage && (
              <div className="p-3.5 bg-amber-50 border border-amber-300 rounded-xl text-xs font-semibold text-amber-950 flex items-start gap-2.5 shadow-2xs">
                <AlertCircle className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <span>{errorMessage}</span>
                </div>
                <button
                  onClick={() => setErrorMessage(null)}
                  className="text-amber-700 hover:text-amber-900 p-0.5 cursor-pointer"
                >
                  <XCircle className="w-3.5 h-3.5" />
                </button>
              </div>
            )
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 block">
                Institutional Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  disabled={lockoutTimer > 0 || isLoading}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="operator@foundationu.com"
                  autoComplete="email"
                  className="w-full h-10 pl-9 pr-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-[#800000] focus:ring-1 focus:ring-[#800000] transition-colors disabled:bg-slate-100 disabled:cursor-not-allowed"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-700 block">
                  Password
                </label>
                {capsLockActive && (
                  <span className="text-[10px] font-bold text-amber-800 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded flex items-center gap-1">
                    ⚠️ Caps Lock is ON
                  </span>
                )}
              </div>

              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  disabled={lockoutTimer > 0 || isLoading}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={handleKeyDown}
                  onKeyUp={handleKeyDown}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className="w-full h-10 pl-9 pr-10 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:border-[#800000] focus:ring-1 focus:ring-[#800000] transition-colors disabled:bg-slate-100 disabled:cursor-not-allowed"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 cursor-pointer"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Remember Me & Security Meta */}
            <div className="flex items-center justify-between text-xs pt-1">
              <label className="flex items-center gap-2 text-slate-600 font-medium cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-3.5 h-3.5 accent-[#800000] rounded cursor-pointer"
                />
                <span>Remember email</span>
              </label>

              <span className="text-[11px] text-slate-400 font-medium">
                Attempts: <strong>{failedAttempts}</strong> / {MAX_FAILED_ATTEMPTS}
              </span>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={lockoutTimer > 0 || isLoading}
              className="w-full h-10 bg-[#800000] hover:bg-[#6B0000] active:scale-[0.99] text-white text-xs font-bold rounded-lg shadow-xs transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Verifying Authorization...</span>
                </>
              ) : (
                <>
                  <KeyRound className="w-4 h-4" />
                  <span>Authenticate & Launch Console</span>
                </>
              )}
            </button>
          </form>

          {/* Footer Meta */}
          <div className="text-[11px] text-slate-400 text-center pt-2 border-t border-slate-100">
            Dumaguete City, Negros Oriental • Encrypted Hatchery Control
          </div>
        </div>

        {/* Right Info / Security Telemetry Pane (5 Cols) */}
        <div className="md:col-span-5 bg-slate-50 border-t md:border-t-0 md:border-l border-slate-200 p-6 sm:p-8 space-y-6 flex flex-col justify-between">
          {/* Section: Capstone Defense Presets */}
          <div className="space-y-3">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
              Defense Demonstration Profiles
            </span>

            <div className="space-y-2">
              <button
                type="button"
                onClick={() => handleQuickFill('ADMIN')}
                className="w-full p-3 bg-white hover:bg-slate-100/80 border border-slate-200 hover:border-[#800000] rounded-xl text-left transition-all cursor-pointer group shadow-2xs"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <UserCheck className="w-4 h-4 text-[#800000]" />
                    <span className="text-xs font-bold text-slate-900 group-hover:text-[#800000]">
                      Lead Researcher (Admin)
                    </span>
                  </div>
                  <span className="text-[9px] font-extrabold bg-maroon-50 text-[#800000] border border-maroon-200 px-1.5 py-0.5 rounded">
                    ADMIN
                  </span>
                </div>
                <span className="text-[11px] text-slate-500 block font-mono mt-1">
                  admin@foundationu.com
                </span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickFill('OPERATOR')}
                className="w-full p-3 bg-white hover:bg-slate-100/80 border border-slate-200 hover:border-emerald-600 rounded-xl text-left transition-all cursor-pointer group shadow-2xs"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <UserCheck className="w-4 h-4 text-emerald-700" />
                    <span className="text-xs font-bold text-slate-900 group-hover:text-emerald-800">
                      Candling Shift Operator
                    </span>
                  </div>
                  <span className="text-[9px] font-extrabold bg-emerald-50 text-emerald-800 border border-emerald-200 px-1.5 py-0.5 rounded">
                    OPERATOR
                  </span>
                </div>
                <span className="text-[11px] text-slate-500 block font-mono mt-1">
                  operator@foundationu.com
                </span>
              </button>
            </div>
          </div>

          {/* Section: Infrastructure Security Telemetry */}
          <div className="p-3.5 bg-white rounded-xl border border-slate-200 space-y-2.5 shadow-2xs">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
              Security Specifications
            </span>

            <div className="space-y-1.5 text-xs">
              <div className="flex items-center gap-2 text-slate-700">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                <span>Bcrypt Password Hashing (12 Rounds)</span>
              </div>
              <div className="flex items-center gap-2 text-slate-700">
                <Zap className="w-3.5 h-3.5 text-[#800000] flex-shrink-0" />
                <span>HS256 JWT Tokenized RBAC Sessions</span>
              </div>
              <div className="flex items-center gap-2 text-slate-700">
                <Server className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
                <span>PostgreSQL 16 Enterprise Audit Trail</span>
              </div>
            </div>
          </div>

          {/* System Status Indicator */}
          <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-200">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
              API Gateway Online
            </span>
            <span className="font-mono text-slate-600">v2.0.0-PROD</span>
          </div>
        </div>
      </div>
    </div>
  );
};
