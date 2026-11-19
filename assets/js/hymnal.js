(() => {
  "use strict";
  const input = document.getElementById("hymnal-search");
  const list = document.getElementById("hymnal-list");
  if (!input || !list) return;
  const count = document.getElementById("hymnal-count");
  const empty = document.getElementById("hymnal-empty");
  const normalize = s => String(s || "").toLocaleLowerCase("pl")
    .normalize("NFKD").replace(/\p{M}/gu, "").replace(/ł/g, "l")
    .replace(/[^\p{L}\p{N}]+/gu, " ").replace(/\s+/g, " ").trim();
  const entries = [...list.querySelectorAll("[data-hymnal-item]")]
    .map(element => ({ element, text: normalize(element.dataset.search), number: element.dataset.number }));
  const filter = () => {
    const query = normalize(input.value);
    const terms = query.split(" ").filter(Boolean);
    let visible = 0;
    entries.forEach(({element, text, number}) => {
      const match = terms.length === 0 || terms.every(term => text.includes(term) || number === term);
      element.hidden = !match;
      if (match) visible++;
    });
    if (count) count.textContent = visible + " / " + entries.length + " pieśni";
    if (empty) empty.hidden = visible > 0;
  };
  input.addEventListener("input", filter);
  filter();
})();
