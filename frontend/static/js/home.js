// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', () => {
  initStickyNavbar();
  initAnimatedCards();
  initDiseaseCardsSwapping();
  initSmoothScrolling();
  initCountAnimation();
});

// Sticky Navbar with Progress Indicator
function initStickyNavbar() {
  const navbar = document.querySelector(".navbar");
  let lastScroll = 0;

  window.addEventListener("scroll", () => {
    const currentScroll = window.pageYOffset;

    // Add/remove sticky class
    if (currentScroll > 50) {
      navbar.classList.add("sticky-navbar");
    } else {
      navbar.classList.remove("sticky-navbar");
    }

    // Hide/show navbar based on scroll direction
    if (currentScroll > lastScroll && currentScroll > 100) {
      navbar.style.transform = "translateY(-100%)";
    } else {
      navbar.style.transform = "translateY(0)";
    }

    lastScroll = currentScroll;
  });
}

// Enhanced Card Animations
function initAnimatedCards() {
  const animatedCards = document.querySelectorAll(".animated-card");

  // Add hover animations
  animatedCards.forEach((card) => {
    card.addEventListener("mouseenter", () => {
      card.style.transform = "translateY(-10px)";
    });

    card.addEventListener("mouseleave", () => {
      card.style.transform = "translateY(0)";
    });

    // Add reveal animation when card comes into view
    observeCardReveal(card);
  });
}

// Observe cards for reveal animation
function observeCardReveal(element) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = "1";
          entry.target.style.transform = "translateY(0)";
          observer.unobserve(entry.target);
        }
      });
    },
    {
      threshold: 0.1,
      rootMargin: "0px"
    }
  );

  element.style.opacity = "0";
  element.style.transform = "translateY(20px)";
  element.style.transition = "all 0.6s ease-out";
  observer.observe(element);
}

// Enhanced Disease Cards Swapping
function initDiseaseCardsSwapping() {
  let currentGroup = 1;
  const totalGroups = 2;
  let isAnimating = false;

  function swapCards() {
    if (isAnimating) return;
    isAnimating = true;

    const currentCards = document.querySelectorAll(`.group-${currentGroup}`);
    const nextGroup = (currentGroup % totalGroups) + 1;
    const nextCards = document.querySelectorAll(`.group-${nextGroup}`);

    // Fade out current group with stagger effect
    currentCards.forEach((card, index) => {
      setTimeout(() => {
        card.classList.add('fade-out');
      }, index * 100);
    });

    // After fade out animation
    setTimeout(() => {
      currentCards.forEach(card => {
        card.style.display = 'none';
        card.classList.remove('fade-out');
      });

      // Show and fade in next group with stagger effect
      nextCards.forEach((card, index) => {
        card.style.display = 'block';
        setTimeout(() => {
          card.classList.add('fade-in');
        }, index * 100);
      });

      // Remove fade-in class after animation
      setTimeout(() => {
        nextCards.forEach(card => {
          card.classList.remove('fade-in');
        });
        isAnimating = false;
      }, 600);

      currentGroup = nextGroup;
    }, 600);
  }

  // Initialize first group
  document.querySelectorAll('.group-1').forEach(card => {
    card.style.display = 'block';
    card.style.opacity = '1';
  });

  // Hide second group initially
  document.querySelectorAll('.group-2').forEach(card => {
    card.style.display = 'none';
  });

  // Start the interval for card swapping
  setInterval(swapCards, 5000);

  // Add manual navigation buttons (optional)
  const createNavButtons = () => {
    const container = document.querySelector('.diseases-carousel .container');
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'text-center mt-4';

    const prevButton = document.createElement('button');
    prevButton.className = 'btn btn-outline-primary mx-2';
    prevButton.innerHTML = '<i class="fas fa-chevron-left"></i>';

    const nextButton = document.createElement('button');
    nextButton.className = 'btn btn-outline-primary mx-2';
    nextButton.innerHTML = '<i class="fas fa-chevron-right"></i>';

    buttonContainer.appendChild(prevButton);
    buttonContainer.appendChild(nextButton);
    container.appendChild(buttonContainer);

    prevButton.addEventListener('click', () => {
      if (!isAnimating) {
        currentGroup = currentGroup === 1 ? totalGroups : currentGroup - 1;
        swapCards();
      }
    });

    nextButton.addEventListener('click', () => {
      if (!isAnimating) {
        swapCards();
      }
    });
  };

  createNavButtons();
}

// Smooth Scrolling
function initSmoothScrolling() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));

      if (target) {
        // Close mobile menu if open
        const navbarToggler = document.querySelector('.navbar-toggler');
        const navbarCollapse = document.querySelector('.navbar-collapse');
        if (navbarCollapse.classList.contains('show')) {
          navbarToggler.click();
        }

        // Smooth scroll to target
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });
}

// Animate Numbers Section
function initCountAnimation() {
  const numberElements = document.querySelectorAll('.numbers-section h3');

  const animateValue = (element, start, end, duration) => {
    let startTimestamp = null;
    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      const currentValue = Math.floor(progress * (end - start) + start);
      element.textContent = currentValue.toLocaleString();
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };
    window.requestAnimationFrame(step);
  };

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const element = entry.target;
          const endValue = parseInt(element.textContent.replace(/,/g, ''));
          animateValue(element, 0, endValue, 2000);
          observer.unobserve(element);
        }
      });
    },
    {
      threshold: 0.5
    }
  );

  numberElements.forEach(element => {
    observer.observe(element);
  });
}

// Handle form submissions (if needed)
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    console.log('Form submitted');
  });
});

// Add loading animation
window.addEventListener('load', () => {
  document.body.classList.add('loaded');
});
document.getElementById('feedbackForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const email = document.getElementById('feedbackEmail').value;
  const message = document.getElementById('feedbackMessage').value;
  const statusDiv = document.getElementById('feedbackStatus');
  const spinner = document.querySelector('.loading-spinner');
  
  // Show loading spinner
  spinner.classList.remove('d-none');
  
  try {
      const response = await fetch('/send_feedback', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email, message })
      });
      
      const data = await response.json();
      
      if (response.ok) {
          statusDiv.innerHTML = '<div class="alert alert-success">Thank you for your feedback!</div>';
          document.getElementById('feedbackEmail').value = '';
          document.getElementById('feedbackMessage').value = '';
      } else {
          statusDiv.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
      }
  } catch (error) {
      statusDiv.innerHTML = '<div class="alert alert-danger">An error occurred. Please try again.</div>';
  } finally {
      // Hide loading spinner
      spinner.classList.add('d-none');
  }
});
