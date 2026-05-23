export type UserRole = "admin" | "user";

export interface User {
  id: number;
  username: string;
  role: UserRole;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
}
