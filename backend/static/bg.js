/* =============================================================================
 *  华深智药 · 密码重置  —  背景「Protein Helix / 蛋白螺旋」
 *
 *  算法哲学（Algorithmic Philosophy）：
 *  一条 α-螺旋（alpha-helix）—— 蛋白质最经典的二级结构 —— 在三维空间里缓缓自转。
 *  螺旋骨架沿轴线盘绕（每圈 3.6 个残基），每个残基向外伸出一根侧链原子，
 *  如同真实的蛋白质主链与侧链。原子以发光球体呈现（外晕、中环、亮核三层），
 *  化学键以光丝相连。深度决定大小与明暗，3D 翻转带来真正的立体感与动感。
 *
 *  隐喻：致敬华深智药 —— 用 AI 理解蛋白质结构、驱动药物发现。
 *  精心调校（meticulously crafted）的参数：螺距、半径、旋转速度、辉光、
 *  深度透视均经反复打磨，求得"科学之美 + 安静的优雅 + 持续的动感"。
 * ========================================================================== */
new p5((p) => {
  let atoms = [];     // {x,y,z, base, col}
  let bonds = [];     // [i, j]
  let rotY = 0;

  const COL_BACKBONE = [135, 212, 255];   // 骨架：青蓝
  const COL_SIDE_A   = [176, 150, 255];   // 侧链 A：紫
  const COL_SIDE_B   = [110, 245, 210];   // 侧链 B：蓝绿
  const COL_BOND     = [120, 185, 255];
  const SEED = 20260623;

  p.setup = function () {
    const c = p.createCanvas(p.windowWidth, p.windowHeight);
    if (document.getElementById('bg-host')) c.parent('bg-host');
    p.pixelDensity(1);
    p.noiseSeed(SEED);
    buildMolecule();
  };

  function buildMolecule() {
    atoms = [];
    bonds = [];
    const residues = 24;
    const R = 1.0;          // 螺旋半径
    const rise = 0.46;      // 每残基上升
    const perTurn = 3.6;    // 每圈残基数（真实 α-螺旋）
    const y0 = -(residues - 1) * rise / 2;

    let prev = -1;
    for (let i = 0; i < residues; i++) {
      const t = (i / perTurn) * p.TWO_PI;
      const bx = R * Math.cos(t);
      const bz = R * Math.sin(t);
      const by = y0 + i * rise;
      atoms.push({ x: bx, y: by, z: bz, base: 5.4, col: COL_BACKBONE });
      const idx = atoms.length - 1;
      if (prev >= 0) bonds.push([prev, idx]);   // 骨架键
      prev = idx;

      // 侧链：向外径向伸出 1~2 个原子
      const branches = (i % 2 === 0) ? 2 : 1;
      const sideCol = (i % 3 === 0) ? COL_SIDE_B : COL_SIDE_A;
      for (let b = 0; b < branches; b++) {
        const ang = t + b * 1.7;
        const ext = R + 0.55 + b * 0.5;
        atoms.push({ x: ext * Math.cos(ang), y: by + (b === 0 ? 0 : rise * 0.3), z: ext * Math.sin(ang), base: 3.8, col: sideCol });
        bonds.push([idx, atoms.length - 1]);
      }
    }
  }

  p.draw = function () {
    // 深蓝底（每帧重绘，保持干净；轻微脉动呼吸）
    p.blendMode(p.BLEND);
    p.noStroke();
    p.background(12, 32, 68);

    const cx = p.width / 2;
    const cy = p.height / 2;
    const UNIT = Math.min(p.width, p.height) * 0.16;   // 单位→像素
    const tiltX = 0.42;                                // 固定俯仰角
    const focal = 4.6;
    const breath = 1 + Math.sin(p.frameCount * 0.012) * 0.015; // 微呼吸

    rotY += 0.006;
    const cosY = Math.cos(rotY), sinY = Math.sin(rotY);
    const cosT = Math.cos(tiltX), sinT = Math.sin(tiltX);

    // 旋转 + 投影
    const proj = atoms.map((a) => {
      const x1 = a.x * cosY - a.z * sinY;
      const z1 = a.x * sinY + a.z * cosY;
      const y1 = a.y;
      const y2 = y1 * cosT - z1 * sinT;
      const z2 = y1 * sinT + z1 * cosT;
      const sc = focal / Math.max(1.2, focal + z2) * breath;
      return {
        sx: cx + x1 * sc * UNIT,
        sy: cy + y2 * sc * UNIT,
        sc: sc,
        depth: z2,
        base: a.base,
        col: a.col,
      };
    });

    // 化学键（先画，按平均深度着色）
    p.strokeWeight(1.6);
    for (const b of bonds) {
      const A = proj[b[0]], B = proj[b[1]];
      const d = (A.depth + B.depth) / 2;            // 越大越远
      const a = p.map(d, -1.6, 1.6, 150, 35, true);
      p.stroke(COL_BOND[0], COL_BOND[1], COL_BOND[2], a);
      p.line(A.sx, A.sy, B.sx, B.sy);
    }

    // 原子：按深度从远到近绘制，带辉光
    const order = proj.map((_, i) => i).sort((i, j) => proj[j].depth - proj[i].depth);
    p.noStroke();
    for (const i of order) {
      const q = proj[i];
      const d = q.depth;
      const pr = q.base * q.sc;
      const coreA = p.map(d, -1.6, 1.6, 235, 110, true);
      const midA  = p.map(d, -1.6, 1.6, 80, 25, true);
      const haloA = p.map(d, -1.6, 1.6, 32, 8, true);
      // 外晕 / 中环 / 亮核
      p.fill(q.col[0], q.col[1], q.col[2], haloA); p.circle(q.sx, q.sy, pr * 3.0);
      p.fill(q.col[0], q.col[1], q.col[2], midA);  p.circle(q.sx, q.sy, pr * 1.8);
      p.fill(q.col[0], q.col[1], q.col[2], coreA); p.circle(q.sx, q.sy, pr);
    }
  };

  p.windowResized = function () {
    p.resizeCanvas(p.windowWidth, p.windowHeight);
  };
});
