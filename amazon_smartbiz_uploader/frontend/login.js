document.addEventListener('DOMContentLoaded', () => {
    // If already logged in, redirect
    if (localStorage.getItem('access_token')) {
        window.location.href = 'index.html';
    }
    
    const loginForm = document.getElementById('login-form');
    const forgotForm = document.getElementById('forgot-form');
    const errorDiv = document.getElementById('login-error');
    
    document.getElementById('show-forgot-btn').addEventListener('click', (e) => {
        e.preventDefault();
        loginForm.style.display = 'none';
        forgotForm.style.display = 'block';
        errorDiv.style.display = 'none';
        document.querySelector('.login-header h2').textContent = 'Reset Password';
        document.querySelector('.login-header p').textContent = 'Enter recovery key to reset';
    });

    document.getElementById('show-login-btn').addEventListener('click', (e) => {
        e.preventDefault();
        forgotForm.style.display = 'none';
        loginForm.style.display = 'block';
        errorDiv.style.display = 'none';
        document.querySelector('.login-header h2').textContent = 'Welcome Back';
        document.querySelector('.login-header p').textContent = 'Please login to continue';
    });
    
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const btn = loginForm.querySelector('button');
        
        btn.textContent = 'Logging in...';
        btn.disabled = true;
        errorDiv.style.display = 'none';
        
        try {
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);
            
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Invalid credentials');
            }
            
            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);
            window.location.href = 'index.html';
            
        } catch (error) {
            errorDiv.textContent = error.message || 'Login failed';
            errorDiv.style.display = 'block';
        } finally {
            btn.textContent = 'Login';
            btn.disabled = false;
        }
    });

    forgotForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const recoveryKey = document.getElementById('recovery-key').value;
        const newPassword = document.getElementById('new-password').value;
        const btn = forgotForm.querySelector('button');
        
        btn.textContent = 'Resetting...';
        btn.disabled = true;
        errorDiv.style.display = 'none';
        
        try {
            const response = await fetch('/api/forgot-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    recovery_key: recoveryKey,
                    new_password: newPassword
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'Reset failed');
            }
            
            alert('Password reset successfully! Please login with your new password.');
            document.getElementById('show-login-btn').click();
            forgotForm.reset();
            
        } catch (error) {
            errorDiv.textContent = error.message;
            errorDiv.style.display = 'block';
        } finally {
            btn.textContent = 'Reset Password';
            btn.disabled = false;
        }
    });
});
