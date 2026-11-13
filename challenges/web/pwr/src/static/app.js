(function () {
  const cfg = window.RELIANT_CONFIG;
  if (!cfg) {
    document.getElementById("banner").textContent =
      "Config failed to load. Reactor UI offline.";
    return;
  }

  const loginPanel = document.getElementById("login-panel");
  const boardPanel = document.getElementById("board-panel");
  const banner = document.getElementById("banner");
  const loginError = document.getElementById("login-error");
  const scramOut = document.getElementById("scram-out");

  document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.hidden = true;
    try {
      const body = {
        username: document.getElementById("username").value,
        password: document.getElementById("password").value,
      };
      const res = await fetch(cfg.api.login, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "login rejected");
      }
      showBoard(cookieToken());
    } catch (err) {
      loginError.textContent = err.message;
      loginError.hidden = false;
    }
  });

  document.getElementById("scram").addEventListener("click", async () => {
    const res = await fetch(cfg.api.scram, {
      method: "POST",
      credentials: "same-origin",
    });
    const data = await res.json();
    scramOut.hidden = false;
    scramOut.textContent = JSON.stringify(data, null, 2);
    if (data.flag) {
      banner.textContent = "SCRAM complete. Core token dumped.";
    }
  });

  function cookieToken() {
    const match = document.cookie.match(/(?:^|; )pwrToken=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function showBoard(token) {
    const payload = decodePayload(token);
    document.getElementById("who").textContent = payload.user || "unknown";
    document.getElementById("role").textContent = payload.role || "unknown";
    banner.textContent = "Authenticated. Player clearance cannot arm SCRAM.";
    loginPanel.hidden = true;
    boardPanel.hidden = false;
  }

  function decodePayload(token) {
    try {
      let part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
      while (part.length % 4) {
        part += "=";
      }
      return JSON.parse(atob(part));
    } catch (err) {
      return {};
    }
  }

  const existing = cookieToken();
  if (existing) {
    showBoard(existing);
  }
})();
