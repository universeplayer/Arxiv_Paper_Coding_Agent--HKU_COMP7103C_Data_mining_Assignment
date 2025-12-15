// Three.js Background Animation
function initBackground() {
    const canvas = document.getElementById('bg-canvas');
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });

    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    // Create particles
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesCount = 1000;
    const posArray = new Float32Array(particlesCount * 3);

    for (let i = 0; i < particlesCount * 3; i++) {
        posArray[i] = (Math.random() - 0.5) * 100;
    }

    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));

    // Particle material
    const particlesMaterial = new THREE.PointsMaterial({
        size: 0.15,
        color: 0x6366f1,
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending
    });

    const particlesMesh = new THREE.Points(particlesGeometry, particlesMaterial);
    scene.add(particlesMesh);

    camera.position.z = 30;

    // Animation
    let mouseX = 0;
    let mouseY = 0;

    document.addEventListener('mousemove', (event) => {
        mouseX = (event.clientX / window.innerWidth) * 2 - 1;
        mouseY = -(event.clientY / window.innerHeight) * 2 + 1;
    });

    function animate() {
        requestAnimationFrame(animate);

        // Rotate particles
        particlesMesh.rotation.x += 0.0005;
        particlesMesh.rotation.y += 0.0005;

        // Mouse interaction
        particlesMesh.rotation.x += mouseY * 0.0005;
        particlesMesh.rotation.y += mouseX * 0.0005;

        renderer.render(scene, camera);
    }

    animate();

    // Handle window resize
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
}

// Theme Toggle
function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = themeToggle.querySelector('.theme-icon');
    const html = document.documentElement;

    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme') || 'dark';
    html.setAttribute('data-theme', savedTheme);
    themeIcon.textContent = savedTheme === 'dark' ? '🌙' : '☀️';

    themeToggle.addEventListener('click', () => {
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        themeIcon.textContent = newTheme === 'dark' ? '🌙' : '☀️';
    });
}

// Search and Filter Functionality
function initSearchAndFilter() {
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const categoryFilter = document.getElementById('category-filter');
    const difficultyFilter = document.getElementById('difficulty-filter');
    const resetBtn = document.getElementById('reset-filters');
    const papersGrid = document.getElementById('papers-grid');
    const filteredCount = document.getElementById('filtered-count');

    function filterPapers() {
        const searchTerm = searchInput.value.toLowerCase();
        const selectedCategory = categoryFilter.value;
        const selectedDifficulty = difficultyFilter.value;

        const papers = papersGrid.querySelectorAll('.paper-card');
        let visibleCount = 0;

        papers.forEach(paper => {
            const title = paper.getAttribute('data-title') || '';
            const authors = paper.getAttribute('data-authors') || '';
            const abstract = paper.getAttribute('data-abstract') || '';
            const category = paper.getAttribute('data-category') || '';
            const difficulty = paper.getAttribute('data-difficulty') || '';

            const matchesSearch = !searchTerm ||
                title.includes(searchTerm) ||
                authors.includes(searchTerm) ||
                abstract.includes(searchTerm);

            const matchesCategory = selectedCategory === 'all' || category === selectedCategory;
            const matchesDifficulty = selectedDifficulty === 'all' || difficulty === selectedDifficulty;

            if (matchesSearch && matchesCategory && matchesDifficulty) {
                paper.classList.remove('hidden');
                visibleCount++;
            } else {
                paper.classList.add('hidden');
            }
        });

        filteredCount.textContent = visibleCount;
    }

    searchInput.addEventListener('input', filterPapers);
    searchBtn.addEventListener('click', filterPapers);
    categoryFilter.addEventListener('change', filterPapers);
    difficultyFilter.addEventListener('change', filterPapers);

    resetBtn.addEventListener('click', () => {
        searchInput.value = '';
        categoryFilter.value = 'all';
        difficultyFilter.value = 'all';
        filterPapers();
    });

    // Allow Enter key for search
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            filterPapers();
        }
    });
}

// Paper Details Modal
function showDetails(paperId) {
    const modal = document.getElementById('paper-modal');
    const modalBody = document.getElementById('modal-body');

    // In a real implementation, this would fetch detailed paper info
    // For now, show a placeholder
    modalBody.innerHTML = `
        <h2>Paper Details: ${paperId}</h2>
        <p>Detailed information would be loaded here, including:</p>
        <ul>
            <li>Full abstract</li>
            <li>Complete author list</li>
            <li>All categories</li>
            <li>Related papers</li>
            <li>Citations</li>
            <li>Comments and discussions</li>
        </ul>
        <div style="margin-top: 2rem;">
            <a href="#" class="btn btn-primary" style="display: inline-block; margin-right: 1rem;">View PDF</a>
            <a href="#" class="btn btn-secondary" style="display: inline-block;">View on arXiv</a>
        </div>
    `;

    modal.style.display = 'block';
}

// Modal Controls
function initModal() {
    const modal = document.getElementById('paper-modal');
    const closeBtn = modal.querySelector('.modal-close');

    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });

    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.style.display === 'block') {
            modal.style.display = 'none';
        }
    });
}

// Lazy Loading Animation
function initLazyLoading() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.style.animationDelay = `${index * 0.1}s`;
                    entry.target.classList.add('visible');
                }, index * 50);
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });

    const papers = document.querySelectorAll('.paper-card');
    papers.forEach(paper => observer.observe(paper));
}

// Smooth Scroll
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Keyboard Navigation
function initKeyboardNav() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K for search focus
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('search-input').focus();
        }

        // Ctrl/Cmd + / for filter focus
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            e.preventDefault();
            document.getElementById('category-filter').focus();
        }
    });
}

// Add stagger animation to paper cards
function initStaggerAnimation() {
    const papers = document.querySelectorAll('.paper-card');
    papers.forEach((paper, index) => {
        paper.style.animationDelay = `${index * 0.05}s`;
    });
}

// Performance: Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize all features on DOM load
document.addEventListener('DOMContentLoaded', () => {
    initBackground();
    initThemeToggle();
    initSearchAndFilter();
    initModal();
    initLazyLoading();
    initSmoothScroll();
    initKeyboardNav();
    initStaggerAnimation();

    console.log('arXiv Daily initialized successfully!');
    console.log('Keyboard shortcuts:');
    console.log('  - Ctrl/Cmd + K: Focus search');
    console.log('  - Ctrl/Cmd + /: Focus filters');
    console.log('  - Escape: Close modal');
});

// Export showDetails for inline onclick handlers
window.showDetails = showDetails;
