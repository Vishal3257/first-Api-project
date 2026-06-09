const BASE_URL = 'https://first-api-project-wuxr.onrender.com/api/auth';

// 1. पेज लोड होते ही चेक करो कि क्या यूज़र पहले से लॉग-इन है?
document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (token) {
        showDashboard();
    }
});

// 2. लॉगिन हैंडल करने का फंक्शन
async function handleLogin() {
    const usernameInput = document.getElementById("username").value;
    const passwordInput = document.getElementById("password").value;
    const errorText = document.getElementById("login-error");

    try {
        const response = await fetch(`${BASE_URL}/login/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: usernameInput, password: passwordInput })
        });

        const data = await response.json();

        if (response.ok) {
            localStorage.setItem("token", data.access); // टोकन को ब्राउज़र में सेव किया
            showDashboard();
        } else {
            errorText.innerText = data.error || "Login failed!";
        }
    } catch (err) {
        errorText.innerText = "Server is unreachable!";
    }
}

// 3. डैशबोर्ड दिखाना और टास्क लोड करना
function showDashboard() {
    document.getElementById("login-section").classList.add("hidden");
    document.getElementById("todo-section").classList.remove("hidden");
    fetchTodos();
}

// 4. मोंगोडीबी से सारे टास्क मँगाना (GET Request)
async function fetchTodos() {
    const token = localStorage.getItem("token");
    const response = await fetch(`${BASE_URL}/todos/`, {
        method: "GET",
        headers: { "Authorization": `Bearer ${token}` }
    });
    
    const todos = await response.json();
    const todoList = document.getElementById("todo-list");
    todoList.innerHTML = ""; // पुराना लिस्ट साफ करना

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

// 5. नया टास्क बनाना (POST Request)
async function createTodo() {
    const titleInput = document.getElementById("todo-title");
    const token = localStorage.getItem("token");

    if (!titleInput.value) return;

    await fetch(`${BASE_URL}/todos/`, {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ title: titleInput.value, is_completed: false })
    });

    titleInput.value = "";
    fetchTodos(); // लिस्ट को रीफ्रेश किया
}

// 6. टास्क को कम्पलीट मार्क करना (PATCH Request)
async function toggleTodo(id, currentStatus) {
    const token = localStorage.getItem("token");
    await fetch(`${BASE_URL}/todos/${id}/`, {
        method: "PATCH",
        headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ is_completed: !currentStatus })
    });
    fetchTodos();
}

// 7. टास्क डिलीट करना (DELETE Request)
async function deleteTodo(id) {
    const token = localStorage.getItem("token");
    await fetch(`${BASE_URL}/todos/${id}/`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
    });
    fetchTodos();
}

// 8. लॉगआउट
function handleLogout() {
    localStorage.removeItem("token");
    document.getElementById("login-section").classList.remove("hidden");
    document.getElementById("todo-section").classList.add("hidden");
}