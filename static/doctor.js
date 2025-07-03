// Doctor data
const doctors = [
  {
    id: 1,
    name: "Dr. Richard James",
    specialty: "General Physician",
    image: "/static/img/doktor1.png",
    experience: "8 Years",
    patients: "1,200+",
    rating: "4.9",
    fee: "Rp 50.000"
  },
  {
    id: 2,
    name: "Dr. Emily Larson",
    specialty: "Gynecologist",
    image: "/static/img/doktor2.png",
    experience: "6 Years",
    patients: "950+",
    rating: "4.8",
    fee: "Rp 50.000"
  },
  {
    id: 3,
    name: "Dr. Sarah Patel",
    specialty: "Dermatologist",
    image: "/static/img/doktor3.png",
    experience: "7 Years",
    patients: "800+",
    rating: "4.9",
    fee: "Rp 50.000"
  },
  {
    id: 4,
    name: "Dr. Christopher Lee",
    specialty: "Pediatrician",
    image: "/static/img/doktor4.png",
    experience: "10 Years",
    patients: "1,500+",
    rating: "5.0",
    fee: "Rp 50.000"
  },
  {
    id: 5,
    name: "Dr. Jennifer Garcia",
    specialty: "Neurologist",
    image: "/static/img/doktor5.png",
    experience: "12 Years",
    patients: "600+",
    rating: "4.9",
    fee: "Rp 50.000"
  },
  {
    id: 6,
    name: "Dr. Alex Morgan",
    specialty: "Orthopedic",
    image: "/static/img/doktor6.png",
    experience: "9 Years",
    patients: "1,100+",
    rating: "4.8",
    fee: "Rp 50.000"
  }
];

let selectedDoctor = null;

// Populate doctors grid
function populateDoctors() {
  const grid = document.getElementById('doctorsGrid');
  grid.innerHTML = doctors.map((doctor, index) => `
    <div class="doctor-card" onclick="openBookingModal(${doctor.id})" style="animation-delay: ${index * 0.1}s">
      <div class="doctor-image">
        <img src="${doctor.image}" alt="${doctor.name}" loading="lazy" />
      </div>
      <div class="doctor-info">
        <h3 class="doctor-name">
          ${doctor.name}
          <i class="fas fa-check-circle verified-badge" title="Dokter Terverifikasi"></i>
        </h3>
        <p class="doctor-specialty">${doctor.specialty}</p>
        
        <div class="doctor-stats">
          <div class="stat">
            <i class="fas fa-clock"></i>
            <span>${doctor.experience}</span>
          </div>
          <div class="stat">
            <i class="fas fa-users"></i>
            <span>${doctor.patients}</span>
          </div>
          <div class="stat">
            <i class="fas fa-star"></i>
            <span>${doctor.rating}</span>
          </div>
        </div>
        
        <div class="availability-status">
          <div class="status-dot"></div>
          <span class="status-text">Available Today</span>
        </div>
        
        <button class="book-button">
          <i class="fas fa-calendar-plus"></i>
          Book Appointment - ${doctor.fee}
        </button>
      </div>
    </div>
  `).join('');
  
  // Add fade-in animation to cards
  const cards = document.querySelectorAll('.doctor-card');
  cards.forEach((card, index) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(30px)';
    setTimeout(() => {
      card.style.transition = 'all 0.6s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, index * 150);
  });
}

// Open booking modal
function openBookingModal(doctorId) {
  selectedDoctor = doctors.find(d => d.id === doctorId);
  if (selectedDoctor) {
    document.getElementById('modalTitle').textContent = `Book with ${selectedDoctor.name}`;
    document.getElementById('bookingModal').classList.add('active');
    
    // Set minimum date to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('date').min = today;
  }
}

// Close modal
function closeModal() {
  document.getElementById('bookingModal').classList.remove('active');
  document.getElementById('bookingForm').reset();
  document.getElementById('successMessage').classList.remove('show');
}

// Handle form submission
document.getElementById('bookingForm').addEventListener('submit', function(e) {
  e.preventDefault();
  
  const submitBtn = document.getElementById('submitBtn');
  const btnText = submitBtn.querySelector('.btn-text');
  const loading = submitBtn.querySelector('.loading');
  
  // Show loading state
  btnText.style.display = 'none';
  loading.style.display = 'inline-block';
  submitBtn.disabled = true;
  
  // Collect form data
  const formData = {
    doctorId: selectedDoctor.id,
    doctorName: selectedDoctor.name,
    fee: selectedDoctor.fee,
    firstName: document.getElementById('firstName').value,
    lastName: document.getElementById('lastName').value,
    email: document.getElementById('email').value,
    phone: document.getElementById('phone').value,
    date: document.getElementById('date').value,
    time: document.getElementById('time').value,
    reason: document.getElementById('reason').value
  };
  
  // Process payment with Midtrans via Flask backend
  setTimeout(() => {
    // Hide loading state
    btnText.style.display = 'inline';
    loading.style.display = 'none';
    submitBtn.disabled = false;
    
  // Process payment
    processPayment(formData);
  }, 1000);
});

// Process payment with Midtrans
function processPayment(data) {
  // Get elements
  const paymentStatusMessage = document.getElementById('paymentStatusMessage');
  const paymentStatusText = document.getElementById('paymentStatusText');
  
  // Show payment status message
  document.getElementById('bookingForm').style.display = 'none';
  paymentStatusMessage.style.display = 'flex';
  paymentStatusText.innerText = 'Memproses pembayaran...';
  
  // Send request to payment processor
  fetch('/process_payment', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data)
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    return response.json();
  })
  .then(responseData => {
    console.log('Payment response:', responseData);
    
    if (!responseData.success) {
      throw new Error(responseData.message || 'Gagal membuat transaksi');
    }
    
    if (!responseData.snap_token) {
      throw new Error('Token pembayaran tidak diterima dari server');
    }
    
    // Check if Midtrans Snap is loaded
    if (!window.snap) {
      console.error('Midtrans Snap is not loaded');
      throw new Error('Midtrans Snap tidak dapat dimuat. Silakan refresh halaman.');
    }
    
    // Open Midtrans Snap payment popup
    window.snap.pay(responseData.snap_token, {
      onSuccess: function(result) {
        paymentStatusText.innerText = 'Pembayaran berhasil!';
        document.getElementById('successMessage').classList.add('show');
        
        // Log transaction data
        console.log('Payment success:', result);
        
        // Redirect to payment status page
        setTimeout(() => {
          window.location.href = `/payment_status?order_id=${result.order_id || responseData.order_id}&transaction_status=success`;
        }, 1500);
      },
      onPending: function(result) {
        // Log transaction data
        console.log('Payment pending:', result);
        
        paymentStatusText.innerText = 'Menunggu pembayaran...';
        
        // Redirect to payment status page
        setTimeout(() => {
          window.location.href = `/payment_status?order_id=${result.order_id || responseData.order_id}&transaction_status=pending`;
        }, 1500);
      },
      onError: function(result) {
        // Log error details
        console.error('Payment error:', result);
        
        paymentStatusText.innerText = 'Pembayaran gagal! Silakan coba lagi.';
        
        // Redirect to payment status page with error status
        if (result && result.order_id) {
          setTimeout(() => {
            window.location.href = `/payment_status?order_id=${result.order_id}&transaction_status=deny`;
          }, 1500);
        } else {
          setTimeout(() => {
            window.location.href = `/payment_status?order_id=${responseData.order_id}&transaction_status=deny`;
          }, 1500);
        }
      },
      onClose: function() {
        console.log('Customer closed the payment popup without finishing payment');
        paymentStatusText.innerText = 'Pembayaran dibatalkan!';
        
        setTimeout(() => {
          paymentStatusMessage.style.display = 'none';
          document.getElementById('bookingForm').style.display = 'block';
        }, 2000);
      }
    });
  })
  .catch(error => {
    console.error('Error processing payment:', error);
    paymentStatusText.innerText = `Error: ${error.message}`;
    
    setTimeout(() => {
      paymentStatusMessage.style.display = 'none';
      document.getElementById('bookingForm').style.display = 'block';
    }, 3000);
  });
}

// Close modal when clicking outside
document.getElementById('bookingModal').addEventListener('click', function(e) {
  if (e.target === this) {
    closeModal();
  }
});

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
  populateDoctors();

  // Atur minimal tanggal ke besok
  const dateInput = document.getElementById('date');
  if (dateInput) {
    const today = new Date();
    today.setDate(today.getDate() + 1);
    
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    const minDate = `${yyyy}-${mm}-${dd}`;
    
    dateInput.min = minDate;
    dateInput.value = minDate;

  }
});
