document.addEventListener('DOMContentLoaded', () => {
  const li = document.querySelectorAll('li.dropdown a');
  const btn = document.querySelector('.nav-btn');
  const nav = document.querySelector('ul.nav');

  // Safely add toggle to nav button
  if (btn && nav) {
    btn.addEventListener('click', e => {
      nav.classList.toggle('toggle');
    });
  }

  // Dropdown logic
  li.forEach((each) => {
    if (each.nextElementSibling !== null) {
      each.addEventListener('click', e => {
        if (window.innerWidth < 768) {
          e.target.parentElement.classList.toggle("active");
        }
      });
    }
  });
});

// Close popup
function closePopup(x) {
  const popup = document.getElementById(x);
  const blur = document.getElementById('blur');

  if (popup && blur) {
    popup.style.display = 'none';
    blur.style.display = 'none';
  }
}

// Open or toggle popup
function togglePopup(x) {
  const popup = document.getElementById(x);
  const blur = document.getElementById('blur');

  if (popup && blur) {
    const isHidden = popup.style.display === 'none' || popup.style.display === '';
    popup.style.display = isHidden ? 'block' : 'none';
    blur.style.display = isHidden ? 'block' : 'none';
  }
}

// Escape key closes popup with ID 'x'
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    const popup = document.getElementById('x');
    const blur = document.getElementById('blur');

    if (popup) popup.style.display = 'none';
    if (blur) blur.style.display = 'none';
  }
});

// Toggle actions menu
function toggleMenu(menuId) {
  // Close all other menus
  document.querySelectorAll('.actions-menu').forEach(menu => {
    if (menu.id !== menuId) {
      menu.style.display = 'none';
    }
  });

  // Toggle selected menu
  const menu = document.getElementById(menuId);
  if (menu) {
    menu.style.display = (menu.style.display === 'none' || menu.style.display === '') ? 'block' : 'none';
  }

  // Close all submenus
  document.querySelectorAll('.submenu').forEach(submenu => {
    submenu.style.display = 'none';
  });
}
