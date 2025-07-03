// static/js/kader_sidebar_toggle.js

document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.querySelector('.toggle-btn');
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const topHeader = document.querySelector('.top-header'); // Biarkan ini tetap ada untuk debug atau referensi

    if (toggleBtn && sidebar && mainContent) {
        toggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('closed');
            mainContent.classList.toggle('fullwidth');
            // --- HAPUS ATAU KOMENTARI BARIS INI ---
            // if (topHeader) {
            //     topHeader.classList.toggle('fullwidth-header');
            // }
            // --- AKHIR PENGHAPUSAN ---

            const icon = toggleBtn.querySelector('i');
            if (icon) {
                if (sidebar.classList.contains('closed')) {
                    icon.classList.remove('fa-bars');
                    icon.classList.add('fa-indent');
                } else {
                    icon.classList.remove('fa-indent');
                    icon.classList.add('fa-bars');
                }
            }
        });
    } else {
        console.error('Sidebar toggle: Elemen tidak ditemukan. Periksa selektor CSS atau struktur HTML.', {
            toggleBtn: !!toggleBtn,
            sidebar: !!sidebar,
            mainContent: !!mainContent,
            topHeader: !!topHeader
        });
    }
});