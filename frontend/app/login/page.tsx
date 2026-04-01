"use client";

import React, { useState } from "react";
import { useAuth, API_URL } from "../../lib/auth";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";



export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("username", username);
      params.append("password", password);

      const resp = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: params,
      });

      if (resp.ok) {
        const data = await resp.json();
        await login(data.access_token);
      } else {
        const errData = await resp.json();
        setError(errData.detail || "Invalid credentials");
      }
    } catch (err) {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0a] p-4 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#1a1500] via-[#0a0a0a] to-[#0a0a0a]">
      <Card className="w-full max-w-md border-[#b8860b]/30 bg-[#121212]/80 backdrop-blur-md shadow-2xl">
        <CardHeader className="text-center space-y-2">
          <div className="mx-auto w-16 h-16 rounded-full bg-[#b8860b]/20 flex items-center justify-center border border-[#b8860b]/40">
             <span className="text-2xl">🕉️</span>
          </div>
          <CardTitle className="text-3xl font-serif text-[#b8860b]">Welcome Back</CardTitle>
          <CardDescription className="text-gray-400">
            Continue your journey of wisdom with Saarthi AI
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Username</label>
              <Input 
                type="text" 
                placeholder="Your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="bg-black/40 border-[#b8860b]/20 focus:border-[#b8860b] h-12"
                required
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Password</label>
              <Input 
                type="password" 
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-black/40 border-[#b8860b]/20 focus:border-[#b8860b] h-12"
                required
              />
            </div>
            {error && <p className="text-red-400 text-sm text-center">{error}</p>}
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" disabled={loading} className="w-full h-12 bg-[#b8860b] hover:bg-[#8b6508] text-white font-bold transition-all duration-300 shadow-lg shadow-[#b8860b]/20 disabled:opacity-70">
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                  </svg>
                  Signing in...
                </span>
              ) : "Sign In"}
            </Button>
            <p className="text-sm text-gray-500 text-center">
              New seeker?{" "}
              <Link href="/signup" className="text-[#b8860b] hover:underline">
                Create an account
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
