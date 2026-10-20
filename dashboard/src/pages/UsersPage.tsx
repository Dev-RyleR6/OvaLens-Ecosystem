import React, { useState, useEffect, useMemo } from 'react';
import {
  UserPlus,
  Search,
  CheckCircle2,
  List,
  LayoutGrid,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  UserRoundX,
  UserRoundCheck,
  X,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { User, UserRole } from '../types';
import { Badge } from '../components/Badge';
import { Dialog } from '../components/ui/dialog';
import { DataUnavailableState } from '../components/ui/DataUnavailableState';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmationModal } from '../components/ui/ConfirmationModal';

type ViewMode = 'TABLE' | 'GRID';
type SortField = 'full_name' | 'role' | 'created_at';
type SortOrder = 'asc' | 'desc';

export const UsersPage: React.FC = () => {
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isRegistering, setIsRegistering] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('TABLE');
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [sortField, setSortField] = useState<SortField>('full_name');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [userToToggle, setUserToToggle] = useState<User | null>(null);
  const [isTogglingStatus, setIsTogglingStatus] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>('OPERATOR');

  const fetchUsers = async () => {
    setIsLoading(true);
    setIsError(false);
    try {
      const data = await apiClient.getUsers();
      setUsers(data || []);
      setHasLoaded(true);
    } catch (err) {
      console.error('Failed to fetch users:', err);
      setIsError(true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { void fetchUsers(); }, []);

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isRegistering) return;
    setIsRegistering(true);
    setSaveError(null);
    try {
      await apiClient.createUser({ full_name: fullName, email, password, role });
      setIsRegisterOpen(false);
      setFullName(''); setEmail(''); setPassword('');
      void fetchUsers();
      setToastMessage(`Account for ${fullName} created.`);
      setTimeout(() => setToastMessage(null), 3000);
    } catch {
      setSaveError('The account could not be created. Check the email address and password requirements, then try again.');
    } finally { setIsRegistering(false); }
  };

  const handleConfirmToggleStatus = async () => {
    if (!userToToggle || isTogglingStatus) return;
    setIsTogglingStatus(true);
    setSaveError(null);
    try {
      await apiClient.toggleUserStatus(userToToggle.user_id);
      await fetchUsers();
      setToastMessage(`Account access for ${userToToggle.full_name} has been ${userToToggle.is_active ? 'suspended' : 'reactivated'}.`);
      setTimeout(() => setToastMessage(null), 3500);
    } catch {
      setSaveError('Account access could not be updated. Refresh the list and try again.');
    } finally {
      setIsTogglingStatus(false);
      setUserToToggle(null);
    }
  };

  const processedUsers = useMemo(() => {
    let result = [...users];
    const q = searchQuery.trim().toLowerCase();
    if (q) result = result.filter(u => u.full_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));
    if (roleFilter !== 'ALL') result = result.filter(u => u.role === roleFilter);
    if (statusFilter === 'ACTIVE') result = result.filter(u => u.is_active);
    else if (statusFilter === 'SUSPENDED') result = result.filter(u => !u.is_active);
    result.sort((a, b) => sortOrder === 'asc'
      ? a[sortField].localeCompare(b[sortField])
      : b[sortField].localeCompare(a[sortField]));
    return result;
  }, [users, searchQuery, roleFilter, statusFilter, sortField, sortOrder]);

  const totalPages = Math.max(1, Math.ceil(processedUsers.length / rowsPerPage));
  useEffect(() => { setCurrentPage(page => Math.min(page, totalPages)); }, [totalPages]);
  const paginatedUsers = useMemo(() => {
    const start = (currentPage - 1) * rowsPerPage;
    return processedUsers.slice(start, start + rowsPerPage);
  }, [processedUsers, currentPage, rowsPerPage]);
  const hasFilters = Boolean(searchQuery.trim()) || roleFilter !== 'ALL' || statusFilter !== 'ALL';
  const clearFilters = () => {
    setSearchQuery(''); setRoleFilter('ALL'); setStatusFilter('ALL'); setCurrentPage(1);
  };
  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortOrder(order => order === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortOrder('asc'); }
  };
  const sortHeader = (field: SortField, label: string) => {
    const selected = sortField === field;
    const nextDirection = selected && sortOrder === 'asc' ? 'descending' : 'ascending';
    const Icon = selected ? (sortOrder === 'asc' ? ArrowUp : ArrowDown) : ArrowUpDown;
    return (
      <th scope="col" aria-sort={selected ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'} className="py-1 px-4">
        <button type="button" onClick={() => toggleSort(field)} aria-label={`Sort ${label} ${nextDirection}`} className="flex items-center gap-2 text-left font-medium hover:text-brand">
          {label}<Icon aria-hidden="true" className="w-4 h-4 shrink-0" />
        </button>
      </th>
    );
  };
  const accessAction = (u: User) => (
    <button type="button" onClick={() => setUserToToggle(u)} aria-label={`${u.is_active ? 'Suspend' : 'Reactivate'} access for ${u.full_name}`} className="secondary-action">
      {u.is_active ? <UserRoundX aria-hidden="true" /> : <UserRoundCheck aria-hidden="true" />}
      {u.is_active ? 'Suspend' : 'Reactivate'}
    </button>
  );

  return (
    <div className="space-y-6 pb-8 min-w-0">
      <div className="page-header">
        <div>
          <h1>User &amp; Access Management</h1>
          <p className="page-description">Manage hatchery operators, shift supervisors, and role-based access permissions.</p>
        </div>
        <div className="page-actions">
          <button type="button" onClick={() => { void fetchUsers(); }} disabled={isLoading} className="secondary-action">
            <RefreshCw aria-hidden="true" />{isLoading ? 'Refreshing…' : 'Refresh'}
          </button>
          <button type="button" onClick={() => { setSaveError(null); setIsRegisterOpen(true); }} className="primary-action">
            <UserPlus aria-hidden="true" />Register New Operator
          </button>
        </div>
      </div>
      {saveError && !isRegisterOpen && <p role="alert" className="p-4 bg-red-50 text-red-800 border border-red-300 rounded-xl">{saveError}</p>}
      {toastMessage && <div role="status" className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 flex items-center gap-2"><CheckCircle2 aria-hidden="true" className="w-4 h-4 shrink-0" /><span>{toastMessage}</span></div>}

      <div className="filter-panel space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="w-full sm:w-80 min-w-0">
            <label htmlFor="users-search" className="block font-medium mb-1.5">Search users</label>
            <div className="relative">
              <Search aria-hidden="true" className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input id="users-search" type="search" placeholder="Operator name or email" value={searchQuery} onChange={e => { setSearchQuery(e.target.value); setCurrentPage(1); }} className="w-full pl-10 pr-3 py-2.5 bg-card border border-slate-300 rounded-lg" />
            </div>
          </div>
          <div className="page-actions" role="group" aria-label="User list view">
            <button type="button" onClick={() => setViewMode('TABLE')} aria-pressed={viewMode === 'TABLE'} className={viewMode === 'TABLE' ? 'primary-action' : 'secondary-action'}><List aria-hidden="true" />Table</button>
            <button type="button" onClick={() => setViewMode('GRID')} aria-pressed={viewMode === 'GRID'} className={viewMode === 'GRID' ? 'primary-action' : 'secondary-action'}><LayoutGrid aria-hidden="true" />Grid</button>
          </div>
        </div>
        <div className="filter-toolbar">
          <div>
            <label htmlFor="users-role">Role</label>
            <select id="users-role" value={roleFilter} onChange={e => { setRoleFilter(e.target.value); setCurrentPage(1); }}>
              <option value="ALL">All Roles</option><option value="ADMIN">Lead Admin</option><option value="MANAGER">Hatchery Manager</option><option value="OPERATOR">Sorting Operator</option>
            </select>
          </div>
          <div>
            <label htmlFor="users-status">Account status</label>
            <select id="users-status" value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setCurrentPage(1); }}>
              <option value="ALL">All Account Statuses</option><option value="ACTIVE">Active Only</option><option value="SUSPENDED">Suspended Only</option>
            </select>
          </div>
          {hasFilters && <button type="button" onClick={clearFilters} className="secondary-action"><X aria-hidden="true" />Clear filters</button>}
        </div>
      </div>

      {isError && hasLoaded && <div role="alert" className="feedback-warning space-y-3"><p>The user list could not be refreshed. Previously loaded accounts are shown and may be out of date.</p><button type="button" onClick={() => { void fetchUsers(); }} disabled={isLoading} className="secondary-action"><RefreshCw aria-hidden="true" />Retry</button></div>}
      {isLoading && hasLoaded && <p role="status" className="text-slate-600">Refreshing user accounts… Previously loaded records remain visible.</p>}
      {isError && !hasLoaded ? (
        <DataUnavailableState title="User Service Offline" description="Unable to load user accounts from PostgreSQL. Ensure the backend REST service is reachable." onRetry={fetchUsers} isRetrying={isLoading} />
      ) : !hasLoaded ? (
        <div role="status" aria-busy="true" className="fu-card p-6 space-y-4">
          <p className="text-slate-600">Loading user accounts…</p>
          <div aria-hidden="true" className="space-y-3 animate-pulse">{[1, 2, 3].map(row => <div key={row} className="h-11 bg-slate-100 rounded" />)}</div>
        </div>
      ) : processedUsers.length === 0 ? (
        <EmptyState title={hasFilters ? 'No matching users' : 'No user accounts'} description={hasFilters ? 'No user accounts match your search and filters. Clear the filters to see all accounts.' : 'Register an operator to grant access to hatchery shifts.'} actionLabel={hasFilters ? 'Clear filters' : 'Add Operator Account'} onAction={hasFilters ? clearFilters : () => { setSaveError(null); setIsRegisterOpen(true); }} />
      ) : viewMode === 'TABLE' ? (
        <div className="table-scroll bordered-table" tabIndex={0} role="region" aria-label="User accounts table, scroll horizontally on smaller screens" aria-busy={isLoading}>
          <table className="w-full min-w-[900px] text-left">
            <thead><tr>
              {sortHeader('full_name', 'Operator / Name')}
              <th scope="col">Email</th>
              {sortHeader('role', 'Role & Access')}
              <th scope="col">Status</th>
              {sortHeader('created_at', 'Registered')}
              <th scope="col" className="text-right">Actions</th>
            </tr></thead>
            <tbody>{paginatedUsers.map(u => (
              <tr key={u.user_id} className="table-row-hover">
                <th scope="row" className="font-medium text-foreground normal-case">
                  <div className="flex items-center gap-3">
                    <div aria-hidden="true" className="w-8 h-8 shrink-0 rounded-full bg-maroon-50 border border-maroon-200 text-brand flex items-center justify-center font-semibold">{u.full_name.charAt(0)}</div>
                    <span className="max-w-64 [overflow-wrap:anywhere]">{u.full_name}</span>
                  </div>
                </th>
                <td className="text-slate-600"><span className="block max-w-64 [overflow-wrap:anywhere]">{u.email}</span></td>
                <td><Badge type="role" value={u.role} /></td>
                <td><Badge value={u.is_active ? 'ACTIVE' : 'INACTIVE'} /></td>
                <td className="text-slate-600 whitespace-nowrap">{new Date(u.created_at).toLocaleDateString()}</td>
                <td className="text-right">{accessAction(u)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      ) : (
        <div className="scan-grid" aria-busy={isLoading}>
          {paginatedUsers.map(u => (
            <article key={u.user_id} className="fu-card p-5 min-w-0 flex flex-col gap-4">
              <div className="flex items-start gap-3 min-w-0">
                <div aria-hidden="true" className="w-10 h-10 shrink-0 rounded-full bg-maroon-50 border border-maroon-200 text-brand flex items-center justify-center font-semibold">{u.full_name.charAt(0)}</div>
                <div className="min-w-0"><h2 className="font-semibold [overflow-wrap:anywhere]">{u.full_name}</h2><p className="text-slate-600 mt-1 [overflow-wrap:anywhere]">{u.email}</p></div>
              </div>
              <div className="flex flex-wrap gap-2"><Badge type="role" value={u.role} /><Badge value={u.is_active ? 'ACTIVE' : 'INACTIVE'} /></div>
              <p className="text-xs text-slate-600">Joined: {new Date(u.created_at).toLocaleDateString()}</p>
              <div className="mt-auto pt-4 border-t border-border page-actions justify-end">{accessAction(u)}</div>
            </article>
          ))}
        </div>
      )}

      {hasLoaded && processedUsers.length > 0 && <div className="flex flex-wrap items-center justify-between gap-4 text-slate-600">
        <div className="flex items-center gap-3 flex-wrap">
          <span>Showing {paginatedUsers.length} of {processedUsers.length} users</span>
          <label htmlFor="users-per-page">Rows per page</label>
          <select id="users-per-page" value={rowsPerPage} onChange={e => { setRowsPerPage(Number(e.target.value)); setCurrentPage(1); }} className="px-3 py-2 bg-card border border-slate-300 rounded-lg"><option value={5}>5</option><option value={10}>10</option><option value={25}>25</option></select>
        </div>
        <div className="page-actions">
          <button type="button" onClick={() => setCurrentPage(p => Math.max(1, p - 1))} aria-label="Previous page" disabled={currentPage === 1} className="secondary-action"><ChevronLeft aria-hidden="true" /></button>
          <span className="px-2 font-medium text-foreground" aria-live="polite">Page {currentPage} of {totalPages}</span>
          <button type="button" onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} aria-label="Next page" disabled={currentPage >= totalPages} className="secondary-action"><ChevronRight aria-hidden="true" /></button>
        </div>
      </div>}

      <Dialog isOpen={isRegisterOpen} onClose={() => { if (!isRegistering) setIsRegisterOpen(false); }} title="Register New Hatchery Operator" description="Create an authorized user credential for candling station shifts.">
        <form onSubmit={handleRegisterSubmit} className="space-y-4">
          {saveError && <p role="alert" className="text-red-800">{saveError}</p>}
          <div className="space-y-1.5"><label htmlFor="userspage-field-1" className="font-medium">Full Name</label><input id="userspage-field-1" required autoComplete="name" placeholder="e.g. Maria Clara" value={fullName} onChange={e => setFullName(e.target.value)} className="w-full px-3 py-2.5 bg-card border border-slate-300 rounded-lg" /></div>
          <div className="space-y-1.5"><label htmlFor="userspage-field-2" className="font-medium">Institutional Email</label><input id="userspage-field-2" type="email" required autoComplete="email" placeholder="e.g. maria.clara@foundationu.com" value={email} onChange={e => setEmail(e.target.value)} className="w-full px-3 py-2.5 bg-card border border-slate-300 rounded-lg" /></div>
          <div className="space-y-1.5"><label htmlFor="userspage-field-3" className="font-medium">Temporary Password</label><input id="userspage-field-3" type="password" required autoComplete="new-password" placeholder="Minimum 6 characters" value={password} onChange={e => setPassword(e.target.value)} className="w-full px-3 py-2.5 bg-card border border-slate-300 rounded-lg" /></div>
          <div className="space-y-1.5"><label htmlFor="userspage-field-4" className="font-medium">Assigned Role</label><select id="userspage-field-4" value={role} onChange={e => setRole(e.target.value as UserRole)} className="w-full px-3 py-2.5 bg-card border border-slate-300 rounded-lg"><option value="OPERATOR">Sorting Operator (Edge Station & Candling)</option><option value="MANAGER">Hatchery Manager (Batches & Analytics)</option><option value="ADMIN">System Administrator (Full Control)</option></select></div>
          <div className="pt-4 page-actions justify-end border-t border-border">
            <button type="button" disabled={isRegistering} onClick={() => setIsRegisterOpen(false)} className="secondary-action"><X aria-hidden="true" />Cancel</button>
            <button type="submit" disabled={isRegistering} className="primary-action"><UserPlus aria-hidden="true" />{isRegistering ? 'Creating account…' : 'Create Account'}</button>
          </div>
        </form>
      </Dialog>
      <ConfirmationModal
        isOpen={userToToggle !== null}
        onClose={() => { if (!isTogglingStatus) setUserToToggle(null); }}
        onConfirm={handleConfirmToggleStatus}
        title={userToToggle?.is_active ? `Suspend User Access: ${userToToggle?.full_name}` : `Reactivate User Access: ${userToToggle?.full_name}`}
        description={userToToggle?.is_active
          ? `Are you sure you want to suspend access for ${userToToggle?.full_name} (${userToToggle?.email})? They will immediately be prevented from logging into candling stations and the admin dashboard.`
          : `Are you sure you want to reactivate access for ${userToToggle?.full_name} (${userToToggle?.email})? They will regain access to their assigned ${userToToggle?.role} role.`}
        confirmText={userToToggle?.is_active ? 'Suspend Account' : 'Reactivate Account'}
        cancelText="Cancel" variant={userToToggle?.is_active ? 'danger' : 'primary'} isLoading={isTogglingStatus}
      />
    </div>
  );
};
