
function getToken() {
  return localStorage.getItem("token");
}

function showError(message) {
  const errorDiv = document.getElementById("error");
  if (errorDiv) {
    errorDiv.textContent = message;
    errorDiv.classList.add("show");
    setTimeout(() => errorDiv.classList.remove("show"), 5000);
  } else {
    alert(message);
  }
}

function showSuccess(message) {
  const successDiv = document.getElementById("success");
  if (successDiv) {
    successDiv.textContent = message;
    successDiv.classList.add("show");
    setTimeout(() => successDiv.classList.remove("show"), 3000);
  }
}

// Rider Functions
async function requestRide() {
  const pickup = document.getElementById("pickup")?.value.trim();
  const dropoff = document.getElementById("dropoff")?.value.trim();

  if (!pickup || !dropoff) {
    showError("Please enter both pickup and dropoff locations");
    return;
  }

  const token = getToken();
  if (!token) {
    showError("Please login first");
    window.location.href = "/static/login.html";
    return;
  }

  // Try WebSocket first if available
  if (typeof isWSConnected === "function" && isWSConnected()) {
    const sent = sendWS("ride_requested", { pickup, dropoff });
    if (sent) {
      showSuccess("Ride request sent! Waiting for confirmation...");
      // Clear inputs
      document.getElementById("pickup").value = "";
      document.getElementById("dropoff").value = "";
      return;
    }
  }

  // Fallback to REST API
  try {
    const res = await fetch(`${BASE_URL}/rides/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ pickup, dropoff }),
    });

    if (!res.ok) {
      const error = await res.json();
      showError(error.detail || "Failed to request ride");
      return;
    }

    const data = await res.json();
    showSuccess("Ride requested successfully!");
    
    // Clear inputs
    document.getElementById("pickup").value = "";
    document.getElementById("dropoff").value = "";
    
    // Refresh rides
    if (typeof loadMyRides === "function") {
      loadMyRides();
    }
  } catch (error) {
    showError("Network error. Please try again.");
  }
}

async function loadMyRides() {
  const token = getToken();
  if (!token) return;

  try {
    const res = await fetch(`${BASE_URL}/rides/my`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) return;

    const rides = await res.json();
    displayRides(rides, "rides");
  } catch (error) {
    console.error("Error loading rides:", error);
  }
}

async function assignRide(rideId) {
  const token = getToken();
  if (!token) {
    showError("Please login first");
    return;
  }

  // Try WebSocket first if available
  if (typeof isWSConnected === "function" && isWSConnected()) {
    const sent = sendWS("ride_assigned", { ride_id: parseInt(rideId) });
    if (sent) {
      showSuccess("Accepting ride...");
      return;
    }
  }

  // Fallback to REST API
  try {
    const res = await fetch(`${BASE_URL}/rides/${rideId}/assign`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) {
      const error = await res.json();
      showError(error.detail || "Failed to assign ride");
      return;
    }

    const data = await res.json();
    showSuccess("Ride assigned successfully!");
    
    // Refresh ride requests and assigned rides
    if (typeof loadRideRequests === "function") {
      loadRideRequests();
    }
    if (typeof loadAssignedRides === "function") {
      loadAssignedRides();
    }
  } catch (error) {
    showError("Network error. Please try again.");
  }
}

async function completeRide(rideId) {
  const token = getToken();
  if (!token) {
    showError("Please login first");
    return;
  }

  // Try WebSocket first if available
  if (typeof isWSConnected === "function" && isWSConnected()) {
    const sent = sendWS("ride_completed", { ride_id: parseInt(rideId) });
    if (sent) {
      showSuccess("Completing ride...");
      return;
    }
  }

  // Fallback to REST API
  try {
    const res = await fetch(`${BASE_URL}/rides/${rideId}/complete`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) {
      const error = await res.json();
      showError(error.detail || "Failed to complete ride");
      return;
    }

    const data = await res.json();
    showSuccess("Ride completed successfully!");
    
    // Refresh assigned rides
    if (typeof loadAssignedRides === "function") {
      loadAssignedRides();
    }
  } catch (error) {
    showError("Network error. Please try again.");
  }
}

async function loadRideRequests() {
  const token = getToken();
  if (!token) return;

  try {
    const res = await fetch(`${BASE_URL}/rides/`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) return;

    const rides = await res.json();
    const requestedRides = rides.filter(r => r.status === "requested");
    displayRideRequests(requestedRides);
  } catch (error) {
    console.error("Error loading ride requests:", error);
  }
}

async function loadAssignedRides() {
  const token = getToken();
  if (!token) return;

  try {
    const res = await fetch(`${BASE_URL}/rides/assigned`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) return;

    const rides = await res.json();
    displayRides(rides, "assignedRides");
  } catch (error) {
    console.error("Error loading assigned rides:", error);
  }
}

function displayRides(rides, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (rides.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <p>No rides yet</p>
      </div>
    `;
    return;
  }

  container.innerHTML = rides.map(ride => `
    <div class="ride-card" data-ride-id="${ride.id}">
      <div class="ride-info">
        <div class="ride-location">
          <strong>📍 Pickup:</strong> ${ride.pickup}
          <br>
          <strong>🎯 Dropoff:</strong> ${ride.dropoff}
        </div>
        <span class="status-badge status-${ride.status}">${ride.status}</span>
      </div>
      ${ride.driver_id ? `<p><strong>Driver ID:</strong> ${ride.driver_id}</p>` : ""}
      <p><small>Created: ${new Date(ride.created_at).toLocaleString()}</small></p>
      ${ride.status === "assigned" && typeof completeRide === "function" ? `
        <div class="ride-actions">
          <button onclick="completeRide(${ride.id})" class="secondary">Complete Ride</button>
        </div>
      ` : ""}
    </div>
  `).join("");
}

function displayRideRequests(rides) {
  const container = document.getElementById("rideRequests");
  if (!container) return;

  if (rides.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <p>No ride requests at the moment</p>
      </div>
    `;
    return;
  }

  container.innerHTML = rides.map(ride => `
    <div class="ride-card new" data-ride-id="${ride.id}">
      <div class="ride-info">
        <div class="ride-location">
          <strong>📍 Pickup:</strong> ${ride.pickup}
          <br>
          <strong>🎯 Dropoff:</strong> ${ride.dropoff}
        </div>
        <span class="status-badge status-${ride.status}">${ride.status}</span>
      </div>
      <p><small>Rider ID: ${ride.user_id} | Created: ${new Date(ride.created_at).toLocaleString()}</small></p>
      <div class="ride-actions">
        <button onclick="assignRide(${ride.id})" class="secondary">Accept Ride</button>
      </div>
    </div>
  `).join("");
}

// WebSocket message handler
function handleWS(data) {
  console.log("Handling WS message:", data);

  // New ride notification for drivers
  if (data.event === "new_ride" || data.type === "ride_created") {
    const rideId = data.ride_id;
    const pickup = data.pickup;
    const dropoff = data.dropoff;
    
    if (rideId && pickup && dropoff) {
      showSuccess(`🚕 New ride request: ${pickup} → ${dropoff}`);
      
      // Play notification sound (optional)
      if (typeof playNotificationSound === "function") {
        playNotificationSound();
      }
      
      // Add to ride requests if driver dashboard
      if (typeof loadRideRequests === "function") {
        // Small delay to ensure backend has processed
        setTimeout(() => {
          loadRideRequests();
        }, 500);
      }
    }
  }

  // Ride created confirmation for riders
  if (data.event === "ride_created") {
    showSuccess(`✅ Ride created successfully! Ride ID: ${data.ride_id}`);
    if (typeof loadMyRides === "function") {
      setTimeout(() => {
        loadMyRides();
      }, 500);
    }
  }

  // Ride assigned notification for riders
  if (data.event === "ride_assigned") {
    showSuccess("🚗 Your ride has been assigned! Driver is on the way.");
    if (typeof loadMyRides === "function") {
      setTimeout(() => {
        loadMyRides();
      }, 500);
    }
  }

  // Ride assigned success for drivers
  if (data.event === "ride_assigned_success") {
    showSuccess(`✅ Ride ${data.ride_id} assigned successfully!`);
    if (typeof loadRideRequests === "function") {
      loadRideRequests();
    }
    if (typeof loadAssignedRides === "function") {
      setTimeout(() => {
        loadAssignedRides();
      }, 500);
    }
  }

  // Ride completed notification
  if (data.event === "ride_completed" || data.event === "ride_completed_success") {
    showSuccess("🏁 Ride completed!");
    if (typeof loadMyRides === "function") {
      setTimeout(() => {
        loadMyRides();
      }, 500);
    }
    if (typeof loadAssignedRides === "function") {
      setTimeout(() => {
        loadAssignedRides();
      }, 500);
    }
  }

  // Error handling
  if (data.event === "error") {
    showError(data.message || "An error occurred");
  }
}

// Callback when WS connects
function onWSConnected() {
  console.log("WebSocket connected successfully");
  showSuccess("✅ Real-time updates enabled");
  
  // Refresh data when connected
  if (typeof loadMyRides === "function") {
    loadMyRides();
  }
  if (typeof loadRideRequests === "function") {
    loadRideRequests();
  }
  if (typeof loadAssignedRides === "function") {
    loadAssignedRides();
  }
}

// Callback when WS disconnects
function onWSDisconnected() {
  console.log("WebSocket disconnected");
  // Don't show error on intentional disconnect
  if (socket && socket.readyState === WebSocket.CLOSING) {
    return;
  }
  showError("⚠️ Connection lost. Attempting to reconnect...");
}
