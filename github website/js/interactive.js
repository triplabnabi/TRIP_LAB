/**
 * TR(i)P Lab - Interactive JavaScript
 * Enhanced interactivity for the TRP Channels website
 */

// Wrap everything in IIFE for safety
(function() {
  "use strict";

  // ===== Mobile Menu Functionality =====
  function initializeMobileMenu() {
    const mobileToggle = document.querySelector('.mobile-nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (!mobileToggle || !navLinks) return;

    mobileToggle.addEventListener('click', () => {
      const isVisible = navLinks.getAttribute('data-visible') === 'true';
      mobileToggle.setAttribute('aria-expanded', !isVisible);
      navLinks.setAttribute('data-visible', !isVisible);
    });
  }

  // ===== Page Scroll Progress Bar =====
  function initializeScrollProgress() {
    const progressBar = document.getElementById('page-progress');

    if (!progressBar) {
      console.warn('Page progress bar element not found');
      return;
    }

    function updateProgress() {
      const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
      const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const scrolled = (winScroll / height) * 100;

      // Use requestAnimationFrame for smooth performance
      requestAnimationFrame(() => {
        progressBar.style.width = scrolled + "%";
      });
    }

    window.addEventListener('scroll', updateProgress, { passive: true });

    // Initial call in case page is already scrolled
    updateProgress();
  }

  // ===== Intersection Observer for Animations =====
  function initializeAnimations() {
    const animatedElements = document.querySelectorAll('.fade-in-up');
    const observerOptions = {
      threshold: 0.1,
      rootMargin: '-10% 0px -10% 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, observerOptions);

    animatedElements.forEach(el => observer.observe(el));
  }

// ===== Header Scroll Effect =====
function initializeHeaderScroll() {
  const header = document.querySelector('header');

  if (!header) return;

  function updateHeader() {
    const scrolled = window.pageYOffset > 100;
    header.classList.toggle('scrolled', scrolled);
  }

  window.addEventListener('scroll', updateHeader, { passive: true });
}

// ===== Scrolly-telling Timeline =====
function initializeScrollyTelling() {
  const storySteps = document.querySelectorAll('.story-step');
  const timelineProgress = document.getElementById('timeline-progress');
  const timelineNodes = document.querySelectorAll('.timeline-node');

  if (storySteps.length === 0) return;

  let currentActiveStep = 0;

  // Set initial state
  setActiveStep(0);

  // Ensure first step is immediately visible (no fade delay)
  const firstStep = storySteps[0];
  if (firstStep) {
    firstStep.classList.add('is-active');
    firstStep.classList.add('is-visible');
    // Update first timeline node immediately
    const firstNode = timelineNodes[0];
    if (firstNode) {
      firstNode.classList.add('is-active');
    }
  }

  // Create ScrollTrigger for mobile and desktop
  if (typeof ScrollTrigger !== 'undefined') {
    ScrollTrigger.matchMedia({
      "(min-width: 769px)": function() {
        // Desktop scrolly-telling
        storySteps.forEach((step, index) => {
          ScrollTrigger.create({
            trigger: step,
            start: "top center",
            end: "bottom center",
            onEnter: () => setActiveStep(index),
            onEnterBack: () => setActiveStep(index),
          });
        });
      },

      "(max-width: 768px)": function() {
        // Mobile scrolly-telling
        storySteps.forEach((step, index) => {
          ScrollTrigger.create({
            trigger: step,
            start: "top 70%",
            end: "bottom 70%",
            onEnter: () => setActiveStep(index),
            onEnterBack: () => setActiveStep(index),
          });
        });
      }
    });
  } else {
    // Fallback for when ScrollTrigger is not available
    window.addEventListener('scroll', handleScrollFallback, { passive: true });
  }

  function setActiveStep(stepIndex) {
    if (stepIndex === currentActiveStep) return;

    currentActiveStep = stepIndex;

    // Update step opacity
    storySteps.forEach((step, index) => {
      step.classList.toggle('is-active', index === stepIndex);
      step.classList.toggle('is-visible', index === stepIndex);
    });

    // Update timeline nodes
    timelineNodes.forEach((node, index) => {
      node.classList.toggle('is-active', index === stepIndex);
    });

    // Update progress bar - step-based, not scroll-based
    if (timelineProgress) {
      const isMobile = window.innerWidth <= 768;
      const progressPercent = ((stepIndex + 1) / storySteps.length) * 100;

      if (isMobile) {
        timelineProgress.style.width = `${progressPercent}%`;
        timelineProgress.style.height = '100%';
      } else {
        timelineProgress.style.height = `${progressPercent}%`;
        timelineProgress.style.width = '100%';
      }
    }
  }

  function handleScrollFallback() {
    const scrollY = window.scrollY;
    const windowHeight = window.innerHeight;
    const triggerPoint = windowHeight * 0.5;

    storySteps.forEach((step, index) => {
      const rect = step.getBoundingClientRect();
      const stepTop = rect.top;
      const stepBottom = rect.bottom;

      if (stepTop < triggerPoint && stepBottom > triggerPoint) {
        setActiveStep(index);
      }
    });
  }
}



  // ===== Smooth Scrolling for Internal Links =====
  function initializeSmoothScrolling() {
    const internalLinks = document.querySelectorAll('a[href^="#"]');

    internalLinks.forEach(link => {
      link.addEventListener('click', function(e) {
        e.preventDefault();

        const href = this.getAttribute('href');

        // Skip navigation links in mobile menu
        if (this.closest('.nav-links') && window.innerWidth <= 768) {
          mobileToggle.click(); // Close mobile menu first
          setTimeout(() => scrollToTarget(href), 350); // Wait for menu animation
        } else {
          scrollToTarget(href);
        }
      });
    });

    function scrollToTarget(href) {
      if (href === '#') return;

      const targetElement = document.querySelector(href);
      if (targetElement) {
        const offsetTop = href === '#home' ? 0 : targetElement.offsetTop - 100;

        window.scrollTo({
          top: offsetTop,
          behavior: 'smooth'
        });
      }
    }
  }

  // ===== Enhanced Logo Animation =====
  function initializeLogoAnimation() {
    const logo = document.querySelector('.logo');
    const logoContainer = document.querySelector('.logo-container');

    if (!logo || !logoContainer) return;

    let subtitleHovered = false;

    logoContainer.addEventListener('mouseenter', () => {
      if (!subtitleHovered) {
        logo.style.transform = 'translateY(-2px)';
      }
    });

    logoContainer.addEventListener('mouseleave', () => {
      logo.style.transform = 'translateY(0)';
    });

    // Handle subtitle hover to cancel logo animation
    const subtitle = logoContainer.querySelector('.lab-subtitle');
    if (subtitle) {
      subtitle.addEventListener('mouseenter', () => {
        subtitleHovered = true;
        logo.style.transform = 'translateY(0)';
      });

      subtitle.addEventListener('mouseleave', () => {
        subtitleHovered = false;
      });
    }
  }

  // ===== Keyframe Management for Skip Links =====
  function initializeSkipLinks() {
    const skipLink = document.querySelector('.skip-link');

    if (!skipLink) return;

    // Handle keyboard navigation
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        // Show skip link when navigating with keyboard
        skipLink.style.top = '6px';
      }
    });

    // Hide skip link when clicked
    skipLink.addEventListener('click', () => {
      skipLink.style.top = '-40px';
    });
  }

  // ===== Handle Window Resize Events =====
  function handleWindowResize() {
    let resizeTimeout;

    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        // Reset scrolly-telling if needed
        if (typeof ScrollTrigger !== 'undefined') {
          ScrollTrigger.refresh();
        }
      }, 250);
    });
  }

  // ===== Initialize All Features =====
  function initialize() {
    // Ensure DOM is loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initializeAll);
    } else {
      initializeAll();
    }

    function initializeAll() {
      try {
        initializeMobileMenu();
        initializeScrollProgress();
        initializeAnimations();
        initializeHeaderScroll();
        initializeScrollyTelling();
        initializeSmoothScrolling();
        initializeLogoAnimation();
        initializeSkipLinks();
        handleWindowResize();
        // Removed advanced visual algorithms for cleaner design

        console.log('TR(i)P Lab interactive features initialized successfully');
        console.log('🎨 Clean and simple design - computer vision algorithms removed');
      } catch (error) {
        console.error('Error initializing TR(i)P Lab interactive features:', error);
      }
    }
  }



  // ===== Export functions for external use =====
  window.TRIPLab = {
    initialize: initialize,
    initializeMobileMenu: initializeMobileMenu,
    initializeScrollProgress: initializeScrollProgress,
    initializeAnimations: initializeAnimations,
    initializeHeaderScroll: initializeHeaderScroll,
    initializeScrollyTelling: initializeScrollyTelling,
    initializeSmoothScrolling: initializeSmoothScrolling,
    initializeLogoAnimation: initializeLogoAnimation,
    initializeSkipLinks: initializeSkipLinks
  };

  // Auto-initialize when DOM is ready
  initialize();

})();
