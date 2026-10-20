import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Eye, EyeOff, AlertCircle, Check, Loader2, LogIn } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import ovalensLogo from '../assets/logos/ovalens_logo_final.svg';

const sanitize = (val: string): string => val.replace(/<[^>]*>?/gm, '').trim();
const isValidEmail = (email: string): boolean => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
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
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [failedAttempts, setFailedAttempts] = useState(() => {
    const saved = sessionStorage.getItem('ovalens_attempts');
    return saved ? parseInt(saved, 10) : 0;
  });
  const [lockoutTimer, setLockoutTimer] = useState(0);

  useEffect(() => {
    if (isAuthenticated && !isLoading && !isSuccess) {
      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, isLoading, isSuccess, navigate, location]);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    if (lockoutTimer > 0) {
      timer = setInterval(() => {
        setLockoutTimer(prev => {
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
    if (lockoutTimer > 0 || isLoading || isSuccess) return;
    setErrorMessage(null);
    const cleanEmail = sanitize(email).toLowerCase();
    if (!cleanEmail || !isValidEmail(cleanEmail)) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }
    if (!password) {
      setErrorMessage('Please enter your password.');
      return;
    }
    setIsLoading(true);
    try {
      // Passwords are credentials: preserve every character, including whitespace.
      await login({ email: cleanEmail, password });
      if (rememberMe) localStorage.setItem('ovalens_remembered_email', cleanEmail);
      else localStorage.removeItem('ovalens_remembered_email');
      setFailedAttempts(0);
      sessionStorage.removeItem('ovalens_attempts');
      setIsSuccess(true);
      await new Promise(res => setTimeout(res, 400));
      const targetPath = (location.state as any)?.from?.pathname;
      const safeDestination = targetPath?.startsWith('/') && !targetPath.startsWith('//') ? targetPath : '/';
      navigate(safeDestination, { replace: true });
    } catch (err: any) {
      const attempts = failedAttempts + 1;
      setFailedAttempts(attempts);
      sessionStorage.setItem('ovalens_attempts', attempts.toString());
      if (attempts >= MAX_FAILED_ATTEMPTS) {
        setLockoutTimer(LOCKOUT_SECONDS);
        setErrorMessage(`Too many failed attempts. Try again in ${LOCKOUT_SECONDS} seconds.`);
      } else if (!err.response) {
        setErrorMessage('Unable to connect. Check your network and try signing in again.');
      } else {
        setErrorMessage(err.response?.data?.detail || 'Invalid email or password. Please try again.');
      }
    } finally { setIsLoading(false); }
  };

  const isDisabled = lockoutTimer > 0 || isLoading || isSuccess;
  return (
    <div className="min-h-screen bg-background flex flex-col justify-center items-center px-4 py-12 font-sans text-foreground">
      <div className="w-full max-w-sm">
        <header className="page-header mb-7">
          <div className="w-full text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-[#F8FAFC] mb-3">
              <img src={ovalensLogo} alt="OvaLens logo" className="w-14 h-14 object-contain" width={56} height={56} />
            </div>
            <h1>OvaLens Hatchery System</h1>
            <p className="page-description">Foundation University Duck Egg Management</p>
          </div>
        </header>
        <div className="fu-card p-6 sm:p-7">
          {errorMessage && <div id="login-error" role="alert" className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 flex items-start gap-2.5"><AlertCircle aria-hidden="true" className="w-4 h-4 shrink-0 mt-0.5" /><span>{errorMessage}</span></div>}
          {lockoutTimer > 0 && <div role="status" className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-center">Sign-in paused in this browser. Please wait <strong>{lockoutTimer}s</strong>.</div>}
          <form onSubmit={handleSubmit} className="space-y-4" aria-busy={isLoading}>
            <div>
              <label htmlFor="loginpage-field-1" className="block font-medium mb-1.5">Email address</label>
              <input id="loginpage-field-1" aria-describedby={errorMessage ? 'login-error' : undefined} type="email" required disabled={isDisabled} value={email} onChange={e => setEmail(e.target.value)} placeholder="name@foundationu.com" autoComplete="email" className="w-full px-3 py-2.5 bg-card border border-slate-300 rounded-lg disabled:bg-slate-50" />
            </div>
            <div>
              <label htmlFor="loginpage-field-2" className="block font-medium mb-1.5">Password</label>
              <div className="relative">
                <input id="loginpage-field-2" aria-describedby={errorMessage ? 'login-error' : undefined} type={showPassword ? 'text' : 'password'} required disabled={isDisabled} value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter your password" autoComplete="current-password" className="w-full pl-3 pr-14 py-2.5 bg-card border border-slate-300 rounded-lg disabled:bg-slate-50" />
                <button type="button" onClick={() => setShowPassword(!showPassword)} disabled={isDisabled} className="absolute right-0 top-1/2 -translate-y-1/2 min-h-11 w-11 flex items-center justify-center rounded-lg text-slate-600 hover:text-foreground hover:bg-slate-100" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword}>
                  {showPassword ? <EyeOff aria-hidden="true" className="w-4 h-4" /> : <Eye aria-hidden="true" className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" checked={rememberMe} onChange={e => setRememberMe(e.target.checked)} disabled={isDisabled} />
              <span className="text-slate-600">Remember email</span>
            </label>
            <div className="page-actions">
              <button type="submit" disabled={isDisabled} className="primary-action w-full">
                {isSuccess ? <Check aria-hidden="true" /> : isLoading ? <Loader2 aria-hidden="true" className="animate-spin" /> : <LogIn aria-hidden="true" />}
                <span>{isSuccess ? 'Signed in' : isLoading ? 'Signing in…' : 'Sign In'}</span>
              </button>
            </div>
            {(isLoading || isSuccess) && <p role="status" className="text-slate-600">{isSuccess ? 'Signed in. Opening the dashboard…' : 'Checking your credentials…'}</p>}
          </form>
        </div>
        <div className="mt-6 text-center text-xs text-slate-600">Foundation University • Team DevIn</div>
      </div>
    </div>
  );
};

export default LoginPage;
