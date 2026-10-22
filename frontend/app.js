// ---------- Find the elements on the page by their ids ----------
const fire = document.getElementById("fire");
const statusText = document.getElementById("status");
const story = document.getElementById("story");
const scariness = document.getElementById("scariness");
const scarinessValue = document.getElementById("scariness-value");
const gallery = document.getElementById("gallery");

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
    } else if (message.type === "stage") {
      statusText.textContent = message.stage;     // what the pipeline is doing now
    } else if (message.type === "image") {
      const img = document.createElement("img");  // build a new <img> element
      img.src = message.url;
      img.alt = message.caption;
      gallery.appendChild(img);                   // and add it to the page
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
  gallery.innerHTML = "";                // and its pictures
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

// ---------- Live hardware stats ----------
const gpuBar = document.getElementById("gpu-bar");
const memBar = document.getElementById("mem-bar");

function showStats(stats) {
  // GPU panel
  document.getElementById("gpu-value").textContent = stats.gpu;
  document.getElementById("temp-value").textContent = stats.temp ?? "--";
  document.getElementById("power-value").textContent = stats.power ?? "--";
  gpuBar.style.width = stats.gpu + "%";

  // Memory panel
  document.getElementById("mem-value").textContent = stats.mem_used;
  document.getElementById("mem-total").textContent = stats.mem_total;
  memBar.style.width = (stats.mem_used / stats.mem_total) * 100 + "%";

  // The fire: 0% busy -> heat 0, 100% busy -> heat 1
  fire.style.setProperty("--heat", stats.gpu / 100);
}

function connectStats() {
  const statsSocket = new WebSocket(`ws://${location.host}/stats`);
  statsSocket.addEventListener("message", (event) => {
    showStats(JSON.parse(event.data));
  });
  statsSocket.addEventListener("close", () => {
    setTimeout(connectStats, 1000);
  });
}

connectStats();