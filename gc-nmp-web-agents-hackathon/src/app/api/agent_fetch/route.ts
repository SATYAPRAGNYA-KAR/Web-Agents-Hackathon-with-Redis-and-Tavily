// src/app/api/agent_fetch/route.ts
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    console.log("Received request body:", body);
    
    // Call FastAPI server on port 8124 for tools
    const backendUrl = "http://localhost:8124";
    const fullUrl = `${backendUrl}/tools/get_market_news`;
    
    console.log("Calling FastAPI at:", fullUrl);
    
    const res = await fetch(fullUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    console.log("FastAPI response status:", res.status);
    
    if (!res.ok) {
      const errorText = await res.text();
      console.error("FastAPI error response:", errorText);
      return NextResponse.json(
        { ok: false, error: `Backend returned ${res.status}: ${errorText}` },
        { status: res.status }
      );
    }

    const contentType = res.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      const text = await res.text();
      console.error("Non-JSON response:", text);
      return NextResponse.json(
        { ok: false, error: `Expected JSON but got: ${text.substring(0, 100)}` },
        { status: 500 }
      );
    }

    const data = await res.json();
    console.log("FastAPI response data:", data);
    return NextResponse.json(data);
    
  } catch (err: any) {
    console.error("Error in agent_fetch route:", err);
    return NextResponse.json(
      { ok: false, error: err.message || "Unknown error" },
      { status: 500 }
    );
  }
}