function togglePassword(id, btn) {
    const input = document.getElementById(id);
    if (!input) return;

    const isHidden = input.type === "password";
    input.type = isHidden ? "text" : "password";

    btn.innerHTML = isHidden ? eyeSlashSVG : eyeSVG;
    btn.title = isHidden ? "Ocultar senha" : "Mostrar senha";
}

// SVGs com stroke vermelho
const eyeSVG = `
<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d9534f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/>
  <circle cx="12" cy="12" r="3"/>
</svg>
`;

const eyeSlashSVG = `
<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d9534f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M17.94 17.94A10.94 10.94 0 0 1 12 19C5 19 1 12 1 12a17.43 17.43 0 0 1 4.21-5.79"/>
  <path d="M22.54 12.88A17.43 17.43 0 0 0 19 6.21"/>
  <path d="M12 12a3 3 0 0 0-3-3"/>
  <path d="M1 1l22 22"/>
</svg>
`;
