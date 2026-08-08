const API = "/api";

let hourlyChart, dailyChart;

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `HTTPエラー: ${res.status}`);
  }
  return res.json();
}

async function loadPoints() {
  const points = await fetchJSON(`${API}/points`);
  renderPointsTable(points);
  renderPointSelects(points);
  return points;
}

function renderPointsTable(points) {
  const tbody = document.querySelector("#points-table tbody");
  tbody.innerHTML = "";
  for (const p of points) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(p.name)}</td>
      <td>${p.lat}</td>
      <td>${p.lng}</td>
      <td>${p.radius_m}m</td>
      <td><button data-id="${p.id}" class="delete-btn">削除</button></td>
    `;
    tbody.appendChild(tr);
  }
  tbody.querySelectorAll(".delete-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await fetchJSON(`${API}/points/${btn.dataset.id}`, { method: "DELETE" });
      await loadPoints();
    });
  });
}

function renderPointSelects(points) {
  for (const selectId of ["fetch-point-select", "compare-point-select"]) {
    const select = document.getElementById(selectId);
    const prev = select.value;
    select.innerHTML = points
      .map((p) => `<option value="${p.id}">${escapeHtml(p.name)}</option>`)
      .join("");
    if (prev) select.value = prev;
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

document.getElementById("point-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    name: document.getElementById("p-name").value,
    lat: parseFloat(document.getElementById("p-lat").value),
    lng: parseFloat(document.getElementById("p-lng").value),
    radius_m: parseInt(document.getElementById("p-radius").value || "500", 10),
    memo: document.getElementById("p-memo").value,
  };
  await fetchJSON(`${API}/points`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  e.target.reset();
  document.getElementById("p-radius").value = 500;
  await loadPoints();
});

document.getElementById("fetch-live-btn").addEventListener("click", async () => {
  const pointId = document.getElementById("fetch-point-select").value;
  const status = document.getElementById("fetch-status");
  if (!pointId) { status.textContent = "先に地点を登録してください。"; return; }
  status.textContent = "取得中...";
  try {
    const result = await fetchJSON(`${API}/traffic/fetch/${pointId}`, { method: "POST" });
    status.textContent = `取得完了: ${result.fetched}件取得 / ${result.inserted}件を新規保存`;
  } catch (err) {
    status.textContent = `エラー: ${err.message}`;
  }
});

document.getElementById("import-archive-btn").addEventListener("click", async () => {
  const pointId = document.getElementById("fetch-point-select").value;
  const fileInput = document.getElementById("archive-file");
  const status = document.getElementById("fetch-status");
  if (!pointId) { status.textContent = "先に地点を登録してください。"; return; }
  if (!fileInput.files.length) { status.textContent = "CSVファイルを選択してください。"; return; }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  status.textContent = "取込中...";
  try {
    const result = await fetchJSON(`${API}/traffic/import/${pointId}`, {
      method: "POST",
      body: formData,
    });
    status.textContent = `取込完了: ${result.fetched}件読取 / ${result.inserted}件を新規保存`;
  } catch (err) {
    status.textContent = `エラー: ${err.message}`;
  }
});

document.getElementById("compare-btn").addEventListener("click", async () => {
  const pointId = document.getElementById("compare-point-select").value;
  const currentStart = document.getElementById("current-start").value;
  const currentEnd = document.getElementById("current-end").value;
  const pastStart = document.getElementById("past-start").value;
  const pastEnd = document.getElementById("past-end").value;
  const status = document.getElementById("compare-status");

  if (!pointId || !currentStart || !currentEnd || !pastStart || !pastEnd) {
    status.textContent = "地点と両方の期間を入力してください。";
    return;
  }

  status.textContent = "集計中...";
  try {
    const params = new URLSearchParams({
      point_id: pointId,
      current_start: currentStart,
      current_end: currentEnd,
      past_start: pastStart,
      past_end: pastEnd,
    });
    const result = await fetchJSON(`${API}/traffic/compare?${params}`);
    status.textContent =
      `現在期間: ${result.current.sample_count}件 / 過去期間: ${result.past.sample_count}件`;
    renderCharts(result);
  } catch (err) {
    status.textContent = `エラー: ${err.message}`;
  }
});

function renderCharts(result) {
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const currentHourly = hours.map((h) => result.current.hourly_avg[h] ?? null);
  const pastHourly = hours.map((h) => result.past.hourly_avg[h] ?? null);

  if (hourlyChart) hourlyChart.destroy();
  hourlyChart = new Chart(document.getElementById("hourly-chart"), {
    type: "bar",
    data: {
      labels: hours.map((h) => `${h}時`),
      datasets: [
        { label: "これから(現在)", data: currentHourly, backgroundColor: "#2563eb" },
        { label: "過去", data: pastHourly, backgroundColor: "#94a3b8" },
      ],
    },
    options: { responsive: true, scales: { y: { beginAtZero: true, title: { display: true, text: "平均交通量" } } } },
  });

  const currentDates = Object.keys(result.current.daily_avg).sort();
  const pastDates = Object.keys(result.past.daily_avg).sort();
  const maxLen = Math.max(currentDates.length, pastDates.length);
  const labels = Array.from({ length: maxLen }, (_, i) => `${i + 1}日目`);

  if (dailyChart) dailyChart.destroy();
  dailyChart = new Chart(document.getElementById("daily-chart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "これから(現在)",
          data: currentDates.map((d) => result.current.daily_avg[d]),
          borderColor: "#2563eb",
          backgroundColor: "#2563eb",
          tension: 0.2,
        },
        {
          label: "過去",
          data: pastDates.map((d) => result.past.daily_avg[d]),
          borderColor: "#94a3b8",
          backgroundColor: "#94a3b8",
          tension: 0.2,
        },
      ],
    },
    options: { responsive: true, scales: { y: { beginAtZero: true, title: { display: true, text: "平均交通量" } } } },
  });
}

loadPoints();
