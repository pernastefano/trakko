const dialog = document.getElementById("confirm-dialog");
const title = document.getElementById("confirm-title");
const message = document.getElementById("confirm-message");
const accept = document.getElementById("confirm-accept");

/** Ask for confirmation of a destructive action; resolves to true only if the user accepts. */
export function confirmAction({ title: heading, message: text, confirmLabel = "Delete" }) {
  title.textContent = heading;
  message.textContent = text;
  accept.textContent = confirmLabel;
  dialog.returnValue = "";
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm"), {
      once: true,
    });
    dialog.showModal();
  });
}
