import React, { useState, useEffect, useMemo } from 'react';
import {
  Users,
  UserPlus,
  Shield,
  Search,
  CheckCircle2,
  List,
  LayoutGrid,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Mail,
  Calendar,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { User, UserRole } from '../types';
import { Dialog } from '../components/ui/dialog';
import { DataUnavailableState } from '../components/ui/DataUnavailableState';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmationModal } from '../components/ui/ConfirmationModal';

type ViewMode = 'TABLE' | 'GRID';
type SortField = 'full_name' | 'role' | 'created_at';
type SortOrder = 'asc' | 'desc';

export const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isError, setIsError] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<ViewMode>('TABLE');
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Sorting & Pagination
  const [sortField, setSortField] = useState<SortField>('full_name');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [userToToggle, setUserToToggle] = useState<User | null>(null);
  const [isTogglingStatus, setIsTogglingStatus] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Form State
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
    } catch (err) {
      console.error('Failed to fetch users:', err);
      setIsError(true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await apiClient.createUser({
      full_name: fullName,
      email,
      password,
      role,
    });
    setIsRegisterOpen(false);
    setFullName('');
    setEmail('');
    setPassword('');
    fetchUsers();
    setToastMessage(`Account for ${fullName} created successfully.`);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleConfirmToggleStatus = async () => {
    if (!userToToggle) return;
    setIsTogglingStatus(true);
    try {
      await apiClient.toggleUserStatus(userToToggle.user_id);
      await fetchUsers();
      setToastMessage(
        `Account access for ${userToToggle.full_name} has been ${
          userToToggle.is_active ? 'suspended' : 'reactivated'
        }.`
      );
      setTimeout(() => setToastMessage(null), 3500);
    } catch (err) {
      console.error('Failed to toggle user status:', err);
    } finally {
      setIsTogglingStatus(false);
      setUserToToggle(null);
    }
  };

  // Filtered & Sorted Users
  const processedUsers = useMemo(() => {
    let result = [...users];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (u) =>
          u.full_name.toLowerCase().includes(q) ||
          u.email.toLowerCase().includes(q)
      );
    }

    if (roleFilter !== 'ALL') {
      result = result.filter((u) => u.role === roleFilter);
    }

    if (statusFilter === 'ACTIVE') {
      result = result.filter((u) => u.is_active);
    } else if (statusFilter === 'SUSPENDED') {
      result = result.filter((u) => !u.is_active);
    }

    result.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      if (typeof aVal === 'string') {
        return sortOrder === 'asc'
          ? (aVal as string).localeCompare(bVal as string)
          : (bVal as string).localeCompare(aVal as string);
      }
      return 0;
    });

    return result;
  }, [users, searchQuery, roleFilter, statusFilter, sortField, sortOrder]);

  const paginatedUsers = useMemo(() => {
    const start = (currentPage - 1) * rowsPerPage;
    return processedUsers.slice(start, start + rowsPerPage);
  }, [processedUsers, currentPage, rowsPerPage]);

  const totalPages = Math.ceil(processedUsers.length / rowsPerPage) || 1;

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">
            User & Access Management
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage hatchery operators, shift supervisors, and role-based access permissions.
          </p>
        </div>

        <button
          onClick={() => setIsRegisterOpen(true)}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#800000] hover:bg-[#6B0000] text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer"
        >
          <UserPlus className="w-4 h-4" />
          <span>Register New Operator</span>
        </button>
      </div>

      {toastMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-semibold text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-700" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Enterprise Filter Toolbar */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by operator name or email..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full h-9 pl-9 pr-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#800000] shadow-xs"
            />
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 self-end sm:self-auto">
            <button
              onClick={() => setViewMode('TABLE')}
              className={`p-1.5 rounded text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors ${
                viewMode === 'TABLE' ? 'bg-white text-[#800000] shadow-xs' : 'text-slate-500 hover:text-slate-800'
              }`}
              title="Table View"
            >
              <List className="w-3.5 h-3.5" />
              <span>Table</span>
            </button>
            <button
              onClick={() => setViewMode('GRID')}
              className={`p-1.5 rounded text-xs font-bold flex items-center gap-1 cursor-pointer transition-colors ${
                viewMode === 'GRID' ? 'bg-white text-[#800000] shadow-xs' : 'text-slate-500 hover:text-slate-800'
              }`}
              title="User Cards View"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>Grid</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
          <select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Roles</option>
            <option value="ADMIN">Lead Admin</option>
            <option value="MANAGER">Hatchery Manager</option>
            <option value="OPERATOR">Sorting Operator</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-9 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-[#800000] shadow-xs cursor-pointer"
          >
            <option value="ALL">All Account Statuses</option>
            <option value="ACTIVE">Active Only</option>
            <option value="SUSPENDED">Suspended Only</option>
          </select>
        </div>
      </div>

      {/* View Mode: Table vs Grid */}
      {isError && users.length === 0 ? (
        <DataUnavailableState
          title="User Service Offline"
          description="Unable to load user accounts from PostgreSQL. Ensure the backend REST service is reachable."
          onRetry={fetchUsers}
          isRetrying={isLoading}
        />
      ) : !isLoading && processedUsers.length === 0 ? (
        <EmptyState
          title="No Users Found"
          description="No user accounts match your filter criteria."
          actionLabel="Add Operator Account"
          onAction={() => setIsRegisterOpen(true)}
        />
      ) : viewMode === 'TABLE' ? (
        <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th
                    className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                    onClick={() => toggleSort('full_name')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Operator / Name</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th className="py-3 px-4">Email</th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                    onClick={() => toggleSort('role')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Role & Access</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th className="py-3 px-4">Status</th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:bg-slate-100 transition-colors"
                    onClick={() => toggleSort('created_at')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Registered</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-400" />
                    </div>
                  </th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paginatedUsers.map((u) => (
                  <tr key={u.user_id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4 font-bold text-[#0F172A]">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-maroon-50 border border-maroon-200 text-[#800000] flex items-center justify-center font-bold text-xs">
                          {u.full_name.charAt(0)}
                        </div>
                        <span>{u.full_name}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-600 font-mono">{u.email}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-bold ${
                          u.role === 'ADMIN'
                            ? 'bg-maroon-50 text-[#800000] border border-maroon-200'
                            : u.role === 'MANAGER'
                            ? 'bg-blue-50 text-blue-800 border border-blue-200'
                            : 'bg-slate-100 text-slate-700 border border-slate-200'
                        }`}
                      >
                        <Shield className="w-3 h-3" />
                        {u.role}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {u.is_active ? (
                        <span className="inline-flex items-center gap-1.5 text-emerald-700 font-semibold text-xs">
                          <span className="w-2 h-2 rounded-full bg-emerald-600" />
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-slate-400 font-medium text-xs">
                          <span className="w-2 h-2 rounded-full bg-slate-300" />
                          Suspended
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-500 font-medium">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setUserToToggle(u)}
                        className={`text-xs font-semibold px-2.5 py-1 rounded border transition-colors cursor-pointer ${
                          u.is_active
                            ? 'border-slate-200 text-slate-600 hover:bg-slate-100'
                            : 'border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
                        }`}
                      >
                        {u.is_active ? 'Suspend' : 'Reactivate'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* User Cards Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {paginatedUsers.map((u) => (
            <div
              key={u.user_id}
              className="bg-white border border-[#E2E8F0] rounded-xl p-5 shadow-xs hover:border-[#800000] transition-colors space-y-3.5 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-maroon-50 border border-maroon-200 text-[#800000] flex items-center justify-center font-bold text-sm">
                      {u.full_name.charAt(0)}
                    </div>
                    <div>
                      <h3 className="font-bold text-[#0F172A] text-sm">{u.full_name}</h3>
                      <span className="text-[11px] text-slate-500 font-mono block">{u.email}</span>
                    </div>
                  </div>
                  {u.is_active ? (
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" title="Active" />
                  ) : (
                    <span className="w-2.5 h-2.5 rounded-full bg-slate-300" title="Suspended" />
                  )}
                </div>

                <div className="pt-3 flex items-center justify-between text-xs">
                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-bold ${
                      u.role === 'ADMIN'
                        ? 'bg-maroon-50 text-[#800000] border border-maroon-200'
                        : u.role === 'MANAGER'
                        ? 'bg-blue-50 text-blue-800 border border-blue-200'
                        : 'bg-slate-100 text-slate-700 border border-slate-200'
                    }`}
                  >
                    <Shield className="w-3 h-3" />
                    {u.role}
                  </span>
                  <span className="text-slate-400 text-[11px]">
                    Joined: {new Date(u.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-end">
                <button
                  onClick={() => setUserToToggle(u)}
                  className={`text-xs font-semibold px-3 py-1 rounded border transition-colors cursor-pointer ${
                    u.is_active
                      ? 'border-slate-200 text-slate-600 hover:bg-slate-100'
                      : 'border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
                  }`}
                >
                  {u.is_active ? 'Suspend Access' : 'Reactivate Access'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 pt-2">
        <div className="flex items-center gap-2">
          <span>Showing {paginatedUsers.length} of {processedUsers.length} users</span>
          <span>•</span>
          <span>Rows per page:</span>
          <select
            value={rowsPerPage}
            onChange={(e) => {
              setRowsPerPage(Number(e.target.value));
              setCurrentPage(1);
            }}
            className="h-7 px-2 bg-white border border-slate-200 rounded text-slate-700 font-medium focus:outline-none"
          >
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={25}>25</option>
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="p-1.5 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="px-2 font-bold text-slate-800">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="p-1.5 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Registration Modal Dialog */}
      <Dialog
        isOpen={isRegisterOpen}
        onClose={() => setIsRegisterOpen(false)}
        title="Register New Hatchery Operator"
        description="Create an authorized user credential for candling station shifts."
      >
        <form onSubmit={handleRegisterSubmit} className="space-y-4 text-sm">
          <div className="space-y-1.5">
            <label className="font-semibold text-xs text-slate-700">Full Name</label>
            <input
              required
              placeholder="e.g. Maria Clara"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="space-y-1.5">
            <label className="font-semibold text-xs text-slate-700">Institutional Email</label>
            <input
              type="email"
              required
              placeholder="e.g. maria.clara@foundationu.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="space-y-1.5">
            <label className="font-semibold text-xs text-slate-700">Temporary Password</label>
            <input
              type="password"
              required
              placeholder="Minimum 6 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-[#800000]"
            />
          </div>

          <div className="space-y-1.5">
            <label className="font-semibold text-xs text-slate-700">Assigned Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as UserRole)}
              className="w-full h-9 px-3 text-xs bg-white border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:border-[#800000]"
            >
              <option value="OPERATOR">Sorting Operator (Edge Station & Candling)</option>
              <option value="MANAGER">Hatchery Manager (Batches & Analytics)</option>
              <option value="ADMIN">System Administrator (Full Control)</option>
            </select>
          </div>

          <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-200">
            <button
              type="button"
              onClick={() => setIsRegisterOpen(false)}
              className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-bold text-white bg-[#800000] hover:bg-[#6B0000] rounded-lg shadow-xs cursor-pointer"
            >
              Create Account
            </button>
          </div>
        </form>
      </Dialog>

      {/* Confirmation Modal for Suspending / Reactivating User */}
      <ConfirmationModal
        isOpen={userToToggle !== null}
        onClose={() => setUserToToggle(null)}
        onConfirm={handleConfirmToggleStatus}
        title={userToToggle?.is_active ? `Suspend User Access: ${userToToggle?.full_name}` : `Reactivate User Access: ${userToToggle?.full_name}`}
        description={
          userToToggle?.is_active
            ? `Are you sure you want to suspend access for ${userToToggle?.full_name} (${userToToggle?.email})? They will immediately be prevented from logging into candling stations and the admin dashboard.`
            : `Are you sure you want to reactivate access for ${userToToggle?.full_name} (${userToToggle?.email})? They will regain access to their assigned ${userToToggle?.role} role.`
        }
        confirmText={userToToggle?.is_active ? 'Suspend Account' : 'Reactivate Account'}
        cancelText="Cancel"
        variant={userToToggle?.is_active ? 'danger' : 'primary'}
        isLoading={isTogglingStatus}
      />
    </div>
  );
};
