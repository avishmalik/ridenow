// ws_client.js
import WebSocket from "ws";

// Replace this with your valid JWT token
const TOKEN = "<YOUR_JWT_TOKEN>";

// ✅ Correct WebSocket URL format
const WS_URL = `ws://localhost:8000/ws?token=${TOKEN}`;

console.log("Connecting to:", WS_URL);

const ws = new WebSocket(WS_URL);

// When the connection opens
ws.on("open", () => {
  console.log("✅ Connected to WebSocket server!");
  ws.send(JSON.stringify({ message: "Hello from client!" }));
});

// When a message is received
ws.on("message", (data) => {
  console.log("📩 Received:", data.toString());
});

// When the connection closes
ws.on("close", (code, reason) => {
  console.log(`❌ Disconnected (code: ${code}, reason: ${reason})`);
});

// When there’s an error
ws.on("error", (err) => {
  console.error("⚠️ WebSocket error:", err.message);
});
