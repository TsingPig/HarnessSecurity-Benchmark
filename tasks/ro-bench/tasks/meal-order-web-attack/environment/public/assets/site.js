const state = { items: [], cart: [], category: 'All' };
const money = cents => `$${(cents / 100).toFixed(2)}`;
const grid = document.getElementById('menu-grid');
const tabs = document.getElementById('category-tabs');

async function loadMenu() {
  const response = await fetch('/api/menu');
  state.items = (await response.json()).items;
  renderMenu();
}

function renderMenu() {
  const categories = ['All', ...new Set(state.items.map(item => item.category))];
  tabs.innerHTML = categories.map(category => `<button type="button" data-category="${category}" class="${category === state.category ? 'active' : ''}">${category}</button>`).join('');
  grid.innerHTML = state.items.filter(item => state.category === 'All' || item.category === state.category).map(item => `
    <article class="menu-card" data-id="${item.id}">
      <img src="${item.image}" alt="${item.name}">
      <div class="details"><small>${item.category}</small><h3>${item.name}</h3>
        <div class="card-bottom"><strong>${money(item.price_cents)}</strong><button type="button" data-add="${item.id}">Add +</button></div>
      </div>
    </article>`).join('');
}

tabs.addEventListener('click', event => {
  if (!event.target.dataset.category) return;
  state.category = event.target.dataset.category;
  renderMenu();
});

grid.addEventListener('click', event => {
  const id = event.target.dataset.add;
  if (!id) return;
  // TODO: add quantities and available add-ons, then update cart and quote.
  state.cart.push({ id, quantity: 1, addons: [] });
});

document.getElementById('place-order').addEventListener('click', () => {
  // TODO: request a quote, submit one idempotent order, and show receipt/cancel action.
  document.getElementById('order-message').textContent = 'Checkout is not ready yet.';
});

loadMenu().catch(error => {
  grid.textContent = `Menu unavailable: ${error.message}`;
});
