const BASE_URL = "http://localhost:8000";

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

function setLoading(button, isLoading) {
  if (isLoading) {
    button.disabled = true;
    button.innerHTML = '<span class="loading"></span> Processing...';
  } else {
    button.disabled = false;
    button.innerHTML = button.getAttribute("data-original-text") || "Submit";
  }
}

async function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  if (!email || !password) {
    showError("Please fill in all fields");
    return;
  }

  const button = event.target;
  button.setAttribute("data-original-text", button.textContent);
  setLoading(button, true);

  try {
    const res = await fetch(`${BASE_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const error = await res.json();
      showError(error.detail || "Invalid email or password");
      setLoading(button, false);
      return;
    }

    const data = await res.json();
    localStorage.setItem("token", data.access_token);
    
    showSuccess("Login successful! Redirecting...");
    
    // Try to determine if user is driver by checking assigned rides endpoint
    // Drivers can access /rides/assigned, riders get 403
    setTimeout(async () => {
      try {
        const driverRes = await fetch(`${BASE_URL}/rides/assigned`, {
          headers: { Authorization: `Bearer ${data.access_token}` },
        });
        
        if (driverRes.status === 200 || driverRes.status === 403) {
          // If 200, user is driver; if 403, user is rider
          if (driverRes.status === 200) {
            window.location.href = "/static/dashboard_driver.html";
          } else {
            window.location.href = "/static/dashboard_rider.html";
          }
        } else {
          // Default to rider dashboard
          window.location.href = "/static/dashboard_rider.html";
        }
      } catch (error) {
        // Default to rider dashboard
        window.location.href = "/static/dashboard_rider.html";
      }
    }, 1000);
  } catch (error) {
    showError("Network error. Please try again.");
    setLoading(button, false);
  }
}

async function signup() {
  const name = document.getElementById("name").value.trim();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const isDriver = document.getElementById("isDriver")?.checked || false;

  if (!name || !email || !password) {
    showError("Please fill in all fields");
    return;
  }

  if (password.length < 6) {
    showError("Password must be at least 6 characters");
    return;
  }

  const button = event.target;
  button.setAttribute("data-original-text", button.textContent);
  setLoading(button, true);

  try {
    const res = await fetch(`${BASE_URL}/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password, is_driver: isDriver }),
    });

    if (!res.ok) {
      const error = await res.json();
      showError(error.detail || "Signup failed. Email might already be registered.");
      setLoading(button, false);
      return;
    }

    const data = await res.json();
    showSuccess("Signup successful! Redirecting to login...");
    
    setTimeout(() => {
      window.location.href = "/static/login.html";
    }, 1500);
  } catch (error) {
    showError("Network error. Please try again.");
    setLoading(button, false);
  }
}

function logout() {
  if (confirm("Are you sure you want to logout?")) {
    localStorage.clear();
    window.location.href = "/static/login.html";
  }
}

// Check if user is already logged in
function checkAuth() {
  const token = localStorage.getItem("token");
  if (!token) {
    return false;
  }
  return true;
}

// Redirect if not authenticated
function requireAuth() {
  if (!checkAuth()) {
    window.location.href = "/static/login.html";
  }
}
