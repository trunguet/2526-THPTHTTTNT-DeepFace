import { apiRequest } from "./client";
import type { User, UserPayload } from "../types/user";


export function listUsers(token: string): Promise<User[]> {
  return apiRequest<User[]>("/admin/users", { token });
}


export function createUser(token: string, payload: UserPayload): Promise<User> {
  return apiRequest<User>("/admin/users", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}


export function updateUser(
  token: string,
  userId: number,
  payload: Partial<UserPayload>,
): Promise<User> {
  return apiRequest<User>(`/admin/users/${userId}`, {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
}


export function deleteUser(token: string, userId: number): Promise<void> {
  return apiRequest<void>(`/admin/users/${userId}`, {
    method: "DELETE",
    token,
  });
}
