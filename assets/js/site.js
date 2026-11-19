(function () {
  'use strict';
  const navButton = document.querySelector('.nav-toggle');
  const nav = document.getElementById('primary-nav');
  if (navButton && nav) {
    navButton.addEventListener('click', () => {
      const expanded = navButton.getAttribute('aria-expanded') === 'true';
      navButton.setAttribute('aria-expanded', String(!expanded));
      navButton.setAttribute('aria-label', expanded ? 'Otwórz menu' : 'Zamknij menu');
      nav.classList.toggle('open', !expanded);
    });
    nav.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
      nav.classList.remove('open');
      navButton.setAttribute('aria-expanded', 'false');
    }));
  }
  const grid = document.getElementById('book-grid');
  if (!grid) return;
  const chips = Array.from(document.querySelectorAll('.filter-chip'));
  const input = document.getElementById('book-search');
  const count = document.getElementById('visible-count');
  const sort = document.getElementById('book-sort');
  const empty = document.getElementById('no-results');
  const cards = Array.from(grid.querySelectorAll('.book-card'));
  let category = '*';
  function normalize(s) { return (s || '').toLocaleLowerCase('pl').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ł/g, 'l'); }
  function applyFilters() {
    const search = normalize(input?.value || '').trim();
    let visible = 0;
    cards.forEach(card => {
      const matches = (category === '*' || card.dataset.category === category) && normalize(card.dataset.search).includes(search);
      card.hidden = !matches;
      if (matches) visible++;
    });
    if (sort) {
      const visibleCards = cards.filter(card => !card.hidden);
      visibleCards.sort((a,b) => {
        if (sort.value === 'title') return a.querySelector('h3').textContent.localeCompare(b.querySelector('h3').textContent, 'pl');
        if (sort.value === 'author') return a.querySelector('.book-author').textContent.localeCompare(b.querySelector('.book-author').textContent, 'pl');
        return Number(b.dataset.order || 0) - Number(a.dataset.order || 0);
      });
      visibleCards.forEach(card => grid.appendChild(card));
    }
    if (count) count.textContent = String(visible);
    if (empty) empty.hidden = visible !== 0;
  }
  chips.forEach(chip => chip.addEventListener('click', () => {
    category = chip.dataset.filter;
    chips.forEach(other => {const selected = other === chip; other.classList.toggle('active', selected); other.setAttribute('aria-pressed', String(selected));});
    applyFilters();
  }));
  input?.addEventListener('input', applyFilters);
  sort?.addEventListener('change', applyFilters);
  document.querySelector('.reset-filters')?.addEventListener('click', () => {
    category = '*'; if (input) input.value = '';
    chips.forEach(chip => {const selected = chip.dataset.filter === '*'; chip.classList.toggle('active', selected); chip.setAttribute('aria-pressed', String(selected));});
    applyFilters();
  });
  applyFilters();
})();


/* Galeria fotografii: przełączanie i powiększenie bez dodatkowych bibliotek. */
document.querySelectorAll('[data-book-gallery]').forEach(gallery => {
  const mainPhoto = gallery.querySelector('.gallery-main-photo');
  if (!mainPhoto) return;
  const thumbnails = Array.from(gallery.querySelectorAll('[data-gallery-image]'));
  const dialog = gallery.querySelector('[data-gallery-dialog]');
  const zoomPhoto = gallery.querySelector('[data-gallery-modal-image]');
  const counter = gallery.querySelector('[data-gallery-count]');
  const modalCounter = gallery.querySelector('[data-gallery-modal-count]');
  const title = mainPhoto.alt;
  let index = 0;
  const images = thumbnails.length
    ? thumbnails.map(button => ({url: button.dataset.galleryImage, alt: button.dataset.galleryAlt || title}))
    : [{url: mainPhoto.src, alt: title}];

  function show(nextIndex) {
    index = (nextIndex + images.length) % images.length;
    const item = images[index];
    mainPhoto.src = item.url;
    mainPhoto.alt = item.alt;
    if (zoomPhoto) {
      zoomPhoto.src = item.url;
      zoomPhoto.alt = item.alt;
    }
    thumbnails.forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
    const progress = (index + 1) + ' / ' + images.length;
    if (counter) counter.textContent = progress;
    if (modalCounter) modalCounter.textContent = progress;
  }

  thumbnails.forEach((button, i) => button.addEventListener('click', () => show(i)));
  gallery.querySelector('[data-gallery-prev]')?.addEventListener('click', () => show(index - 1));
  gallery.querySelector('[data-gallery-next]')?.addEventListener('click', () => show(index + 1));
  gallery.querySelector('[data-gallery-zoom]')?.addEventListener('click', () => {
    if (dialog && !dialog.open) dialog.showModal();
  });
  gallery.querySelector('[data-gallery-close]')?.addEventListener('click', () => dialog?.close());
  gallery.querySelector('[data-gallery-modal-prev]')?.addEventListener('click', () => show(index - 1));
  gallery.querySelector('[data-gallery-modal-next]')?.addEventListener('click', () => show(index + 1));
  dialog?.addEventListener('click', event => {
    if (event.target === dialog) dialog.close();
  });
  gallery.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    if (!gallery.contains(document.activeElement) && !dialog?.open) return;
    event.preventDefault();
    show(index + (event.key === 'ArrowRight' ? 1 : -1));
  });
  show(0);
});
