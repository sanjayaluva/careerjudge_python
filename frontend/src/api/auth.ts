/**
 * Auth API functions — signup, login, logout, verify-email, refresh, reset.
 */
import axios from "axios";

import { API_BASE_URL } from "@/lib/constants";
import type {
  ApiSuccessEnvelope,
  LoginResponse,
  SignupResponse,
  TokenRefreshResponse,
} from "./types";

// Use a plain axios instance here (instead of apiClient) to avoid the
// auto-refresh interceptor firing on login/signup/reset.
const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

export interface SignupArgs {
  email: string;
  password: string;
  full_name?: string;
}

export async function signup(args: SignupArgs): Promise<SignupResponse> {
  const res = await http.post<ApiSuccessEnvelope<SignupResponse>>("/auth/signup", args);
  return res.data.data;
}

export interface LoginArgs {
  email: string;
  password: string;
}

export async function login(args: LoginArgs): Promise<LoginResponse> {
  const res = await http.post<ApiSuccessEnvelope<LoginResponse>>("/auth/login", args);
  return res.data.data;
}

export async function logout(refresh: string, accessToken: string): Promise<void> {
  await axios.post(
    `${API_BASE_URL}/auth/logout`,
    { refresh },
    {
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );
}

export async function refreshToken(refresh: string): Promise<TokenRefreshResponse> {
  const res = await http.post<ApiSuccessEnvelope<TokenRefreshResponse>>("/auth/token/refresh", {
    refresh,
  });
  return res.data.data;
}

export async function verifyEmail(token: string): Promise<void> {
  await http.post("/auth/verify-email", { token });
}

export async function resendVerification(email: string): Promise<void> {
  await http.post("/auth/resend-verification", { email });
}

export async function forgotPassword(email: string): Promise<void> {
  await http.post("/auth/forgot-password", { email });
}

export async function resetPassword(token: string, password: string): Promise<void> {
  await http.post("/auth/reset-password", { token, password });
}
