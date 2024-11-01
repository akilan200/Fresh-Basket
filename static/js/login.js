document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const formTitle = document.getElementById('formTitle');
    const signUpFields = document.getElementById('signUpFields');
    const submitButton = document.getElementById('submitButton');
    const toggleFormLink = document.getElementById('toggleFormLink');
    const signupLinks = document.querySelectorAll('.signup-link');

    // Toggle between login and signup
    toggleFormLink.addEventListener('click', function(e) {
        e.preventDefault();
        toggleForm();
    });

    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        if (formTitle.textContent === 'Sign Up to Fresh Basket') {
            // Handle Sign Up
            const firstName = document.getElementById('firstName').value;
            const lastName = document.getElementById('lastName').value;
            const phoneNumber = document.getElementById('phoneNumber').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;

            if (firstName && lastName && phoneNumber && email && password) {
                // Here you would typically make an API call to register the user
                // For now, we'll just simulate success and return to login
                showCustomAlert('Sign up successful! Please login.');
                resetToSignIn();
            } else {
                showCustomAlert('Please fill in all fields');
            }
        } else {
            // Handle Login
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;

            if (email && password) {
                try {
                    // Here you would typically verify credentials with your backend
                    // For now, we'll simulate a successful login
                    localStorage.setItem('isLoggedIn', 'true');
                    window.location.href = 'shop.html';
                } catch (error) {
                    console.error('Login error:', error);
                    showCustomAlert('Login failed. Please try again.');
                }
            } else {
                showCustomAlert('Please enter both email and password');
            }
        }
    });

    function toggleForm() {
        if (formTitle.textContent === 'Sign In to Fresh Basket') {
            // Switch to Sign Up form
            formTitle.textContent = 'Sign Up to Fresh Basket';
            signUpFields.style.display = 'block';
            submitButton.textContent = 'Sign Up';
            signupLinks.forEach(link => link.style.display = 'none');
            loginForm.reset(); // Clear the form
        } else {
            resetToSignIn();
        }
    }

    function resetToSignIn() {
        formTitle.textContent = 'Sign In to Fresh Basket';
        signUpFields.style.display = 'none';
        submitButton.textContent = 'Login';
        signupLinks.forEach(link => link.style.display = 'block');
        loginForm.reset(); // Clear the form
    }

    // Admin login handler
    document.getElementById('adminLoginLink').addEventListener('click', function(e) {
        e.preventDefault();
        const loginContainer = document.querySelector('.login-container');
        
        // Change form title and hide signup link
        formTitle.textContent = 'Admin Login';
        signupLinks[0].style.display = 'none'; // Hide "Don't have an account?"
        
        // Show admin login indicator
        if (!document.querySelector('.admin-login-text')) {
            const adminLoginText = document.createElement('h3');
            adminLoginText.textContent = 'Admin Access Only';
            adminLoginText.classList.add('admin-login-text');
            loginContainer.insertBefore(adminLoginText, loginContainer.querySelector('h2'));
        }

        // Modify form submission for admin login
        loginForm.removeEventListener('submit', regularFormHandler);
        loginForm.addEventListener('submit', adminFormHandler);
    });

    // Regular form submission handler
    function regularFormHandler(e) {
        e.preventDefault();
        // ... your existing login/signup logic ...
    }

    // Admin form submission handler
    function adminFormHandler(e) {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        // Add your admin credentials validation here
        if (email === 'admin@freshbasket.com' && password === 'admin123') {
            localStorage.setItem('isAdminLoggedIn', 'true');
            window.location.href = 'admin_dashboard.html';
        } else {
            showCustomAlert('Invalid admin credentials');
        }
    }

    // Add this function to reset to regular login
    function resetToRegularLogin() {
        formTitle.textContent = 'Sign In to Fresh Basket';
        signupLinks[0].style.display = 'block';
        const adminLoginText = document.querySelector('.admin-login-text');
        if (adminLoginText) {
            adminLoginText.remove();
        }
        loginForm.removeEventListener('submit', adminFormHandler);
        loginForm.addEventListener('submit', regularFormHandler);
    }

    // Initialize regular form handler
    loginForm.addEventListener('submit', regularFormHandler);
});

function showCustomAlert(message) {
    alert(message);
}
