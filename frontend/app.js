// ---------- Find the elements on the page by their ids ----------
const fire = document.getElementById("fire");
const statusText = document.getElementById("status");
const story = document.getElementById("story");
const scariness = document.getElementById("scariness");
const scarinessValue = document.getElementById("scariness-value");
const gallery = document.getElementById("gallery");
const player = document.getElementById("player");
const playerImage = document.getElementById("player-image");
const playerSubtitle = document.getElementById("player-subtitle");
const playerAudio = document.getElementById("player-audio");
const animateButton = document.getElementById("animate");

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
    } else if (message.type === "written") {
      finish("Like it? Bring it to life, or tap the fire for another");
      animateButton.hidden = false;               // offer the film
    } else if (message.type === "scene") {
      addThumbnail(message);                      // a small copy in the gallery
      queue.push(message);                        // join the line to be played
      if (!playing) playNext();                   // start if nothing is playing
    } else if (message.type === "done") {
      storyFinished = true;
      if (!playing) playNext();                   // closes the player if all played
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
  queue = [];                            // and any scenes left to play
  storyFinished = false;
  animateButton.hidden = true;           // hide the old story's film button
  fire.disabled = true;                  // no double-taps while writing                // no double-taps while writing
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

// ---------- The film player ----------
let queue = [];             // scenes that are ready but haven't played yet
let playing = false;        // is a scene playing right now?
let storyFinished = false;  // has the server sent "done"?

function addThumbnail(scene) {
  const img = document.createElement("img");
  img.src = scene.image;
  img.alt = scene.text;
  gallery.appendChild(img);
}

function playNext() {
  if (queue.length === 0) {
    playing = false;
    if (storyFinished) {
      closePlayer();          // everything has played: fade back to the fire
    } else {
      playerSubtitle.textContent = "The storyteller gathers the next scene...";
    }
    return;
  }

  const scene = queue.shift();  // take the scene at the front of the line
  playing = true;
  player.classList.add("visible");

  playerImage.src = scene.image;
  playerImage.classList.remove("panning");
  void playerImage.offsetWidth;          // restart the pan animation
  playerImage.classList.add("panning");
  playerSubtitle.textContent = scene.text;
  playerAudio.src = scene.audio;
  playerAudio.play().catch(() => {
    // The browser blocked the sound; still move on after a pause
    setTimeout(playNext, 8000);
  });
}

function closePlayer() {
  playing = false;
  playerAudio.pause();
  player.classList.remove("visible");
}

// When one scene's narration ends, play the next
playerAudio.addEventListener("ended", playNext);

// Clicking the player stops the film early
player.addEventListener("click", () => {
  queue = [];
  storyFinished = true;
  closePlayer();
});

// ---------- "Bring it to life!" ----------
animateButton.addEventListener("click", () => {
  animateButton.hidden = true;
  gallery.innerHTML = "";
  queue = [];
  storyFinished = false;
  fire.disabled = true;
  fire.classList.add("roaring");
  statusText.textContent = "Picturing the scenes...";

  socket.send(JSON.stringify({ type: "animate", story: story.textContent }));
  });