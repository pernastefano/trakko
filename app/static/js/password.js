import { ApiError, changePassword } from "./api.js";

/** Dialog to change the signed-in user's password. Calls `onChanged()` after it succeeded. */
export function createPasswordDialog({ onChanged }) {
  const dialog = document.getElementById("password-dialog");
  const form = document.getElementById("password-form");
  const current = document.getElementById("password-current");
  const next = document.getElementById("password-new");
  const confirm = document.getElementById("password-confirm");
  const error = document.getElementById("password-error");
  const save = document.getElementById("password-save");

  function showError(message) {
    error.textContent = message ?? "";
    error.hidden = !message;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showError(null);
    if (next.value.length < 8) {
      showError("The new password must be at least 8 characters.");
      next.focus();
      return;
    }
    if (next.value !== confirm.value) {
      showError("The two new passwords do not match.");
      confirm.focus();
      return;
    }
    save.disabled = true;
    try {
      await changePassword(current.value, next.value);
    } catch (failure) {
      showError(failure instanceof ApiError ? failure.message : "Something went wrong.");
      return;
    } finally {
      save.disabled = false;
    }
    dialog.close();
    form.reset();
    onChanged();
  });

  document.getElementById("password-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  return {
    open() {
      form.reset();
      showError(null);
      dialog.showModal();
      current.focus();
    },
  };
}
