// Charting functionality for PesaPrime

class InvestmentChart {
    constructor(canvasId, options = {}) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        
        this.ctx = this.canvas.getContext('2d');
        this.options = {
            type: options.type || 'line',
            data: options.data || { labels: [], datasets: [] },
            config: options.config || {}
        };
        
        this.chart = null;
        this.init();
    }
    
    init() {
        const defaultConfig = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: getComputedStyle(document.documentElement).getPropertyValue('--text-color') || '#374151'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(156, 163, 175, 0.1)'
                    },
                    ticks: {
                        color: '#6B7280'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(156, 163, 175, 0.1)'
                    },
                    ticks: {
                        color: '#6B7280',
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            }
        };
        
        const config = { ...defaultConfig, ...this.options.config };
        this.chart = new Chart(this.ctx, {
            type: this.options.type,
            data: this.options.data,
            options: config
        });
    }
    
    update(data) {
        if (this.chart) {
            this.chart.data = data;
            this.chart.update();
        }
    }
    
    destroy() {
        if (this.chart) {
            this.chart.destroy();
        }
    }
}

// Initialize charts on page load
document.addEventListener('DOMContentLoaded', function() {
    // Portfolio Performance Chart
    const portfolioChartElement = document.getElementById('portfolioChart');
    if (portfolioChartElement) {
        const portfolioData = {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            datasets: [{
                label: 'Portfolio Value',
                data: [5000, 5500, 6000, 5800, 6500, 7000, 7500, 7800, 8200, 8500, 9000, 9500],
                borderColor: '#10B981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                tension: 0.4,
                fill: true
            }]
        };
        
        new InvestmentChart('portfolioChart', {
            data: portfolioData,
            config: {
                plugins: {
                    title: {
                        display: true,
                        text: 'Portfolio Performance',
                        color: '#111827'
                    }
                }
            }
        });
    }
    
    // Asset Distribution Chart
    const distributionChartElement = document.getElementById('distributionChart');
    if (distributionChartElement) {
        const distributionData = {
            labels: ['Bitcoin', 'Ethereum', 'Forex', 'Stocks', 'Commodities'],
            datasets: [{
                data: [40, 25, 15, 12, 8],
                backgroundColor: [
                    '#10B981',
                    '#3B82F6',
                    '#8B5CF6',
                    '#F59E0B',
                    '#EF4444'
                ],
                borderWidth: 2,
                borderColor: '#1F2937'
            }]
        };
        
        new InvestmentChart('distributionChart', {
            type: 'doughnut',
            data: distributionData,
            config: {
                plugins: {
                    title: {
                        display: true,
                        text: 'Asset Distribution',
                        color: '#111827'
                    },
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }
    
    // Real-time Price Chart
    const realtimeChartElement = document.getElementById('realtimeChart');
    if (realtimeChartElement) {
        const timeLabels = [];
        const priceData = [];
        let currentPrice = 50000;
        
        // Generate initial data
        for (let i = 0; i < 30; i++) {
            timeLabels.push(`${i}:00`);
            currentPrice += (Math.random() - 0.5) * 1000;
            priceData.push(currentPrice);
        }
        
        const realtimeData = {
            labels: timeLabels,
            datasets: [{
                label: 'BTC/USD',
                data: priceData,
                borderColor: '#F59E0B',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                tension: 0.4,
                fill: true
            }]
        };
        
        const realtimeChart = new InvestmentChart('realtimeChart', {
            data: realtimeData,
            config: {
                plugins: {
                    title: {
                        display: true,
                        text: 'Bitcoin Price (Simulated)',
                        color: '#111827'
                    }
                }
            }
        });
        
        // Simulate real-time updates
        setInterval(() => {
            const lastPrice = priceData[priceData.length - 1];
            const newPrice = lastPrice + (Math.random() - 0.5) * 500;
            
            // Add new data point
            priceData.push(newPrice);
            priceData.shift();
            
            // Add new time label
            const lastTime = parseInt(timeLabels[timeLabels.length - 1].split(':')[0]);
            timeLabels.push(`${(lastTime + 1) % 24}:00`);
            timeLabels.shift();
            
            realtimeChart.update({
                labels: timeLabels,
                datasets: [{
                    label: 'BTC/USD',
                    data: priceData,
                    borderColor: '#F59E0B',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            });
        }, 5000);
    }
});

// Dark mode support for charts
const updateChartTheme = () => {
    const isDark = document.documentElement.classList.contains('dark');
    const textColor = isDark ? '#F9FAFB' : '#111827';
    const gridColor = isDark ? 'rgba(156, 163, 175, 0.1)' : 'rgba(209, 213, 219, 0.3)';
    
    // Update all charts
    Chart.helpers.each(Chart.instances, (instance) => {
        if (instance.options.scales) {
            instance.options.scales.x.ticks.color = textColor;
            instance.options.scales.y.ticks.color = textColor;
            instance.options.scales.x.grid.color = gridColor;
            instance.options.scales.y.grid.color = gridColor;
            
            if (instance.options.plugins?.title) {
                instance.options.plugins.title.color = textColor;
            }
            
            if (instance.options.plugins?.legend?.labels) {
                instance.options.plugins.legend.labels.color = textColor;
            }
            
            instance.update();
        }
    });
};

// Listen for theme changes
const themeObserver = new MutationObserver(updateChartTheme);
themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class']
});