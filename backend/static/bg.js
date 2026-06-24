/* =============================================================================
 *  华深智药 · 密码重置  —  背景「Protein Field / 蛋白质场」
 *
 *  算法哲学（Algorithmic Philosophy）：
 *  满屏弥漫着缓缓漂浮的发光小原子（如溶液中游离的分子），整张画面都活着、
 *  在呼吸；画面中央，一条 α-螺旋（alpha-helix）—— 蛋白质最经典的二级结构 ——
 *  在三维空间里从容自转，骨架盘绕、侧链伸展。两者共用同一套"发光原子"语汇，
 *  既有铺满全屏的动感，又有清晰的科学主角。
 *
 *  隐喻：致敬华深智药 —— 用 AI 理解蛋白质结构、驱动药物发现。
 *  精心调校（meticulously crafted）：环境原子密度/流速、螺旋螺距/半径/旋转、
 *  辉光与深度透视均经反复打磨，求"科学之美 + 满屏动感 + 安静优雅"。
 * ========================================================================== */
new p5((p) => {
  let ambient = [];   // 全屏漂浮原子
  let atoms = [];     // 螺旋原子 {x,y,z,base,col}
  let bonds = [];     // 螺旋化学键 [i,j]
  let rotY = 0;

  const COL_BACKBONE = [135, 212, 255];
  const COL_SIDE_A   = [176, 150, 255];
  const COL_SIDE_B   = [110, 245, 210];
  const COL_AMBIENT  = [[120, 200, 255], [150, 170, 255], [120, 240, 220]];
  const COL_BOND     = [120, 185, 255];
  const BASE_BG = [12, 32, 68];
  const SEED = 20260623;

  p.setup = function () {
    const c = p.createCanvas(p.windowWidth, p.windowHeight);
    if (document.getElementById('bg-host')) c.parent('bg-host');
    p.pixelDensity(1);
    p.noiseSeed(SEED);
    initAmbient();
    buildMolecule();
  };

  function initAmbient() {
    ambient = [];
    const n = Math.min(220, Math.floor((p.width * p.height) / 9000));
    for (let i = 0; i < n; i++) {
      ambient.push({
        x: p.random(p.width),
        y: p.random(p.height),
        r: p.random(1.3, 2.8),
        col: COL_AMBIENT[Math.floor(p.random(COL_AMBIENT.length))],
        ph: p.random(p.TWO_PI),
      });
    }
  }

  function buildMolecule() {
    atoms = [];
    bonds = [];
    const residues = 28;
    const R = 1.0;
    const rise = 0.46;
    const perTurn = 3.6;
    const y0 = -(residues - 1) * rise / 2;
    let prev = -1;
    for (let i = 0; i < residues; i++) {
      const t = (i / perTurn) * p.TWO_PI;
      const by = y0 + i * rise;
      atoms.push({ x: R * Math.cos(t), y: by, z: R * Math.sin(t), base: 5.6, col: COL_BACKBONE });
      const idx = atoms.length - 1;
      if (prev >= 0) bonds.push([prev, idx]);
      prev = idx;
      const branches = (i % 2 === 0) ? 2 : 1;
      const sideCol = (i % 3 === 0) ? COL_SIDE_B : COL_SIDE_A;
      for (let b = 0; b < branches; b++) {
        const ang = t + b * 1.7;
        const ext = R + 0.55 + b * 0.5;
        atoms.push({ x: ext * Math.cos(ang), y: by + (b === 0 ? 0 : rise * 0.3), z: ext * Math.sin(ang), base: 3.9, col: sideCol });
        bonds.push([idx, atoms.length - 1]);
      }
    }
  }

  p.draw = function () {
    p.blendMode(p.BLEND);
    p.noStroke();
    p.background(BASE_BG[0], BASE_BG[1], BASE_BG[2]);

    // 1) 全屏漂浮原子（铺满画面，缓慢漂流 + 微闪烁）
    const t = p.frameCount * 0.0015;
    for (const a of ambient) {
      const ang = p.noise(a.x * 0.0017, a.y * 0.0017, t) * p.TWO_PI * 2;
      a.x += Math.cos(ang) * 0.55;
      a.y += Math.sin(ang) * 0.55;
      if (a.x < 0) a.x += p.width; else if (a.x > p.width) a.x -= p.width;
      if (a.y < 0) a.y += p.height; else if (a.y > p.height) a.y -= p.height;
      const tw = Math.sin(p.frameCount * 0.04 + a.ph) * 0.5 + 0.5;
      p.fill(a.col[0], a.col[1], a.col[2], 38 + tw * 55);
      p.circle(a.x, a.y, a.r * 2);
      p.fill(a.col[0], a.col[1], a.col[2], 14);
      p.circle(a.x, a.y, a.r * 5);   // 柔光晕
    }

    // 2) 中央旋转 α-螺旋
    const cx = p.width / 2, cy = p.height / 2;
    const UNIT = Math.min(p.width, p.height) * 0.21;   // 放大，填更多空间
    const tiltX = 0.42;
    const focal = 4.6;
    const breath = 1 + Math.sin(p.frameCount * 0.012) * 0.015;

    rotY += 0.006;
    const cosY = Math.cos(rotY), sinY = Math.sin(rotY);
    const cosT = Math.cos(tiltX), sinT = Math.sin(tiltX);

    const proj = atoms.map((a) => {
      const x1 = a.x * cosY - a.z * sinY;
      const z1 = a.x * sinY + a.z * cosY;
      const y2 = a.y * cosT - z1 * sinT;
      const z2 = a.y * sinT + z1 * cosT;
      const sc = focal / Math.max(1.2, focal + z2) * breath;
      return { sx: cx + x1 * sc * UNIT, sy: cy + y2 * sc * UNIT, sc, depth: z2, base: a.base, col: a.col };
    });

    p.strokeWeight(1.7);
    for (const b of bonds) {
      const A = proj[b[0]], B = proj[b[1]];
      const d = (A.depth + B.depth) / 2;
      const al = p.map(d, -1.6, 1.6, 165, 40, true);
      p.stroke(COL_BOND[0], COL_BOND[1], COL_BOND[2], al);
      p.line(A.sx, A.sy, B.sx, B.sy);
    }

    const order = proj.map((_, i) => i).sort((i, j) => proj[j].depth - proj[i].depth);
    p.noStroke();
    for (const i of order) {
      const q = proj[i];
      const pr = q.base * q.sc;
      const coreA = p.map(q.depth, -1.6, 1.6, 240, 120, true);
      const midA  = p.map(q.depth, -1.6, 1.6, 85, 28, true);
      const haloA = p.map(q.depth, -1.6, 1.6, 34, 9, true);
      p.fill(q.col[0], q.col[1], q.col[2], haloA); p.circle(q.sx, q.sy, pr * 3.0);
      p.fill(q.col[0], q.col[1], q.col[2], midA);  p.circle(q.sx, q.sy, pr * 1.8);
      p.fill(q.col[0], q.col[1], q.col[2], coreA); p.circle(q.sx, q.sy, pr);
    }
  };

  p.windowResized = function () {
    p.resizeCanvas(p.windowWidth, p.windowHeight);
    initAmbient();
  };
});
