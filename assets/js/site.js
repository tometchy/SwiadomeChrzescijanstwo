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


/* Galeria: miniatury, poprzednie/następne zdjęcie i nawigacja klawiaturą. */
document.querySelectorAll('[data-book-gallery]').forEach(gallery => {
  const large = gallery.querySelector('.book-cover > img');
  const thumbnails = Array.from(gallery.querySelectorAll('[data-gallery-image]'));
  const counter = gallery.querySelector('[data-gallery-count]');
  if (!large || thumbnails.length < 2) return;

  let selectedIndex = 0;
  function show(index) {
    selectedIndex = (index + thumbnails.length) % thumbnails.length;
    const selected = thumbnails[selectedIndex];
    large.src = selected.dataset.galleryImage;
    large.alt = selected.dataset.galleryAlt || '';
    large.style.display = 'block';
    thumbnails.forEach((thumb, i) => thumb.setAttribute('aria-pressed', String(i === selectedIndex)));
    if (counter) counter.textContent = (selectedIndex + 1) + ' / ' + thumbnails.length;
  }
  thumbnails.forEach((thumb, index) => thumb.addEventListener('click', () => show(index)));
  gallery.querySelector('[data-gallery-prev]')?.addEventListener('click', () => show(selectedIndex - 1));
  gallery.querySelector('[data-gallery-next]')?.addEventListener('click', () => show(selectedIndex + 1));
  gallery.addEventListener('keydown', (event) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    if (!gallery.contains(document.activeElement)) return;
    event.preventDefault();
    show(selectedIndex + (event.key === 'ArrowRight' ? 1 : -1));
    thumbnails[selectedIndex].focus();
  });
});
