import { apiRequest } from "./client";
import type { LoginResponse, User } from "../types/user";

export function login(username: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function getCurrentUser(token: string): Promise<User> {
  return apiRequest<User>("/auth/me", { token });
}
