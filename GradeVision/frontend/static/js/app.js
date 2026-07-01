function logout() {
  localStorage.removeItem("token");
  window.location.href = "/login";
}

function checkAuth() {
  const token = localStorage.getItem("token");
  const currentPath = window.location.pathname;

  if (currentPath !== "/login" && currentPath !== "/" && !token) {
    window.location.href = "/login";
  }

  if (token && (currentPath === "/login" || currentPath === "/")) {
    window.location.href = "/dashboard";
  }
}

document.addEventListener("DOMContentLoaded", checkAuth);
