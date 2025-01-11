
  
  const li = document.querySelectorAll('li.dropdown a');
  const btn = document.querySelector('.nav-btn');
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
  })

// stąd biore tutorial
  // https://codepen.io/fazley_rabby/pen/rNxVRWx