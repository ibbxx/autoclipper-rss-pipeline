"use client";

import { useRouter } from "next/navigation";
import * as React from "react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-xl border p-6 space-y-4">
        <h1 className="text-xl font-semibold">Login</h1>
        <p className="text-sm text-muted-foreground">MVP auth placeholder.</p>
        <input
          className="w-full rounded-md border px-3 py-2 text-sm"
          placeholder="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="w-full rounded-md border px-3 py-2 text-sm"
          placeholder="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button
          className="w-full rounded-md border px-3 py-2 text-sm hover:bg-muted"
          onClick={() => {
            // Dummy login: store token placeholder
            localStorage.setItem("token", "dev-token");
            router.push("/");
          }}
        >
          Sign in
        </button>
      </div>
    </div>
  );
}
