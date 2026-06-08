document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-copy]");
  if (!target) return;
  const text = target.getAttribute("data-copy");
  if (text && navigator.clipboard) {
    navigator.clipboard.writeText(text);
  }
});

document.body.addEventListener("htmx:afterRequest", (event) => {
  if (event.detail.failed) {
    const container = document.getElementById("toast-container");
    if (container) {
      container.innerHTML = '<div class="card" style="background:#fee2e2;border-color:#fca5a5">Request failed. Please try again.</div>';
      setTimeout(() => { container.innerHTML = ""; }, 4000);
    }
  }
});
