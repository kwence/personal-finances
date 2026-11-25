document.addEventListener("DOMContentLoaded", function () {
  const select = document.querySelector("[data-category-select]");
  const radios = document.querySelectorAll('input[name="kind"]');
  const dataNode = document.getElementById("category-kinds");
  if (!select || !radios.length || !dataNode) return;

  const kinds = JSON.parse(dataNode.textContent);
  const allOptions = Array.from(select.options);

  function applyFilter() {
    const chosen = document.querySelector('input[name="kind"]:checked');
    const kind = chosen ? chosen.value : "expense";
    let firstMatch = null;

    allOptions.forEach(function (option) {
      const matches = !option.value || kinds[option.value] === kind;
      option.hidden = !matches;
      option.disabled = !matches;
      if (matches && option.value && !firstMatch) firstMatch = option;
    });

    const currentMatches = select.value && kinds[select.value] === kind;
    if (!currentMatches && firstMatch) select.value = firstMatch.value;
    if (!currentMatches && !firstMatch) select.value = "";
  }

  radios.forEach(function (radio) {
    radio.addEventListener("change", applyFilter);
  });
  applyFilter();
});
