let socket = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
let reconnectTimeout = null;

function updateWSStatus(status) {
  const statusEl = document.getElementById("wsStatus");
  if (statusEl) {
    statusEl.className = `ws-status ${status}`;
    statusEl.textContent = status === "connected" ? "🟢 Connected" : 
                           status === "connecting" ? "🟡 Connecting..." : 
                           "🔴 Disconnected";
  }
}

function connectWS() {
  const token = localStorage.getItem("token");
  
  if (!token) {
    console.error("No token found");
    updateWSStatus("disconnected");
    if (typeof showError === "function") {
      showError("Please login first to connect WebSocket");
    }
    return;
  }

  // Close existing connection if any
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.close();
  }

  // Clear any pending reconnection
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }

  updateWSStatus("connecting");
  
  const WS_URL = BASE_URL.replace("http", "ws");

  socket = new WebSocket(`${WS_URL}/ws?token=${token}`);

  socket.onopen = () => {
    console.log("🟢 WebSocket connected! Waiting for welcome message...");
    updateWSStatus("connected");
    reconnectAttempts = 0;
    
    // Notify user
    if (typeof onWSConnected === "function") {
      onWSConnected();
    }
  };

  socket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      console.log("📨 WS Message:", msg);
      
      // Handle welcome message
      if (msg.event === "connected") {
        console.log(`✅ Connection confirmed - User ID: ${msg.user_id}, Driver: ${msg.is_driver}`);
        updateWSStatus("connected");
        
        // Store user info
        if (msg.user_id) {
          localStorage.setItem("user_id", msg.user_id);
        }
        if (msg.is_driver !== undefined) {
          localStorage.setItem("is_driver", msg.is_driver);
        }
        
        if (typeof onWSMessage === "function") {
          onWSMessage(msg);
        }
        return;
      }
      
      // Handle other messages
      if (typeof handleWS === "function") {
        handleWS(msg);
      }
    } catch (error) {
      console.error("⚠️ Failed to parse WS message:", error, event.data);
    }
  };

  socket.onclose = (event) => {
    console.log(`🔴 WebSocket disconnected. Code: ${event.code}, Reason: ${event.reason || 'No reason'}`);
    updateWSStatus("disconnected");
    
    // Don't reconnect if it was a manual close or authentication error
    if (event.code === 1000 || event.code === 1008) {
      console.log("WebSocket closed intentionally or due to auth error");
      socket = null;
      if (typeof onWSDisconnected === "function") {
        onWSDisconnected();
      }
      return;
    }
    
    // Attempt to reconnect
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      reconnectAttempts++;
      const delay = Math.min(3000 * reconnectAttempts, 30000); // Max 30 seconds
      console.log(`Reconnecting... Attempt ${reconnectAttempts} in ${delay}ms`);
      
      reconnectTimeout = setTimeout(() => {
        connectWS();
      }, delay);
    } else {
      console.error("Max reconnection attempts reached");
      if (typeof showError === "function") {
        showError("WebSocket connection failed. Please refresh the page.");
      }
    }
    
    if (typeof onWSDisconnected === "function") {
      onWSDisconnected();
    }
  };

  socket.onerror = (error) => {
    console.error("⚠️ WebSocket error:", error);
    updateWSStatus("disconnected");
  };
}

function sendWS(action, data = {}) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    console.error("WebSocket not connected");
    if (typeof showError === "function") {
      showError("WebSocket not connected. Attempting to reconnect...");
    }
    // Try to reconnect
    const token = localStorage.getItem("token");
    if (token) {
      connectWS();
    }
    return false;
  }
  
  const message = { action, ...data };
  try {
    socket.send(JSON.stringify(message));
    console.log("➡️ Sent:", message);
    return true;
  } catch (error) {
    console.error("Error sending WebSocket message:", error);
    if (typeof showError === "function") {
      showError("Failed to send message. Please try again.");
    }
    return false;
  }
}

function disconnectWS() {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }
  
  if (socket) {
    socket.close(1000, "Manual disconnect");
    socket = null;
  }
  
  updateWSStatus("disconnected");
}

function isWSConnected() {
  return socket && socket.readyState === WebSocket.OPEN;
}

// Auto-connect on page load if token exists
if (typeof window !== "undefined") {
  window.addEventListener("load", () => {
    const token = localStorage.getItem("token");
    if (token) {
      // Small delay to ensure DOM is ready
      setTimeout(() => {
        connectWS();
      }, 500);
    }
  });
  
  // Reconnect on visibility change (when tab becomes visible)
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      const token = localStorage.getItem("token");
      if (token && (!socket || socket.readyState !== WebSocket.OPEN)) {
        console.log("Tab visible, reconnecting WebSocket...");
        connectWS();
      }
    }
  });
  
  // Reconnect on focus
  window.addEventListener("focus", () => {
    const token = localStorage.getItem("token");
    if (token && (!socket || socket.readyState !== WebSocket.OPEN)) {
      console.log("Window focused, reconnecting WebSocket...");
      connectWS();
    }
  });
  
  // Clean up on page unload
  window.addEventListener("beforeunload", () => {
    disconnectWS();
  });
}

// Export for use in other scripts
if (typeof window !== "undefined") {
  window.connectWS = connectWS;
  window.disconnectWS = disconnectWS;
  window.sendWS = sendWS;
  window.isWSConnected = isWSConnected;
}
