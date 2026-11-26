if (navigator.clipboard) {
  document.querySelectorAll("pre").forEach(pre => {
    const wrap = document.createElement("div");
    wrap.className = "code-wrap";
    pre.before(wrap);
    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "copy";
    copy.textContent = "Copy";
    copy.setAttribute("aria-label", "Copy command block");
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(pre.textContent.trimEnd());
        copy.textContent = "Copied";
      } catch {
        const range = document.createRange();
        range.selectNodeContents(pre);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        copy.textContent = "Selected";
      }
      setTimeout(() => { copy.textContent = "Copy"; }, 1800);
    });
    wrap.append(pre, copy);
  });
}
