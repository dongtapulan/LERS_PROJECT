// Global UI behaviors and validation for the LERS interface
document.addEventListener("DOMContentLoaded", () => {
    
    // 1. Auto-dismiss Flash Alerts after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.transition = "opacity 0.5s ease";
            msg.style.opacity = "0";
            setTimeout(() => msg.remove(), 500);
        }, 5000);
    });

    // 2. Sidebar Toggle Controller
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            const layout = document.querySelector('.dashboard-layout');
            if (layout) {
                layout.classList.toggle('sidebar-collapsed');
            }
        });
    }
});

/**
 * 3. Form Validation: Password Entry Matcher
 * Linked to the onsubmit handler inside reset_password.html
 */
function validatePasswords() {
    const pass = document.getElementById('password').value;
    const confirmPass = document.getElementById('confirm_password').value;
    
    if (pass !== confirmPass) {
        alert("Form Error: Entry matching failed. Please verify passwords match.");
        return false;
    }
    return true;
}