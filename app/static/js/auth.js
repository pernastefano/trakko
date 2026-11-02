import { ApiError, getAuthStatus, login, register } from "./api.js";

const OFFLINE_STATUSES = [0, 503];

function promptLogin(initialStatus) {
  const section = document.getElementById("login");
  const form = document.getElementById("login-form");
  const subtitle = document.getElementById("login-subtitle");
  const username = document.getElementById("login-username");
  const password = document.getElementById("login-password");
  const confirmField = document.getElementById("login-confirm-field");
  const confirmPassword = document.getElementById("login-password-confirm");
  const hint = document.getElementById("login-hint");
  const error = document.getElementById("login-error");
  const submit = document.getElementById("login-submit");
  const switchButton = document.getElementById("login-switch");

  let registering = false;

  function showError(message) {
    error.textContent = message ?? "";
    error.hidden = !message;
  }

  function setMode(creating) {
    registering = creating;
    subtitle.textContent = creating ? "Create your account" : "Sign in to continue";
    submit.textContent = creating ? "Create account" : "Sign in";
    switchButton.textContent = creating ? "I already have an account" : "Create an account";
    // A closed installation can still be signed in to; the account form is only offered if open.
    switchButton.hidden = !creating && !initialStatus.registration_open;
    confirmField.hidden = hint.hidden = !creating;
    confirmPassword.required = creating;
    password.autocomplete = creating ? "new-password" : "current-password";
    showError(null);
  }

  setMode(false);
  section.hidden = false;
  username.focus();

  switchButton.addEventListener("click", () => {
    setMode(!registering);
    username.focus();
  });

  return new Promise((resolve) => {
    form.addEventListener("submit", async function onSubmit(event) {
      event.preventDefault();
      showError(null);
      if (registering && password.value !== confirmPassword.value) {
        showError("The two passwords do not match.");
        confirmPassword.focus();
        return;
      }
      submit.disabled = true;
      let status;
      try {
        status = registering
          ? await register(username.value, password.value)
          : await login(username.value, password.value);
      } catch (failure) {
        showError(failure instanceof ApiError ? failure.message : "Something went wrong.");
        password.select();
        return;
      } finally {
        submit.disabled = false;
      }
      form.removeEventListener("submit", onSubmit);
      form.reset();
      section.hidden = true;
      resolve(status);
    });
  });
}

/**
 * Resolve with the auth status once somebody is signed in, asking for an account first if needed.
 * Resolves with null when the server cannot be reached (the cached app can still be shown).
 */
export async function ensureAuthenticated() {
  let status;
  try {
    status = await getAuthStatus();
  } catch (error) {
    if (error instanceof ApiError && OFFLINE_STATUSES.includes(error.status)) return null;
    throw error;
  }
  return status.authenticated ? status : promptLogin(status);
}
