export type UserRole = "admin" | "user";

export interface User {
  id: number;
  username: string;
  role: UserRole;
  created_at: string;
}

export interface UserPayload {
  username: string;
  password?: string;
  role: UserRole;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
}
