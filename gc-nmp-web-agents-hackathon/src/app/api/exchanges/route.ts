// src/app/api/exchanges/route.ts
import { NextResponse } from "next/server";

export async function GET() {
  try {
    // IMPORTANT: Use port 8124 for FastAPI, NOT 8123 (LangGraph)
    const backendUrl = "http://localhost:8124";
    const fullUrl = `${backendUrl}/exchanges`;
    
    console.log("Fetching exchanges from FastAPI:", fullUrl);
    
    const res = await fetch(fullUrl, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store" // Prevent Next.js caching
    });

    if (!res.ok) {
      const errorText = await res.text();
      console.error("FastAPI error response:", errorText);
      return NextResponse.json(
        { ok: false, error: `Backend returned ${res.status}: ${errorText}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    console.log("Exchanges fetched successfully:", data);
    return NextResponse.json(data);
    
  } catch (err: any) {
    console.error("Error in exchanges route:", err);
    return NextResponse.json(
      { ok: false, error: err.message || "Unknown error" },
      { status: 500 }
    );
  }
}