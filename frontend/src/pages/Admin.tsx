import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { UserPlus, Shield } from "lucide-react";

interface UserRow {
  id: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
}

const ROLES = ["admin", "analist", "viewer", "ai_engineer"];

export default function Admin() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();

  if (user?.role !== "admin") {
    navigate("/dashboard");
    return null;
  }

  const qc = useQueryClient();
  const { data: users, isLoading } = useQuery<UserRow[]>({
    queryKey: ["admin-users"],
    queryFn: async () => {
      const { data } = await apiClient.get("/admin/users");
      return data;
    },
  });

  const [newUser, setNewUser] = useState({ email: "", username: "", password: "", role: "viewer" });

  const createMutation = useMutation({
    mutationFn: () => apiClient.post("/admin/users", newUser),
    onSuccess: () => {
      toast.success("Kullanıcı oluşturuldu");
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      setNewUser({ email: "", username: "", password: "", role: "viewer" });
    },
    onError: (err: any) => toast.error(err?.response?.data?.error?.message || "Hata"),
  });

  const updateRoleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) =>
      apiClient.patch(`/admin/users/${id}`, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  return (
    <div className="p-8 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
        <Shield size={24} className="text-primary-600" /> Admin Paneli
      </h1>

      {/* Create User */}
      <div className="bg-white rounded-xl shadow p-6">
        <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <UserPlus size={18} /> Yeni Kullanıcı
        </h2>
        <div className="grid grid-cols-2 gap-4">
          {(["email", "username", "password"] as const).map((field) => (
            <input
              key={field}
              type={field === "password" ? "password" : "text"}
              placeholder={field}
              value={newUser[field]}
              onChange={(e) => setNewUser((p) => ({ ...p, [field]: e.target.value }))}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          ))}
          <select
            value={newUser.role}
            onChange={(e) => setNewUser((p) => ({ ...p, role: e.target.value }))}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <button
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
          className="mt-4 bg-primary-600 hover:bg-primary-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          Oluştur
        </button>
      </div>

      {/* User List */}
      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Kullanıcı</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Rol</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Durum</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {users?.map((u) => (
              <tr key={u.id}>
                <td className="px-6 py-4">
                  <p className="font-medium">{u.username}</p>
                  <p className="text-xs text-gray-500">{u.email}</p>
                </td>
                <td className="px-6 py-4">
                  <select
                    value={u.role}
                    onChange={(e) => updateRoleMutation.mutate({ id: u.id, role: e.target.value })}
                    className="border border-gray-200 rounded px-2 py-1 text-xs"
                  >
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
                <td className="px-6 py-4">
                  <span className={`text-xs font-medium ${u.is_active ? "text-green-600" : "text-red-500"}`}>
                    {u.is_active ? "Aktif" : "Pasif"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
