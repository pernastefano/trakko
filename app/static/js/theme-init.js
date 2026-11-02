// Runs before the page is drawn (it is a plain script in <head>) so the saved theme is applied
// without a flash of the default one. theme.js owns the theme list and the rest of the logic.
(function () {
  try {
    var id = localStorage.getItem("trakko.theme");
    if (id && id !== "auto" && /^[a-z]+$/.test(id)) {
      document.documentElement.setAttribute("data-theme", id);
    }
  } catch (error) {
    // Storage can be unavailable (private mode); the automatic theme is used.
  }
})();
