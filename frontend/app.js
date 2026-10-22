// ---------- Find the elements on the page by their ids ----------
const fire = document.getElementById("fire");
const statusText = document.getElementById("status");
const story = document.getElementById("story");
const scariness = document.getElementById("scariness");
const scarinessValue = document.getElementById("scariness-value");

// Show the slider's number next to its label as it moves
scariness.addEventListener("input", () => {
  scarinessValue.textContent = scariness.value;
});

// ---------- The connection to the server ----------
let socket;

function connect() {
  // location.host is "localhost:8000", so this becomes ws://localhost:8000/ws
  socket = new WebSocket(`ws://${location.host}/ws`);

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);

    if (message.type === "token") {
      story.textContent += message.text;          // add the new piece of story
    } else if (message.type === "done") {
      finish("Tap the fire for another story");
    } else if (message.type === "error") {
      finish("The fire sputtered: " + message.message);
    }
  });

  // If the server restarts, try to reconnect after a second
  socket.addEventListener("close", () => {
    setTimeout(connect, 1000);
  });
}

connect();

// ---------- Tapping the fire ----------
fire.addEventListener("click", () => {
  if (socket.readyState !== WebSocket.OPEN) {
    statusText.textContent = "The fire is still catching... try again in a moment";
    return;
  }

  const settings = {
    tone: document.getElementById("tone").value,
    length: document.getElementById("length").value,
    scariness: scariness.value,
    details: document.getElementById("details").value,
  };

  story.textContent = "";                // clear the last story
  fire.disabled = true;                  // no double-taps while writing
  fire.classList.add("roaring");         // turn on the CSS roaring effect
  statusText.textContent = "The storyteller leans in...";

  socket.send(JSON.stringify({ type: "start", settings: settings }));
});

// ---------- When a story ends (or fails) ----------
function finish(text) {
  fire.disabled = false;
  fire.classList.remove("roaring");
  statusText.textContent = text;
}