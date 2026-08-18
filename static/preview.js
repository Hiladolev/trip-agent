const recommendationsBody = document.getElementById("recommendations-body");
const skeletonBody = document.getElementById("skeleton-body");

function emptyRow(colSpan) {
  const row = document.createElement("tr");
  const td = document.createElement("td");
  td.colSpan = colSpan;
  td.textContent = "No data yet.";
  row.appendChild(td);
  return row;
}

function textCell(text) {
  const td = document.createElement("td");
  td.textContent = text ?? "";
  return td;
}

function linkCell(url) {
  const td = document.createElement("td");
  if (url) {
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = url;
    td.appendChild(a);
  }
  return td;
}

function renderRecommendations(recommendations) {
  if (recommendations.length === 0) {
    recommendationsBody.appendChild(emptyRow(6));
    return;
  }
  for (const rec of recommendations) {
    const row = document.createElement("tr");
    row.appendChild(textCell(rec.city));
    row.appendChild(textCell(rec.place_name));
    row.appendChild(textCell(rec.priority));
    row.appendChild(textCell(rec.description));
    row.appendChild(linkCell(rec.maps_link));
    row.appendChild(textCell(rec.source));
    recommendationsBody.appendChild(row);
  }
}

function renderSkeleton(skeleton) {
  if (skeleton.length === 0) {
    skeletonBody.appendChild(emptyRow(4));
    return;
  }
  for (const row of skeleton) {
    const tr = document.createElement("tr");
    tr.appendChild(textCell(row.date));
    tr.appendChild(textCell(row.type));
    tr.appendChild(textCell(row.location_route));
    tr.appendChild(textCell(row.details));
    skeletonBody.appendChild(tr);
  }
}

async function loadPreview() {
  const response = await fetch("/preview/data");
  const data = await response.json();
  renderRecommendations(data.recommendations);
  renderSkeleton(data.skeleton);
}

loadPreview();
