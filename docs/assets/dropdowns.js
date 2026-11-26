// The page's sections and models are dropdowns (<details>) that start collapsed.
// A link to something inside a collapsed dropdown, such as a model named in an answer,
// would land on a hidden element. This opens the dropdowns around the link's target,
// and the target itself if it is a dropdown, so the browser can scroll to it.
// It only opens dropdowns: without it the pages still work, by opening them by hand.

function openAround(hash) {
  if (!hash || hash.length < 2) return null;
  const target = document.getElementById(decodeURIComponent(hash.slice(1)));
  for (let element = target; element; element = element.parentElement) {
    if (element.tagName === "DETAILS") element.open = true;
  }
  return target;
}

// Before the browser follows an in-page link, open what it points into.
document.addEventListener("click", (event) => {
  const link = event.target.closest('a[href^="#"]');
  if (link) openAround(link.hash);
});

// Arriving with a link from elsewhere, or going back and forward.
function revealCurrent() {
  const target = openAround(location.hash);
  if (target) target.scrollIntoView();
}
window.addEventListener("hashchange", revealCurrent);
revealCurrent();
