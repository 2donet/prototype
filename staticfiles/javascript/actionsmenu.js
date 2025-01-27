
  
//   const li = document.querySelectorAll('li.dropdown a');
//   const btn = document.querySelector('.nav-btn');
  const nav = document.querySelector('ul.nav');
  
  btn.addEventListener('click', e=>{
      nav.classList.toggle('toggle');
  })
  
  
  li.forEach((each)=>{
      if (each.nextElementSibling !== null) {
          each.addEventListener('click', e=>{
              if (window.innerWidth < 768) {
                e.target.parentElement.classList.toggle("active");  
              }
          })
      }
  });

// stąd biore tutorial
  // https://codepen.io/fazley_rabby/pen/rNxVRWx


  function toggleMenu(menuId) {
    // Close any open menus
    document.querySelectorAll('.actions-menu').forEach(menu => {
        if (menu.id !== menuId) {
            menu.style.display = 'none';
        }
    });

    // Toggle the clicked menu
    const menu = document.getElementById(menuId);
    if (menu.style.display === 'none' || menu.style.display === '') {
        menu.style.display = 'block';
    } else {
        menu.style.display = 'none';
    }

    // Close all submenus
    document.querySelectorAll('.submenu').forEach(submenu => {
        submenu.style.display = 'none';
    });
}
