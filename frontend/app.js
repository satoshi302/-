const { createClient } = supabase;
const client = createClient(window.SUPABASE_CONFIG.url, window.SUPABASE_CONFIG.anonKey);

let hourlyChart, dailyChart;

async function loadPoints() {
  const { data, error } = await client.from("points").select("*").order("id");
  if (error) {
    document.getElementById("compare-status").textContent = `地点の読込に失敗しました: ${error.message}`;
    return [];
  }
  renderPointSelect(data);
  return data;
}

function renderPointSelect(points) {
  const select = document.getElementById("compare-point-select");
  if (!points.length) {
    select.innerHTML = `<option value="">(登録済みの地点がありません)</option>`;
    return;
  }
  select.innerHTML = points.map((p) => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function fetchRecords(pointId, start, end) {
  const { data, error } = await client
    .from("traffic_records")
    .select("observed_at,volume_up,volume_down")
    .eq("point_id", pointId)
    .gte("observed_at", `${start}T00:00:00`)
    .lte("observed_at", `${end}T23:59:59`);
  if (error) throw new Error(error.message);
  return data;
}

function aggregate(rows) {
  const byHour = new Map();
  const byDate = new Map();
  for (const r of rows) {
    const dt = new Date(r.observed_at);
    if (Number.isNaN(dt.getTime())) continue;
    const total = (r.volume_up || 0) + (r.volume_down || 0);
    const hour = dt.getHours();
    const date = dt.toISOString().slice(0, 10);
    if (!byHour.has(hour)) byHour.set(hour, []);
    byHour.get(hour).push(total);
    if (!byDate.has(date)) byDate.set(date, []);
    byDate.get(date).push(total);
  }
  const avg = (arr) => Math.round((arr.reduce((a, b) => a + b, 0) / arr.length) * 10) / 10;
  const hourlyAvg = Object.fromEntries([...byHour.entries()].map(([h, v]) => [h, avg(v)]));
  const dailyAvg = Object.fromEntries([...byDate.entries()].map(([d, v]) => [d, avg(v)]));
  return { hourlyAvg, dailyAvg, sampleCount: rows.length };
}

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
    const [currentRows, pastRows] = await Promise.all([
      fetchRecords(pointId, currentStart, currentEnd),
      fetchRecords(pointId, pastStart, pastEnd),
    ]);
    const current = aggregate(currentRows);
    const past = aggregate(pastRows);
    status.textContent = `現在期間: ${current.sampleCount}件 / 過去期間: ${past.sampleCount}件`;
    renderCharts(current, past);
  } catch (err) {
    status.textContent = `エラー: ${err.message}`;
  }
});

function renderCharts(current, past) {
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const currentHourly = hours.map((h) => current.hourlyAvg[h] ?? null);
  const pastHourly = hours.map((h) => past.hourlyAvg[h] ?? null);

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

  const currentDates = Object.keys(current.dailyAvg).sort();
  const pastDates = Object.keys(past.dailyAvg).sort();
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
          data: currentDates.map((d) => current.dailyAvg[d]),
          borderColor: "#2563eb",
          backgroundColor: "#2563eb",
          tension: 0.2,
        },
        {
          label: "過去",
          data: pastDates.map((d) => past.dailyAvg[d]),
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
