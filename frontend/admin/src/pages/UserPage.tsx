import { FormEvent, useEffect, useState } from "react";
import { createUser, deleteUser, listUsers, updateUser } from "../api/users";
import type { User, UserPayload, UserRole } from "../types/user";


interface UserPageProps {
  currentUser: User;
  token: string;
}


const emptyForm: UserPayload = {
  username: "",
  password: "",
  role: "user",
};

const PAGE_SIZE = 7;


export default function UserPage({ currentUser, token }: UserPageProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form, setForm] = useState<UserPayload>(emptyForm);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pageCount = Math.max(1, Math.ceil(users.length / PAGE_SIZE));
  const normalizedPage = Math.min(currentPage, pageCount);
  const pageStart = (normalizedPage - 1) * PAGE_SIZE;
  const visibleUsers = users.slice(pageStart, pageStart + PAGE_SIZE);

  async function loadUsers() {
    setIsLoading(true);
    setError(null);
    try {
      setUsers(await listUsers(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot load roles");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadUsers();
  }, [token]);

  useEffect(() => {
    setCurrentPage(1);
  }, [users]);

  function startEdit(user: User) {
    setEditingUser(user);
    setForm({
      username: user.username,
      password: "",
      role: user.role,
    });
    setError(null);
    setMessage(null);
  }

  function cancelEdit() {
    setEditingUser(null);
    setForm(emptyForm);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    setMessage(null);
    try {
      const username = form.username.trim();
      const password = form.password?.trim() ?? "";

      if (!username) {
        setError("Username is required.");
        return;
      }

      if (!editingUser && !password) {
        setError("Password is required.");
        return;
      }

      if (editingUser) {
        const payload: Partial<UserPayload> = {};

        if (username !== editingUser.username) {
          payload.username = username;
        }

        if (form.role !== editingUser.role) {
          payload.role = form.role;
        }

        if (password) {
          payload.password = password;
        }

        if (Object.keys(payload).length === 0) {
          setMessage("No role changes to save.");
          return;
        }

        await updateUser(token, editingUser.id, payload);
        setMessage("Role updated.");
      } else {
        await createUser(token, {
          username,
          password,
          role: form.role,
        });
        setMessage("Role created.");
      }
      cancelEdit();
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot save role");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(user: User) {
    setError(null);
    setMessage(null);

    if (user.id === currentUser.id) {
      setError("You cannot delete the signed-in role.");
      return;
    }

    const confirmed = window.confirm(
      `Delete role "${user.username}"? This action cannot be undone.`,
    );

    if (!confirmed) {
      return;
    }

    try {
      await deleteUser(token, user.id);
      setMessage("Role deleted.");
      if (editingUser?.id === user.id) {
        cancelEdit();
      }
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot delete role");
    }
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Roles</p>
          <h2>Role management</h2>
        </div>
        <button className="secondary-button" onClick={() => void loadUsers()}>
          Refresh
        </button>
      </div>

      {error ? <div className="alert error">{error}</div> : null}
      {message ? <div className="alert success">{message}</div> : null}

      <div className="split-layout">
        <form className="panel form-panel" onSubmit={handleSubmit}>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{editingUser ? "Edit" : "Create"}</p>
              <h2>{editingUser ? editingUser.username : "New Role"}</h2>
            </div>
            {editingUser ? (
              <button className="ghost-button" type="button" onClick={cancelEdit}>
                Cancel
              </button>
            ) : null}
          </div>

          <label>
            Username
            <input
              required
              value={form.username}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  username: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Password
            <input
              required={!editingUser}
              type="password"
              value={form.password ?? ""}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  password: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Role
            <select
              value={form.role}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  role: event.target.value as UserRole,
                }))
              }
            >
              <option value="user">user</option>
              <option value="admin">admin</option>
            </select>
          </label>

          <button className="primary-button" disabled={isSaving} type="submit">
            {isSaving ? "Saving..." : editingUser ? "Update role" : "Create role"}
          </button>
        </form>

        <div className="panel table-panel">
          {isLoading ? (
            <div className="state-panel">Loading roles...</div>
          ) : users.length === 0 ? (
            <div className="state-panel">No roles yet.</div>
          ) : (
            <>
              <table>
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleUsers.map((user) => (
                    <tr key={user.id}>
                      <td>{user.username}</td>
                      <td>
                        <span className={`status-pill ${user.role}`}>
                          {user.role}
                        </span>
                      </td>
                      <td>{new Date(user.created_at).toLocaleString()}</td>
                      <td className="row-actions">
                        <button className="small-button" onClick={() => startEdit(user)}>
                          Edit
                        </button>
                        <button
                          className="danger-button"
                          disabled={user.id === currentUser.id}
                          onClick={() => void handleDelete(user)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="pagination-bar">
                <span>
                  Showing {pageStart + 1}-{Math.min(pageStart + PAGE_SIZE, users.length)}{" "}
                  of {users.length}
                </span>
                <div className="pagination-actions">
                  <button
                    className="secondary-button compact-button"
                    disabled={normalizedPage === 1}
                    onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                    type="button"
                  >
                    Previous
                  </button>
                  <strong>
                    {normalizedPage} / {pageCount}
                  </strong>
                  <button
                    className="secondary-button compact-button"
                    disabled={normalizedPage === pageCount}
                    onClick={() =>
                      setCurrentPage((page) => Math.min(pageCount, page + 1))
                    }
                    type="button"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
