const eyeSVG = `
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
         fill="none" stroke="#d9534f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/>
        <circle cx="12" cy="12" r="3"/>
    </svg>`;

const eyeSlashSVG = `
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
         fill="none" stroke="#d9534f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17.94 17.94A10.94 10.94 0 0 1 12 19
            C5 19 1 12 1 12a17.43 17.43 0 0 1 4.21-5.79"/>
        <path d="M22.54 12.88A17.43 17.43 0 0 0 19 6.21"/>
        <path d="M12 12a3 3 0 0 0-3-3"/>
        <path d="M1 1l22 22"/>
    </svg>`;

function togglePassword(id, btn) {
    const input = document.getElementById(id);
    if (!input) return;

    const isHidden = input.type === "password";
    input.type = isHidden ? "text" : "password";

    const iconSpan = btn.querySelector('.password-toggle-icon');
    if (iconSpan) {
        iconSpan.innerHTML = isHidden ? eyeSlashSVG : eyeSVG;
        btn.title = isHidden ? "Ocultar senha" : "Mostrar senha";
    }
}

function generatePassword(id) {
    const input = document.getElementById(id);
    if (!input) return;

    const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&!";
    let password = "";
    for (let i = 0; i < 12; i++) {
        password += charset[Math.floor(Math.random() * charset.length)];
    }

    input.value = password;

    // Mostrar senha ao gerar
    if (input.type === "password") {
        input.type = "text";
        const toggleBtn = input.parentNode.querySelector("button[onclick^='togglePassword'] .password-toggle-icon");
        if (toggleBtn) {
            toggleBtn.innerHTML = eyeSlashSVG;
        }
    }
}

// Disponibiliza no escopo global para funcionar com onclick inline
window.togglePassword = togglePassword;
window.generatePassword = generatePassword;

// Alias para compatibilidade com HTML antigo
window.toggleModalPassword = togglePassword;

document.addEventListener("DOMContentLoaded", function () {
    const btn = document.getElementById("btn-toggle-senha");
    if (btn) {
        btn.addEventListener("click", function () {
            togglePassword("input-senha", btn);
        });
    }
});
