import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, ArrowLeft, Layers } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';

interface RoleProtectedRouteProps {
  allowedRoles: ('ADMIN' | 'MANAGER' | 'OPERATOR')[];
  children: React.ReactNode;
  moduleName?: string;
}

export const RoleProtectedRoute: React.FC<RoleProtectedRouteProps> = ({
  allowedRoles,
  children,
  moduleName = 'This Module',
}) => {
  const { user } = useAuth();
  const currentRole = (user?.role || 'OPERATOR') as 'ADMIN' | 'MANAGER' | 'OPERATOR';

  if (!allowedRoles.includes(currentRole)) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-xs text-center space-y-5">
          <div className="w-12 h-12 rounded-2xl bg-amber-50 border border-amber-200 text-amber-700 mx-auto flex items-center justify-center shadow-2xs">
            <ShieldAlert className="w-6 h-6" />
          </div>

          <div className="space-y-1.5">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
              403 Forbidden • Access Restricted
            </span>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              {moduleName} Access Restricted
            </h2>
            <p className="text-xs text-slate-500 leading-relaxed">
              Your active account role is assigned as{' '}
              <strong className="text-slate-800 font-mono font-bold uppercase">
                {currentRole}
              </strong>
              . This management interface requires{' '}
              <strong className="text-slate-800">
                {allowedRoles.join(' or ')}
              </strong>{' '}
              privileges.
            </p>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-left text-xs space-y-1 text-slate-600">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Active User:</span>
              <strong className="text-slate-900 font-mono">{user?.email || 'operator@foundationu.com'}</strong>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Assigned Scope:</span>
              <span className="font-semibold text-emerald-800">Candling Line & Vision Operations</span>
            </div>
          </div>

          <div className="flex items-center justify-center gap-3 pt-2">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors btn-press cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Command Center</span>
            </Link>

            <Link
              to="/batches"
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-bold shadow-xs transition-colors btn-press cursor-pointer"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Incubation Batches</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export default RoleProtectedRoute;
