import { ApiError, getAuthStatus, login } from "./api.js";

function promptLogin() {
  const section = document.getElementById("login");
  const form = document.getElementById("login-form");
  const input = document.getElementById("login-password");
  const error = document.getElementById("login-error");

  section.hidden = false;
  input.focus();

  return new Promise((resolve) => {
    form.addEventListener("submit", async function onSubmit(event) {
      event.preventDefault();
      error.hidden = true;
      try {
        await login(input.value);
      } catch (failure) {
        error.textContent = failure instanceof ApiError ? failure.message : "Sign-in failed.";
        error.hidden = false;
        input.select();
        return;
      }
      form.removeEventListener("submit", onSubmit);
      input.value = "";
      section.hidden = true;
      resolve();
    });
  });
}

/** Resolve once the user may use the API, asking for the password if the server needs one. */
export async function ensureAuthenticated() {
  let status;
  try {
    status = await getAuthStatus();
  } catch (error) {
    // Offline: let the data requests try the cache instead of blocking the whole app.
    if (error instanceof ApiError && (error.status === 0 || error.status === 503)) return;
    throw error;
  }
  if (status.auth_required && !status.authenticated) await promptLogin();
}
