import { exportData, importData } from "./api.js";
import { confirmAction } from "./confirm.js";
import { today } from "./dates.js";
import { element } from "./dom.js";

/** Export all data as a JSON file and import such a file back (replacing everything). */
export function initDataTransfer({ onImported }) {
  const status = document.getElementById("data-status");
  const fileInput = document.getElementById("import-file");

  function setStatus(message, isError = false) {
    status.textContent = message;
    status.classList.toggle("is-error", isError);
    status.hidden = false;
  }

  function download(text, fileName) {
    const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    const link = element("a");
    link.href = url;
    link.download = fileName;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  async function exportAll() {
    try {
      const data = await exportData();
      download(JSON.stringify(data, null, 2), `trakko-export-${today()}.json`);
      setStatus("Exported all data.");
    } catch (failure) {
      setStatus(`Export failed: ${failure.message}`, true);
    }
  }

  async function importFile(file) {
    let document_;
    try {
      document_ = JSON.parse(await file.text());
    } catch {
      setStatus("This file is not valid JSON.", true);
      return;
    }
    const accepted = await confirmAction({
      title: "Replace all data?",
      message: `Importing “${file.name}” deletes all current Tracks, event types and entries and replaces them with the content of the file. This cannot be undone.`,
      confirmLabel: "Import",
    });
    if (!accepted) return;
    try {
      await importData(document_);
    } catch (failure) {
      setStatus(`Import failed: ${failure.message}`, true);
      return;
    }
    setStatus("Import complete.");
    onImported();
  }

  document.getElementById("export-button").addEventListener("click", exportAll);
  document.getElementById("import-button").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    const [file] = fileInput.files;
    fileInput.value = "";
    if (file) importFile(file);
  });
}
