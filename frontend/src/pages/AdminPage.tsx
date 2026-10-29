import { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/endpoints";

export function AdminPage() {
  const qc = useQueryClient();
  const users = useQuery({ queryKey: ["admin-users"], queryFn: adminApi.users });
  const roles = useQuery({ queryKey: ["admin-roles"], queryFn: adminApi.roles });
  const sensors = useQuery({
    queryKey: ["admin-sensors"],
    queryFn: adminApi.sensorTypes,
  });

  const create = useMutation({
    mutationFn: (payload: Record<string, unknown>) => adminApi.createUser(payload),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  function onCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    create.mutate({
      username: String(fd.get("username")),
      password: String(fd.get("password")),
      full_name: String(fd.get("full_name")),
      role: String(fd.get("role")),
      email: String(fd.get("email") || "") || null,
    });
    e.currentTarget.reset();
  }

  return (
    <div>
      <h1 className="page-title">Администрирование</h1>
      <p className="page-subtitle">Пользователи, роли и справочник типов датчиков</p>

      <div className="panel">
        <h2>Создать пользователя</h2>
        <form className="form-grid" onSubmit={onCreate}>
          <label>
            Логин
            <input name="username" required minLength={3} />
          </label>
          <label>
            Пароль
            <input name="password" type="password" required minLength={8} />
          </label>
          <label>
            ФИО
            <input name="full_name" required />
          </label>
          <label>
            Email
            <input name="email" type="email" />
          </label>
          <label>
            Роль
            <select name="role" defaultValue="technologist">
              {(roles.data || [
                { code: "admin" },
                { code: "technologist" },
                { code: "viewer" },
              ]).map((r: { code: string; name?: string }) => (
                <option key={r.code} value={r.code}>
                  {r.name || r.code}
                </option>
              ))}
            </select>
          </label>
          <button className="btn primary" disabled={create.isPending}>
            Создать
          </button>
          {create.isError && (
            <div className="state-box error">{(create.error as Error).message}</div>
          )}
        </form>
      </div>

      <div className="panel">
        <h2>Пользователи</h2>
        {users.isLoading && <div className="state-box">Загрузка...</div>}
        {users.data && (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Логин</th>
                  <th>ФИО</th>
                  <th>Роль</th>
                  <th>Активен</th>
                </tr>
              </thead>
              <tbody>
                {users.data.map((u) => (
                  <tr key={u.id}>
                    <td>{u.id}</td>
                    <td>{u.username}</td>
                    <td>{u.full_name}</td>
                    <td>{u.role_name}</td>
                    <td>{u.is_active ? "да" : "нет"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="panel">
        <h2>Типы датчиков</h2>
        {sensors.data && (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Код</th>
                  <th>Название</th>
                  <th>Ед.</th>
                  <th>Мин</th>
                  <th>Макс</th>
                </tr>
              </thead>
              <tbody>
                {sensors.data.map(
                  (s: {
                    id: number;
                    code: string;
                    name: string;
                    unit: string;
                    min_value?: number;
                    max_value?: number;
                  }) => (
                    <tr key={s.id}>
                      <td className="mono">{s.code}</td>
                      <td>{s.name}</td>
                      <td>{s.unit}</td>
                      <td>{s.min_value ?? "—"}</td>
                      <td>{s.max_value ?? "—"}</td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
