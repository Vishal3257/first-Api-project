const BASE_URL = 'https://first-api-project-wuxr.onrender.com/api/auth';

// 1. पेज लोड चेक
document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (token) showDashboard();
});

// टैब बदलने का लॉजिक (Login <-> Register)
function switchTab(type) {
    const msg = document.getElementById("auth-message");
    msg.innerText = "";
    msg.className = "message";

    if (type === 'login') {
        document.getElementById("login-form").classList.remove("hidden");
        document.getElementById("register-form").classList.add("hidden");
        document.getElementById("otp-verify-form").classList.add("hidden");
        document.getElementById("tab-login").classList.add("active-tab");
        document.getElementById("tab-register").classList.remove("active-tab");
    } else {
        document.getElementById("login-form").classList.add("hidden");
        document.getElementById("register-form").classList.remove("hidden");
        document.getElementById("otp-verify-form").classList.add("hidden");
        document.getElementById("tab-login").classList.remove("active-tab");
        document.getElementById("tab-register").classList.add("active-tab");
    }
}

// 2. नया यूज़र रजिस्टर करना (REGISTER API)
async function handleRegister() {
    const u = document.getElementById("reg-username").value;
    const e = document.getElementById("reg-email").value;
    const p = document.getElementById("reg-password").value;
    const msg = document.getElementById("auth-message");

    try {
        const res = await fetch(`${BASE_URL}/register/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: u, email: e, password: p })
        });
        const data = await res.json();
        if (res.ok) {
            msg.innerText = "Registration Successful! Please Sign In.";
            msg.className = "message success";
            switchTab('login');
        } else {
            msg.innerText = JSON.stringify(data);
            msg.className = "message error";
        }
    } catch (err) { msg.innerText = "Server Error!"; msg.className = "message error"; }
}

// 3. पासवर्ड लॉगिन (LOGIN API)
async function handleLogin() {
    const u = document.getElementById("username").value;
    const p = document.getElementById("password").value;
    const msg = document.getElementById("auth-message");

    try {
        const res = await fetch(`${BASE_URL}/login/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: u, password: p })
        });
        const data = await res.json();
        if (res.ok) {
            localStorage.setItem("token", data.access);
            showDashboard();
        } else {
            msg.innerText = data.error || "Invalid username or password";
            msg.className = "message error";
        }
    } catch (err) { msg.innerText = "Server Error!"; msg.className = "message error"; }
}

// 4. ओटीपी भेजना (SEND OTP API)
async function handleSendOTP() {
    const emailInput = document.getElementById("otp-email").value;
    const msg = document.getElementById("auth-message");
    if(!emailInput) return alert("Please enter email!");

    try {
        const res = await fetch(`${BASE_URL}/send-otp/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: emailInput })
        });
        if (res.ok) {
            document.getElementById("login-form").classList.add("hidden");
            document.getElementById("otp-verify-form").classList.remove("hidden");
            msg.innerText = "";
        } else {
            const data = await res.json();
            msg.innerText = data.error || "Failed to send OTP";
            msg.className = "message error";
        }
    } catch (err) { msg.innerText = "Server Error!"; msg.className = "message error"; }
}

// 5. ओटीपी वेरीफाई करना (VERIFY OTP API)
async function handleVerifyOTP() {
    const emailInput = document.getElementById("otp-email").value;
    const codeInput = document.getElementById("otp-code").value;
    const msg = document.getElementById("auth-message");

    try {
        const res = await fetch(`${BASE_URL}/verify-otp/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: emailInput, otp: codeInput })
        });
        const data = await res.json();
        if (res.ok) {
            localStorage.setItem("token", data.access);
            showDashboard();
        } else {
            msg.innerText = data.error || "Invalid OTP!";
            msg.className = "message error";
        }
    } catch (err) { msg.innerText = "Server Error!"; msg.className = "message error"; }
}

// TODO DASHBOARD LOGIC (पुराने जैसा ही रहेगा)
function showDashboard() {
    document.getElementById("auth-section").classList.add("hidden");
    document.getElementById("todo-section").classList.remove("hidden");
    fetchTodos();
}

async function fetchTodos() {
    const token = localStorage.getItem("token");
    const res = await fetch(`${BASE_URL}/todos/`, {
        method: "GET",
        headers: { "Authorization": `Bearer ${token}` }
    });
    const todos = await res.json();
    const todoList = document.getElementById("todo-list");
    todoList.innerHTML = "";
    todos.forEach(todo => {
        const li = document.createElement("li");
        li.innerHTML = `
            <span class="${todo.is_completed ? 'completed' : ''}">${todo.title}</span>
            <div>
                <button onclick="toggleTodo('${todo._id}', ${todo.is_completed})" style="width:auto; padding:4px 8px; background:#28a745;">✓</button>
                <button onclick="deleteTodo('${todo._id}')" style="width:auto; padding:4px 8px; background:#dc3545;">X</button>
            </div>
        `;
        todoList.appendChild(li);
    });
}

async function createTodo() {
    const titleInput = document.getElementById("todo-title");
    const token = localStorage.getItem("token");
    if (!titleInput.value) return;
    await fetch(`${BASE_URL}/todos/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ title: titleInput.value, is_completed: false })
    });
    titleInput.value = "";
    fetchTodos();
}

async function toggleTodo(id, currentStatus) {
    const token = localStorage.getItem("token");
    await fetch(`${BASE_URL}/todos/${id}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ is_completed: !currentStatus })
    });
    fetchTodos();
}

async function deleteTodo(id) {
    const token = localStorage.getItem("token");
    await fetch(`${BASE_URL}/todos/${id}/`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
    });
    fetchTodos();
}

function handleLogout() {
    localStorage.removeItem("token");
    document.getElementById("auth-section").classList.remove("hidden");
    document.getElementById("todo-section").classList.add("hidden");
    switchTab('login');
}