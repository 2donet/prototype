
  
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


  function togglePopup(x) {
    const popup = document.getElementById(x);
    if (popup.style.display === 'none' || popup.style.display === '') {
        popup.style.display = 'block';
      } else {
          popup.style.display = 'none';
      }
  };
function closePopup (x) {
    const popup = document.getElementById(x);
    if (popup.style.display === 'block') {
        popup.style.display = 'none';
  } else {
      popup.style.display = 'none';
  } if (e.key === "Escape") {
    document.getElementById('x').style.display = 'none'}
};
