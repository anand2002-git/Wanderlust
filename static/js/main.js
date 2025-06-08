document.addEventListener('DOMContentLoaded', function() {
    // Initialize date pickers
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        if (!input.value) {
            const today = new Date().toISOString().split('T')[0];
            input.value = today;
        }
    });

    // Form submission handling
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitButtons = form.querySelectorAll('button[type="submit"]');
            submitButtons.forEach(button => {
                button.disabled = true;
                button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            });
        });
    });

    // Image preview for forms
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const previewContainer = document.createElement('div');
            previewContainer.className = 'image-preview mt-2';
            
            if (this.files && this.files.length > 0) {
                for (let i = 0; i < this.files.length; i++) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        img.className = 'img-thumbnail mr-2 mb-2';
                        img.style.maxHeight = '100px';
                        previewContainer.appendChild(img);
                    }
                    reader.readAsDataURL(this.files[i]);
                }
            }
            
            const existingPreview = this.nextElementSibling;
            if (existingPreview && existingPreview.classList.contains('image-preview')) {
                existingPreview.remove();
            }
            
            this.after(previewContainer);
        });
    });
    

    // Mobile Menu Toggle
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', () => {
            mobileMenu.classList.toggle('open');
        });
    }
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
                
                // Close mobile menu if open
                if (mobileMenu && mobileMenu.classList.contains('open')) {
                    mobileMenu.classList.remove('open');
                }
            }
        });
    });
    
    // Scroll animation for sections
    const sections = document.querySelectorAll('section');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fadeIn');
            }
        });
    }, {
        threshold: 0.1
    });
    
    sections.forEach(section => {
        observer.observe(section);
    });
    
    // Highlight active nav link
    const currentUrl = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === currentUrl) {
            link.classList.add('text-secondary');
            link.classList.remove('text-light');
        }
    });

    // File input label update
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const files = e.target.files;
            const label = fileInput.nextElementSibling;
            if (files.length > 1) {
                label.textContent = files.length + ' files selected';
            } else if (files.length === 1) {
                label.textContent = files[0].name;
            }
        });
    }
});