// Payment Enhancement JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Add loading states to buttons
    addLoadingStates();
    
    // Add smooth scrolling to action buttons
    addSmoothScrolling();
    
    // Add real-time search functionality
    enhanceSearch();
    
    // Add tooltips for payment methods
    addPaymentMethodTooltips();
    
    // Add copy to clipboard functionality
    addCopyFunctionality();
    
    // Add auto-refresh for pending payments
    addAutoRefresh();
});

function addLoadingStates() {
    const buttons = document.querySelectorAll('.btn, .action-btn');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!this.classList.contains('loading')) {
                this.classList.add('loading');
                
                // Create loading spinner
                const spinner = document.createElement('i');
                spinner.className = 'fas fa-spinner fa-spin loading-spinner';
                
                // Store original content
                const originalContent = this.innerHTML;
                this.setAttribute('data-original', originalContent);
                
                // Add spinner
                this.innerHTML = '';
                this.appendChild(spinner);
                
                // Remove loading state after 2 seconds (or when page loads)
                setTimeout(() => {
                    this.classList.remove('loading');
                    this.innerHTML = originalContent;
                }, 2000);
            }
        });
    });
}

function addSmoothScrolling() {
    const actionButtons = document.querySelectorAll('a[href^="#"], a[href^="/"]');
    actionButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href.startsWith('#')) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
}

function enhanceSearch() {
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    
    if (searchInput && statusFilter) {
        // Add real-time search
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                filterPayments();
            }, 300);
        });
        
        // Add search suggestions
        const suggestions = createSearchSuggestions();
        if (suggestions.length > 0) {
            addSearchSuggestions(searchInput, suggestions);
        }
    }
}

function createSearchSuggestions() {
    const rows = document.querySelectorAll('#paymentTableBody tr');
    const suggestions = new Set();
    
    rows.forEach(row => {
        const orderId = row.cells[1]?.textContent?.trim();
        const doctorName = row.cells[2]?.textContent?.trim();
        
        if (orderId) suggestions.add(orderId);
        if (doctorName) suggestions.add(doctorName);
    });
    
    return Array.from(suggestions);
}

function addSearchSuggestions(input, suggestions) {
    const suggestionBox = document.createElement('div');
    suggestionBox.className = 'search-suggestions';
    suggestionBox.style.display = 'none';
    input.parentNode.appendChild(suggestionBox);
    
    input.addEventListener('input', function() {
        const value = this.value.toLowerCase();
        if (value.length > 1) {
            const matches = suggestions.filter(s => 
                s.toLowerCase().includes(value)
            ).slice(0, 5);
            
            if (matches.length > 0) {
                suggestionBox.innerHTML = matches.map(match => 
                    `<div class="suggestion-item">${match}</div>`
                ).join('');
                suggestionBox.style.display = 'block';
                
                // Add click handlers
                suggestionBox.querySelectorAll('.suggestion-item').forEach(item => {
                    item.addEventListener('click', function() {
                        input.value = this.textContent;
                        suggestionBox.style.display = 'none';
                        filterPayments();
                    });
                });
            } else {
                suggestionBox.style.display = 'none';
            }
        } else {
            suggestionBox.style.display = 'none';
        }
    });
    
    // Hide suggestions when clicking outside
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !suggestionBox.contains(e.target)) {
            suggestionBox.style.display = 'none';
        }
    });
}

function addPaymentMethodTooltips() {
    const paymentMethods = document.querySelectorAll('[data-payment-method]');
    paymentMethods.forEach(method => {
        const tooltip = createTooltip(getPaymentMethodInfo(method.dataset.paymentMethod));
        method.appendChild(tooltip);
    });
}

function createTooltip(content) {
    const tooltip = document.createElement('div');
    tooltip.className = 'payment-tooltip';
    tooltip.innerHTML = content;
    return tooltip;
}

function getPaymentMethodInfo(method) {
    const info = {
        'credit_card': 'Pembayaran menggunakan kartu kredit Visa/Mastercard',
        'bca_va': 'Transfer melalui Virtual Account BCA',
        'bni_va': 'Transfer melalui Virtual Account BNI',
        'bri_va': 'Transfer melalui Virtual Account BRI',
        'gopay': 'Pembayaran digital melalui aplikasi GoPay',
        'shopeepay': 'Pembayaran digital melalui ShopeePay'
    };
    return info[method] || 'Metode pembayaran digital';
}

function addCopyFunctionality() {
    const copyButtons = document.querySelectorAll('[data-copy]');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.dataset.copy;
            navigator.clipboard.writeText(textToCopy).then(() => {
                showCopySuccess(this);
            }).catch(() => {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = textToCopy;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                showCopySuccess(this);
            });
        });
    });
}

function showCopySuccess(button) {
    const originalText = button.textContent;
    button.textContent = 'Copied!';
    button.style.background = '#27ae60';
    
    setTimeout(() => {
        button.textContent = originalText;
        button.style.background = '';
    }, 2000);
}

function addAutoRefresh() {
    const pendingPayments = document.querySelectorAll('.status-badge.pending');
    
    if (pendingPayments.length > 0) {
        // Check for updates every 30 seconds
        setInterval(() => {
            checkPendingPayments();
        }, 30000);
    }
}

function checkPendingPayments() {
    const pendingRows = document.querySelectorAll('tr:has(.status-badge.pending)');
    
    pendingRows.forEach(row => {
        const orderId = row.cells[1]?.textContent?.trim();
        if (orderId) {
            fetch('/check_payment_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ order_id: orderId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.transaction_status !== 'pending') {
                    updatePaymentRow(row, data);
                }
            })
            .catch(error => {
                console.log('Error checking payment status:', error);
            });
        }
    });
}

function updatePaymentRow(row, data) {
    const statusBadge = row.querySelector('.status-badge');
    if (statusBadge) {
        statusBadge.className = `status-badge ${data.transaction_status}`;
        statusBadge.textContent = data.transaction_status.charAt(0).toUpperCase() + data.transaction_status.slice(1);
        
        // Add update animation
        statusBadge.style.animation = 'pulse 0.5s ease';
        setTimeout(() => {
            statusBadge.style.animation = '';
        }, 500);
        
        // Remove pay button if payment is completed
        if (data.transaction_status === 'settlement' || data.transaction_status === 'capture') {
            const payButton = row.querySelector('.pay-btn');
            if (payButton) {
                payButton.remove();
            }
        }
    }
}

function filterPayments() {
    const statusFilter = document.getElementById('statusFilter');
    const searchInput = document.getElementById('searchInput');
    
    if (!statusFilter || !searchInput) return;
    
    const status = statusFilter.value;
    const search = searchInput.value.toLowerCase();
    
    document.querySelectorAll('#paymentTableBody tr').forEach(row => {
        const statusValue = row.querySelector('.status-badge')?.classList[1] || '';
        const orderId = row.cells[1]?.textContent?.toLowerCase() || '';
        const doctorName = row.cells[2]?.textContent?.toLowerCase() || '';
        
        const statusMatch = status === 'all' || statusValue === status;
        const searchMatch = orderId.includes(search) || doctorName.includes(search);
        
        if (statusMatch && searchMatch) {
            row.style.display = '';
            row.style.animation = 'fadeIn 0.3s ease';
        } else {
            row.style.display = 'none';
        }
    });
    
    updateEmptyState();
}

function updateEmptyState() {
    const visibleRows = document.querySelectorAll('#paymentTableBody tr:not([style*="display: none"])');
    const noDataRow = document.querySelector('.no-data-filtered');
    
    if (visibleRows.length === 0 && !noDataRow) {
        const tbody = document.getElementById('paymentTableBody');
        const tr = document.createElement('tr');
        tr.className = 'no-data-filtered';
        tr.innerHTML = `<td colspan="7" class="no-data">
            <i class="fas fa-search"></i>
            <p>Tidak ada data yang sesuai dengan filter</p>
        </td>`;
        tbody.appendChild(tr);
    } else if (visibleRows.length > 0) {
        const noDataFiltered = document.querySelector('.no-data-filtered');
        if (noDataFiltered) {
            noDataFiltered.remove();
        }
    }
}
