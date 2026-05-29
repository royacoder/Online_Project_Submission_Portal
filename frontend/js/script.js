const API_URL = window.location.origin + '/api';
const API_URL_BASE = window.location.origin;
const FILES_BASE_URL = '/uploads';
const SCREENSHOTS_BASE_URL = '/screenshots';

/* ── Progress Bar ── */
const _bar = document.createElement('div');
_bar.id = 'nprogress-bar';
document.documentElement.appendChild(_bar);

function progressStart() {
    _bar.style.width = '0%';
    _bar.style.opacity = '1';
    let w = 0;
    _bar._timer = setInterval(() => {
        w = Math.min(w + Math.random() * 12, 85);
        _bar.style.width = w + '%';
    }, 200);
}
function progressDone() {
    clearInterval(_bar._timer);
    _bar.style.width = '100%';
    setTimeout(() => { _bar.style.opacity = '0'; _bar.style.width = '0%'; }, 400);
}

/* ── Utils ── */
function escapeHtml(unsafe) {
    if(!unsafe) return '';
    return unsafe.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

/* ── Toast System ── */
(function () {
    const container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
})();

function showToast(message, type = 'info', title = null) {
    const icons = { success: 'fa-check', error: 'fa-times', warning: 'fa-exclamation', info: 'fa-info' };
    const titles = { success: 'Success', error: 'Error', warning: 'Warning', info: 'Info' };
    const el = document.createElement('div');
    el.className = `toast-item toast-${type}`;
    el.innerHTML = `
        <div class="toast-icon"><i class="fas ${icons[type] || icons.info}"></i></div>
        <div class="toast-body">
            <div class="toast-title">${title || titles[type]}</div>
            <div class="toast-msg">${message}</div>
        </div>
        <button class="toast-close" onclick="this.closest('.toast-item').remove()"><i class="fas fa-times"></i></button>
        <div class="toast-progress"></div>
    `;
    document.getElementById('toast-container').appendChild(el);
    setTimeout(() => {
        el.classList.add('toast-out');
        setTimeout(() => el.remove(), 350);
    }, 4000);
}

/* ── Custom Confirm Dialog ── */
function showConfirm(message, title = 'Are you sure?') {
    return new Promise(resolve => {
        const overlay = document.createElement('div');
        overlay.id = 'confirm-overlay';
        overlay.innerHTML = `
            <div id="confirm-box">
                <div class="confirm-icon"><i class="fas fa-exclamation-triangle"></i></div>
                <h5>${title}</h5>
                <p>${message}</p>
                <div class="confirm-btns">
                    <button class="btn btn-outline-secondary" id="confirm-no">Cancel</button>
                    <button class="btn btn-danger" id="confirm-yes"><i class="fas fa-trash me-2"></i>Confirm</button>
                </div>
            </div>`;
        document.body.appendChild(overlay);
        overlay.querySelector('#confirm-yes').onclick = () => { overlay.remove(); resolve(true); };
        overlay.querySelector('#confirm-no').onclick  = () => { overlay.remove(); resolve(false); };
        overlay.onclick = (e) => { if (e.target === overlay) { overlay.remove(); resolve(false); } };
    });
}

/* ── Greeting Banner ── */
function injectGreeting(username, role) {
    const container = document.querySelector('.container.fade-in');
    if (!container || document.getElementById('greeting-banner')) return;

    const hour = new Date().getHours();
    const greet = hour < 12 ? 'Good Morning' : hour < 17 ? 'Good Afternoon' : 'Good Evening';
    const roleIcons = { admin: 'fa-shield-alt', hod: 'fa-user-shield', clerk: 'fa-user-edit', guide: 'fa-chalkboard-teacher', student: 'fa-user-graduate' };

    const banner = document.createElement('div');
    banner.id = 'greeting-banner';
    banner.className = 'greeting-banner';
    banner.innerHTML = `
        <div class="greeting-text">
            <h4><i class="fas ${roleIcons[role] || 'fa-user'} me-2" style="color:var(--primary)"></i>${greet}, ${username}!</h4>
            <p>You're logged in as <strong style="color:var(--primary)">${role.charAt(0).toUpperCase() + role.slice(1)}</strong> · ${new Date().toLocaleDateString('en-US', {weekday:'long', month:'long', day:'numeric', year:'numeric'})}</p>
        </div>
        <div class="greeting-time">
            <span class="time-display" id="live-clock"></span>
            <span id="live-date-short"></span>
        </div>`;
    container.insertBefore(banner, container.firstChild);

    function tick() {
        const now = new Date();
        const cl = document.getElementById('live-clock');
        const ds = document.getElementById('live-date-short');
        if (cl) cl.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        if (ds) ds.textContent = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
    tick();
    setInterval(tick, 1000);
}

/* ── Sidebar Role Badge ── */
function injectSidebarBadge(username, role) {
    const sidebar = document.querySelector('.list-group');
    if (!sidebar || document.querySelector('.sidebar-role-badge')) return;
    const roleIcons = { admin: 'fa-shield-alt', hod: 'fa-user-shield', clerk: 'fa-user-edit', guide: 'fa-chalkboard-teacher', student: 'fa-user-graduate' };
    const badge = document.createElement('div');
    badge.className = 'sidebar-role-badge';
    badge.innerHTML = `
        <div class="role-avatar"><i class="fas ${roleIcons[role] || 'fa-user'}"></i></div>
        <div class="role-name">${username}</div>
        <div class="role-label">${role}</div>`;
    sidebar.insertBefore(badge, sidebar.firstChild);
}

/* ── Auth: check session ── */
async function checkAuth(requiredRole = null) {
    try {
        progressStart();
        const response = await fetch(`${API_URL}?action=getSession`, { credentials: 'include' });
        const data = await response.json();
        progressDone();

        if (!data.success) {
            const path = window.location.pathname;
            if (path.indexOf('login.html') === -1 && 
                path.indexOf('register.html') === -1 && 
                path.indexOf('approved-projects.html') === -1 && 
                path.indexOf('view-project.html') === -1) {
                window.location.href = 'login.html';
            }
            return null;
        }

        // Profile photo in navbar
        const brandContainer = document.querySelector('.navbar-brand')?.parentElement;
        if (brandContainer && !document.getElementById('profile-nav-link')) {
            const profileLink = document.createElement('a');
            profileLink.id = 'profile-nav-link';
            profileLink.href = 'profile.html';
            profileLink.className = 'text-white me-3 d-flex align-items-center';
            profileLink.title = 'My Profile';
            if (data.user.profile_photo) {
                const finalUrl = data.user.profile_photo.startsWith('profile_photos/')
                    ? `${API_URL_BASE}/${data.user.profile_photo}`
                    : `${API_URL_BASE}/profile_photos/${data.user.profile_photo}`;
                profileLink.innerHTML = `<img src="${finalUrl}" class="rounded-circle border border-2 border-light" style="width:38px;height:38px;object-fit:cover;">`;
            } else {
                profileLink.innerHTML = `<div style="width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,var(--primary),var(--secondary));display:flex;align-items:center;justify-content:center;font-size:0.9rem;color:white;font-weight:700">${data.user.username.charAt(0).toUpperCase()}</div>`;
            }
            brandContainer.prepend(profileLink);
        }

        // Navbar welcome & notifications
        const navAuth = document.getElementById('nav-auth');
        if (navAuth) {
            navAuth.innerHTML = `
                <li class="nav-item me-3 d-flex align-items-center">
                    <a href="notifications.html" class="btn btn-link text-white position-relative" style="padding:0; text-decoration:none;">
                        <i class="fas fa-bell fs-5"></i>
                        <span id="notif-badge" class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger" style="display:none; font-size:0.5rem; transform:translate(-40%, -20%)!important;">0</span>
                    </a>
                </li>
                <li class="nav-item d-flex align-items-center">
                    <span class="nav-link" style="cursor:default">
                        <span class="badge bg-primary me-1" style="font-size:0.7rem">${data.user.role}</span>
                        ${data.user.username}
                    </span>
                </li>`;
        }
        
        pollNotifications();

        // Inject greeting & sidebar badge
        injectGreeting(data.user.username, data.user.role);
        injectSidebarBadge(data.user.username, data.user.role);

        return data.user;
    } catch (err) {
        progressDone();
        console.error('Auth check failed:', err);
    }
}

/* ── Notifications Logic ── */
async function pollNotifications() {
    try {
        const req = await fetch(`${API_URL}?action=getNotifications`, { credentials: 'include' });
        const res = await req.json();
        const badge = document.getElementById('notif-badge');
        const unreadCount = res.success ? res.notifications.filter(n => !n.is_read).length : 0;
        
        if (badge) {
            if (unreadCount > 0) {
                badge.textContent = unreadCount;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
        
        document.querySelectorAll('.sidebar-notif-badge').forEach(el => {
            if (unreadCount > 0) {
                el.textContent = unreadCount;
                el.style.display = 'inline-block';
            } else {
                el.style.display = 'none';
            }
        });
    } catch(e){}
}
setInterval(pollNotifications, 5000); // 5 sec sync

/* ── Theme ── */
function initTheme() {
    const theme = localStorage.getItem('theme') || 'dark';
    if (theme === 'light') document.body.classList.add('light-mode');
    updateThemeToggleIcon();
}
function toggleTheme() {
    document.body.classList.toggle('light-mode');
    const isLight = document.body.classList.contains('light-mode');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    updateThemeToggleIcon();
}
function updateThemeToggleIcon() {
    const btn = document.getElementById('theme-toggle');
    if (btn) {
        const isLight = document.body.classList.contains('light-mode');
        btn.innerHTML = isLight ? '<i class="fas fa-moon"></i>' : '<i class="fas fa-sun"></i>';
        btn.title = isLight ? 'Switch to Dark Mode' : 'Switch to Light Mode';
    }
}

/* ── DOMContentLoaded ── */
document.addEventListener('DOMContentLoaded', () => {
    initTheme();

    // Navbar scroll shrink
    window.addEventListener('scroll', () => {
        document.querySelector('.navbar')?.classList.toggle('scrolled', window.scrollY > 20);
    });

    // Theme toggle
    const navAuth = document.getElementById('nav-auth');
    if (navAuth && !document.getElementById('theme-toggle')) {
        const li = document.createElement('li');
        li.className = 'nav-item d-flex align-items-center';
        li.innerHTML = `<button id="theme-toggle" class="theme-toggle-btn" onclick="toggleTheme()"><i class="fas fa-sun"></i></button>`;
        navAuth.parentNode.appendChild(li);
        updateThemeToggleIcon();
    }
});

/* ── Logout ── */
async function logout() {
    progressStart();
    await fetch(`${API_URL}?action=logout`, { credentials: 'include' });
    progressDone();
    window.location.href = 'login.html';
}

/* ── Password visibility toggle ── */
function togglePw(id, actualPw) {
    const span = document.getElementById(id);
    const icon = document.getElementById('icon-' + id);
    if (span.textContent === '••••••••') {
        span.textContent = actualPw;
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        span.textContent = '••••••••';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
}

/* ── Input password show/hide ── */
function initPwToggle(inputId, btnId) {
    const input = document.getElementById(inputId);
    const btn   = document.getElementById(btnId);
    if (!input || !btn) return;
    btn.addEventListener('click', () => {
        const isText = input.type === 'text';
        input.type = isText ? 'password' : 'text';
        btn.innerHTML = isText ? '<i class="fas fa-eye"></i>' : '<i class="fas fa-eye-slash"></i>';
    });
}
