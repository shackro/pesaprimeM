// Main JavaScript for PesaPrime

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggers = document.querySelectorAll('[data-tooltip]');
    tooltipTriggers.forEach(trigger => {
        trigger.addEventListener('mouseenter', function(e) {
            const tooltip = document.createElement('div');
            tooltip.className = 'fixed z-50 px-3 py-2 text-sm text-white bg-gray-900 rounded-lg shadow-lg';
            tooltip.textContent = this.dataset.tooltip;
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
            tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
            
            this.dataset.tooltipElement = tooltip;
        });
        
        trigger.addEventListener('mouseleave', function() {
            if (this.dataset.tooltipElement) {
                document.body.removeChild(this.dataset.tooltipElement);
                delete this.dataset.tooltipElement;
            }
        });
    });
    
    // Initialize number carousel
    const initNumberCarousel = () => {
        const carousel = document.querySelector('.number-carousel');
        if (carousel) {
            let scrollAmount = 0;
            const scrollSpeed = 1;
            const carouselWidth = carousel.scrollWidth;
            const containerWidth = carousel.parentElement.clientWidth;
            
            function autoScroll() {
                if (carousel) {
                    scrollAmount += scrollSpeed;
                    if (scrollAmount >= carouselWidth - containerWidth) {
                        scrollAmount = 0;
                    }
                    carousel.style.transform = `translateX(-${scrollAmount}px)`;
                    requestAnimationFrame(autoScroll);
                }
            }
            
            carousel.addEventListener('mouseenter', () => {
                scrollSpeed = 0;
            });
            
            carousel.addEventListener('mouseleave', () => {
                scrollSpeed = 1;
            });
            
            autoScroll();
        }
    };
    
    initNumberCarousel();
    
    // Currency formatting
    window.formatCurrency = function(amount, currency = 'KES') {
        const currencies = {
            'KES': { symbol: 'KSh ', decimalDigits: 2 },
            'USD': { symbol: '$', decimalDigits: 2 },
            'EUR': { symbol: '€', decimalDigits: 2 },
            'GBP': { symbol: '£', decimalDigits: 2 }
        };
        
        const config = currencies[currency] || currencies['KES'];
        return config.symbol + parseFloat(amount).toLocaleString('en-US', {
            minimumFractionDigits: config.decimalDigits,
            maximumFractionDigits: config.decimalDigits
        });
    };
    
    // Investment calculator
    const investmentCalculator = () => {
        const calculator = document.querySelector('.investment-calculator');
        if (calculator) {
            const amountInput = calculator.querySelector('[name="amount"]');
            const assetSelect = calculator.querySelector('[name="asset"]');
            const resultElement = calculator.querySelector('.calculation-result');
            
            const calculateReturns = () => {
                const amount = parseFloat(amountInput.value) || 0;
                const assetId = assetSelect.value;
                
                // In a real app, this would fetch from an API
                const assets = {
                    'btc': { hourlyReturn: 0.015, duration: 24 },
                    'eth': { hourlyReturn: 0.012, duration: 24 },
                    'default': { hourlyReturn: 0.01, duration: 24 }
                };
                
                const asset = assets[assetId] || assets['default'];
                const hourlyReturn = amount * asset.hourlyReturn;
                const totalReturn = hourlyReturn * asset.duration;
                
                if (resultElement) {
                    resultElement.innerHTML = `
                        <div class="space-y-2">
                            <div class="flex justify-between">
                                <span>Hourly Return:</span>
                                <span class="font-semibold">${formatCurrency(hourlyReturn)}</span>
                            </div>
                            <div class="flex justify-between">
                                <span>Daily Return:</span>
                                <span class="font-semibold">${formatCurrency(hourlyReturn * 24)}</span>
                            </div>
                            <div class="flex justify-between border-t pt-2">
                                <span>Total Return (${asset.duration}h):</span>
                                <span class="font-semibold text-green-600">${formatCurrency(totalReturn)}</span>
                            </div>
                        </div>
                    `;
                }
            };
            
            amountInput.addEventListener('input', calculateReturns);
            assetSelect.addEventListener('change', calculateReturns);
            
            // Initial calculation
            calculateReturns();
        }
    };
    
    investmentCalculator();
    
    // Form validation
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = this.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('border-red-500');
                    isValid = false;
                    
                    // Add error message
                    let errorMsg = field.nextElementSibling;
                    if (!errorMsg || !errorMsg.classList.contains('error-message')) {
                        errorMsg = document.createElement('p');
                        errorMsg.className = 'error-message text-red-500 text-sm mt-1';
                        errorMsg.textContent = 'This field is required';
                        field.parentNode.insertBefore(errorMsg, field.nextSibling);
                    }
                } else {
                    field.classList.remove('border-red-500');
                    const errorMsg = field.nextElementSibling;
                    if (errorMsg && errorMsg.classList.contains('error-message')) {
                        errorMsg.remove();
                    }
                }
            });
            
            if (!isValid) {
                e.preventDefault();
            }
        });
    });
    
    // Auto-update prices (simulated)
    const updatePrices = () => {
        const priceElements = document.querySelectorAll('.price-update');
        priceElements.forEach(element => {
            const currentPrice = parseFloat(element.dataset.price || '0');
            const change = (Math.random() - 0.5) * 0.02; // ±1%
            const newPrice = currentPrice * (1 + change);
            
            element.dataset.price = newPrice.toFixed(2);
            element.textContent = formatCurrency(newPrice);
            
            // Update change indicator
            const changeElement = element.nextElementSibling;
            if (changeElement && changeElement.classList.contains('price-change')) {
                const changePercent = (change * 100).toFixed(2);
                changeElement.textContent = `${change >= 0 ? '+' : ''}${changePercent}%`;
                changeElement.className = `price-change ${change >= 0 ? 'text-green-500' : 'text-red-500'}`;
            }
        });
    };
    
    // Update prices every 30 seconds
    if (document.querySelector('.price-update')) {
        setInterval(updatePrices, 30000);
    }
    
    // Mobile menu toggle
    const mobileMenuButton = document.querySelector('[data-mobile-menu-toggle]');
    const mobileMenu = document.querySelector('[data-mobile-menu]');
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!mobileMenu.contains(e.target) && !mobileMenuButton.contains(e.target)) {
                mobileMenu.classList.add('hidden');
            }
        });
    }
    
    // Copy to clipboard
    const copyButtons = document.querySelectorAll('[data-copy]');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.dataset.copy;
            navigator.clipboard.writeText(textToCopy).then(() => {
                // Show success feedback
                const originalText = this.innerHTML;
                this.innerHTML = '<span class="flex items-center"><svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>Copied!</span>';
                
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 2000);
            });
        });
    });
});

// API helper functions
const API = {
    async get(url) {
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        return response.json();
    },
    
    async post(url, data) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    async put(url, data) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        const response = await fetch(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    async delete(url) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        const response = await fetch(url, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        return response.json();
    }
};