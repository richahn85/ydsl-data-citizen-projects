(() => {
  const canvas = document.getElementById("graph-canvas");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const dataUrl = document.body.dataset.graphData || "graph-data.json";
  const stats = document.getElementById("graph-stats");
  const searchInput = document.getElementById("graph-search");
  const resetButton = document.getElementById("graph-reset");
  const detailEmpty = document.getElementById("graph-detail-empty");
  const detailContent = document.getElementById("graph-detail-content");
  const detailGroup = document.getElementById("graph-detail-group");
  const detailTitle = document.getElementById("graph-detail-title");
  const detailSummary = document.getElementById("graph-detail-summary");
  const detailDegree = document.getElementById("graph-detail-degree");
  const detailLink = document.getElementById("graph-detail-link");

  const colors = {
    home: "#111827",
    teaching: "#2563eb",
    projects: "#059669",
    concepts: "#d97706",
    entities: "#7c3aed",
    synthesis: "#dc2626",
    other: "#64748b",
  };
  const groupLabels = {
    home: "홈",
    teaching: "강의 교안",
    projects: "프로젝트",
    concepts: "개념",
    entities: "기관/도구",
    synthesis: "종합",
    other: "기타",
  };

  let graph = null;
  let nodes = [];
  let links = [];
  let nodeById = new Map();
  let visibleGroups = new Set(["home", "teaching", "projects", "concepts", "entities", "synthesis", "other"]);
  let selected = null;
  let hovered = null;
  let draggingNode = null;
  let panning = false;
  let lastPointer = null;
  let pointerMoved = false;
  let view = { x: 0, y: 0, k: 1 };

  function encodePath(url) {
    return url.split("/").map(encodeURIComponent).join("/");
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    draw();
  }

  function screenToWorld(x, y) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: (x - rect.left - view.x) / view.k,
      y: (y - rect.top - view.y) / view.k,
    };
  }

  function visibleNodeSet() {
    const term = (searchInput?.value || "").trim().toLowerCase();
    const base = new Set(
      nodes
        .filter((node) => visibleGroups.has(node.group))
        .filter((node) => !term || node.title.toLowerCase().includes(term) || (node.summary || "").toLowerCase().includes(term))
        .map((node) => node.id),
    );
    if (!term) return base;
    for (const link of links) {
      if (base.has(link.source.id) && visibleGroups.has(link.target.group)) base.add(link.target.id);
      if (base.has(link.target.id) && visibleGroups.has(link.source.group)) base.add(link.source.id);
    }
    return base;
  }

  function updateStats() {
    const visible = visibleNodeSet();
    const linkCount = links.filter((link) => visible.has(link.source.id) && visible.has(link.target.id)).length;
    stats.textContent = `${visible.size}개 노드 · ${linkCount}개 연결`;
  }

  function radius(node) {
    return 5 + Math.min(13, Math.sqrt(node.degree || 1) * 2.1);
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function repairNode(node, index, rect) {
    if (!Number.isFinite(node.x) || !Number.isFinite(node.y)) {
      const angle = index * 2.399963229728653;
      const ring = 35 + (index % 18) * 16;
      node.x = rect.width / 2 + Math.cos(angle) * ring;
      node.y = rect.height / 2 + Math.sin(angle) * ring;
    }
    if (!Number.isFinite(node.vx)) node.vx = 0;
    if (!Number.isFinite(node.vy)) node.vy = 0;
    node.vx = clamp(node.vx, -6, 6);
    node.vy = clamp(node.vy, -6, 6);
    node.x = clamp(node.x, -240, rect.width + 240);
    node.y = clamp(node.y, -240, rect.height + 240);
  }

  function placeNodes() {
    const rect = canvas.getBoundingClientRect();
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const groupOrder = ["home", "teaching", "projects", "concepts", "entities", "synthesis", "other"];
    const buckets = new Map(groupOrder.map((group) => [group, []]));
    for (const node of nodes) (buckets.get(node.group) || buckets.get("other")).push(node);
    groupOrder.forEach((group, groupIndex) => {
      const bucket = buckets.get(group);
      const angleOffset = (Math.PI * 2 * groupIndex) / groupOrder.length;
      bucket.forEach((node, index) => {
        const angle = angleOffset + (Math.PI * 2 * index) / Math.max(1, bucket.length);
        const ring = 80 + groupIndex * 34 + (index % 5) * 9;
        node.x = cx + Math.cos(angle) * ring;
        node.y = cy + Math.sin(angle) * ring;
        node.vx = 0;
        node.vy = 0;
      });
    });
    view = { x: 0, y: 0, k: 1 };
  }

  function tick() {
    const rect = canvas.getBoundingClientRect();
    const visible = visibleNodeSet();
    const active = nodes.filter((node) => visible.has(node.id));
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    active.forEach((node, index) => repairNode(node, index, rect));

    for (const link of links) {
      if (!visible.has(link.source.id) || !visible.has(link.target.id)) continue;
      const dx = link.target.x - link.source.x;
      const dy = link.target.y - link.source.y;
      if (!Number.isFinite(dx) || !Number.isFinite(dy)) continue;
      const distance = Math.hypot(dx, dy) || 1;
      const force = clamp((distance - 108) * 0.0009, -0.045, 0.045);
      const fx = dx * force;
      const fy = dy * force;
      link.source.vx += fx;
      link.source.vy += fy;
      link.target.vx -= fx;
      link.target.vy -= fy;
    }

    for (let i = 0; i < active.length; i++) {
      const a = active[i];
      for (let j = i + 1; j < active.length; j++) {
        const b = active[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        if (!Number.isFinite(dx) || !Number.isFinite(dy)) continue;
        const distance = Math.max(18, Math.hypot(dx, dy));
        const force = 18 / (distance * distance);
        const fx = dx * force;
        const fy = dy * force;
        a.vx -= fx;
        a.vy -= fy;
        b.vx += fx;
        b.vy += fy;
      }
    }

    for (const node of active) {
      if (node === draggingNode) continue;
      node.vx += (centerX - node.x) * 0.0014;
      node.vy += (centerY - node.y) * 0.0014;
      node.vx *= 0.82;
      node.vy *= 0.82;
      node.vx = clamp(node.vx, -6, 6);
      node.vy = clamp(node.vy, -6, 6);
      node.x += node.vx;
      node.y += node.vy;
      repairNode(node, active.indexOf(node), rect);
    }
  }

  function draw() {
    if (!graph) return;
    const rect = canvas.getBoundingClientRect();
    const visible = visibleNodeSet();
    ctx.clearRect(0, 0, rect.width, rect.height);
    ctx.save();
    ctx.translate(view.x, view.y);
    ctx.scale(view.k, view.k);

    for (const link of links) {
      if (!visible.has(link.source.id) || !visible.has(link.target.id)) continue;
      if (!Number.isFinite(link.source.x) || !Number.isFinite(link.source.y) || !Number.isFinite(link.target.x) || !Number.isFinite(link.target.y)) continue;
      const emphasis = selected && (link.source === selected || link.target === selected);
      ctx.strokeStyle = emphasis ? "rgba(15,23,42,.46)" : "rgba(100,116,139,.18)";
      ctx.lineWidth = emphasis ? 2 / view.k : 1 / view.k;
      ctx.beginPath();
      ctx.moveTo(link.source.x, link.source.y);
      ctx.lineTo(link.target.x, link.target.y);
      ctx.stroke();
    }

    for (const node of nodes) {
      if (!visible.has(node.id)) continue;
      if (!Number.isFinite(node.x) || !Number.isFinite(node.y)) continue;
      const r = radius(node);
      const isFocus = node === hovered || node === selected;
      ctx.beginPath();
      ctx.arc(node.x, node.y, isFocus ? r + 3 : r, 0, Math.PI * 2);
      ctx.fillStyle = colors[node.group] || colors.other;
      ctx.globalAlpha = isFocus ? 1 : 0.86;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = isFocus ? "#0f172a" : "#ffffff";
      ctx.lineWidth = isFocus ? 2.4 / view.k : 1.5 / view.k;
      ctx.stroke();
    }

    ctx.font = `${Math.max(10, 12 / Math.sqrt(view.k))}px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    for (const node of nodes) {
      if (!visible.has(node.id)) continue;
      if (!Number.isFinite(node.x) || !Number.isFinite(node.y)) continue;
      if (node !== hovered && node !== selected && (node.degree || 0) < 78) continue;
      const label = node.title.replace(/\s+강의 교안$/, "");
      ctx.fillStyle = "rgba(15,23,42,.88)";
      ctx.fillText(label.slice(0, 28), node.x, node.y + radius(node) + 5);
    }
    ctx.restore();
  }

  function animate() {
    tick();
    draw();
    requestAnimationFrame(animate);
  }

  function nearestNode(event) {
    const point = screenToWorld(event.clientX, event.clientY);
    const visible = visibleNodeSet();
    let best = null;
    let bestDistance = Infinity;
    for (const node of nodes) {
      if (!visible.has(node.id)) continue;
      const distance = Math.hypot(point.x - node.x, point.y - node.y);
      if (distance < radius(node) + 8 && distance < bestDistance) {
        best = node;
        bestDistance = distance;
      }
    }
    return best;
  }

  function selectNode(node) {
    selected = node;
    if (!node) {
      detailEmpty.hidden = false;
      detailContent.hidden = true;
      draw();
      return;
    }
    detailEmpty.hidden = true;
    detailContent.hidden = false;
    detailGroup.textContent = groupLabels[node.group] || "노드";
    detailTitle.textContent = node.title;
    detailSummary.textContent = node.summary || "";
    detailDegree.textContent = `${node.degree || 0}개 연결`;
    detailLink.href = encodePath(node.url);
    draw();
  }

  function refresh() {
    updateStats();
    if (selected && !visibleNodeSet().has(selected.id)) selectNode(null);
    draw();
  }

  window.ydslGraphDebug = () => {
    const finite = nodes.filter((node) => Number.isFinite(node.x) && Number.isFinite(node.y));
    return {
      nodes: nodes.length,
      links: links.length,
      visible: visibleNodeSet().size,
      selected: selected?.title || "",
      minX: Math.min(...finite.map((node) => node.x)),
      maxX: Math.max(...finite.map((node) => node.x)),
      minY: Math.min(...finite.map((node) => node.y)),
      maxY: Math.max(...finite.map((node) => node.y)),
      first: finite.slice(0, 5).map((node) => ({ title: node.title, group: node.group, x: node.x, y: node.y })),
    };
  };

  canvas.addEventListener("pointermove", (event) => {
    const point = screenToWorld(event.clientX, event.clientY);
    if (draggingNode) {
      draggingNode.x = point.x;
      draggingNode.y = point.y;
      draggingNode.vx = 0;
      draggingNode.vy = 0;
      pointerMoved = true;
      return;
    }
    if (panning && lastPointer) {
      view.x += event.clientX - lastPointer.x;
      view.y += event.clientY - lastPointer.y;
      lastPointer = { x: event.clientX, y: event.clientY };
      pointerMoved = true;
      draw();
      return;
    }
    hovered = nearestNode(event);
    canvas.style.cursor = hovered ? "pointer" : "grab";
    draw();
  });

  canvas.addEventListener("pointerdown", (event) => {
    canvas.setPointerCapture(event.pointerId);
    pointerMoved = false;
    lastPointer = { x: event.clientX, y: event.clientY };
    draggingNode = nearestNode(event);
    panning = !draggingNode;
  });

  canvas.addEventListener("pointerup", (event) => {
    canvas.releasePointerCapture(event.pointerId);
    const clicked = draggingNode || nearestNode(event);
    draggingNode = null;
    panning = false;
    if (!pointerMoved && clicked) selectNode(clicked);
  });

  canvas.addEventListener("dblclick", (event) => {
    const node = nearestNode(event);
    if (node) window.location.href = encodePath(node.url);
  });

  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mouse = { x: event.clientX - rect.left, y: event.clientY - rect.top };
    const before = screenToWorld(event.clientX, event.clientY);
    const scale = event.deltaY > 0 ? 0.9 : 1.1;
    view.k = Math.min(3, Math.max(0.45, view.k * scale));
    view.x = mouse.x - before.x * view.k;
    view.y = mouse.y - before.y * view.k;
    draw();
  }, { passive: false });

  searchInput?.addEventListener("input", refresh);
  document.querySelectorAll("[data-graph-group]").forEach((box) => {
    box.addEventListener("change", () => {
      visibleGroups = new Set(["home", "other"]);
      document.querySelectorAll("[data-graph-group]:checked").forEach((checked) => {
        visibleGroups.add(checked.dataset.graphGroup);
      });
      refresh();
    });
  });
  resetButton?.addEventListener("click", () => {
    searchInput.value = "";
    document.querySelectorAll("[data-graph-group]").forEach((box) => {
      box.checked = true;
    });
    visibleGroups = new Set(["home", "teaching", "projects", "concepts", "entities", "synthesis", "other"]);
    selected = null;
    placeNodes();
    refresh();
  });

  window.addEventListener("resize", resize);

  fetch(dataUrl)
    .then((response) => response.json())
    .then((data) => {
      graph = data;
      nodes = data.nodes.map((node) => ({ ...node }));
      nodeById = new Map(nodes.map((node) => [node.id, node]));
      links = data.links
        .map((link) => ({ source: nodeById.get(link.source), target: nodeById.get(link.target) }))
        .filter((link) => link.source && link.target);
      resize();
      placeNodes();
      updateStats();
      animate();
    })
    .catch((error) => {
      stats.textContent = "그래프 데이터를 불러오지 못했습니다.";
      console.error(error);
    });
})();
