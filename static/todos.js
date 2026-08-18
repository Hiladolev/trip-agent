const todosBody = document.getElementById("todos-body");
const todoForm = document.getElementById("todo-form");
const taskInput = document.getElementById("todo-task");
const deadlineInput = document.getElementById("todo-deadline");

function emptyRow(colSpan) {
  const row = document.createElement("tr");
  const td = document.createElement("td");
  td.colSpan = colSpan;
  td.textContent = "No to-dos yet.";
  row.appendChild(td);
  return row;
}

function renderTodos(todos) {
  todosBody.innerHTML = "";
  if (todos.length === 0) {
    todosBody.appendChild(emptyRow(3));
    return;
  }
  for (const todo of todos) {
    const row = document.createElement("tr");

    const taskCell = document.createElement("td");
    taskCell.textContent = todo.task;
    if (todo.completed) taskCell.classList.add("done");
    row.appendChild(taskCell);

    const deadlineCell = document.createElement("td");
    deadlineCell.textContent = todo.deadline ?? "";
    row.appendChild(deadlineCell);

    const actionsCell = document.createElement("td");
    if (!todo.completed) {
      const completeButton = document.createElement("button");
      completeButton.textContent = "Mark Done";
      completeButton.className = "btn-complete";
      completeButton.addEventListener("click", () => completeTodo(todo.id));
      actionsCell.appendChild(completeButton);
    }
    const deleteButton = document.createElement("button");
    deleteButton.textContent = "Delete";
    deleteButton.className = "btn-delete";
    deleteButton.addEventListener("click", () => deleteTodo(todo.id));
    actionsCell.appendChild(deleteButton);
    row.appendChild(actionsCell);

    todosBody.appendChild(row);
  }
}

async function loadTodos() {
  const response = await fetch("/todos/data");
  const todos = await response.json();
  renderTodos(todos);
}

async function completeTodo(id) {
  const response = await fetch(`/todos/data/${id}/complete`, { method: "POST" });
  const todos = await response.json();
  renderTodos(todos);
}

async function deleteTodo(id) {
  if (!confirm("Delete this to-do?")) return;
  const response = await fetch(`/todos/data/${id}`, { method: "DELETE" });
  const todos = await response.json();
  renderTodos(todos);
}

todoForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const task = taskInput.value.trim();
  if (!task) return;
  const deadline = deadlineInput.value || null;

  const response = await fetch("/todos/data", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task, deadline }),
  });
  const todos = await response.json();
  renderTodos(todos);
  taskInput.value = "";
  deadlineInput.value = "";
});

loadTodos();
