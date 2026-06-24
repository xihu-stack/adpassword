/* =============================================================================
 *  华深智药 · 密码重置  —  背景「Luminous Network / 光网」
 *
 *  算法哲学（Algorithmic Philosophy）：
 *  上百个发光节点散布于暗夜，顺 Perlin 力场缓缓漂移；彼此靠近时便以光线相连，
 *  距离越近、光丝越亮。节点带各自相位轻轻闪烁（twinkle），加法混色（ADD）让
 *  交叠的光丝汇聚成灼热的枢纽。整张光网随力场整体流转、不断重组——
 *  既有星图般的秩序，又有数据流般的动感。
 *
 *  这是一段精心调校（meticulously crafted）的生成式算法：节点密度、连接阈值、
 *  漂移速度、拖尾衰减、闪烁频率均经反复打磨。种子化噪声保证构图稳定可复现。
 *
 *  隐喻：分子节点在能量网中互联、跃迁（致敬华深智药 AI 制药）。
 * ========================================================================== */
new p5((p) => {
  let nodes = [];
  let zoff = 0;

  const PALETTE = [
    [127, 212, 255],
    [ 90, 168, 255],
    [155, 232, 255],
    [120, 250, 230],
    [191, 166, 255],
  ];
  const BASE = [10, 28, 60];     // 基底深蓝（wash 色）
  const SCALE = 0.0018;          // 噪声尺度
  const SPEED = 1.9;             // 节点漂移速度（越大越动感）
  const LINK = 152;              // 连接距离阈值
  const FADE = 28;               // 拖尾衰减（越大越清爽，运动越明显）
  const SEED = 20260623;

  p.setup = function () {
    const c = p.createCanvas(p.windowWidth, p.windowHeight);
    if (document.getElementById('bg-host')) c.parent('bg-host');
    p.pixelDensity(1);
    p.background(BASE[0], BASE[1], BASE[2]);
    p.noiseSeed(SEED);
    initNodes();
  };

  function initNodes() {
    nodes = [];
    const n = Math.min(130, Math.floor((p.width * p.height) / 14000));
    for (let i = 0; i < n; i++) {
      nodes.push({
        x: p.random(p.width),
        y: p.random(p.height),
        col: PALETTE[Math.floor(p.random(PALETTE.length))],
        ph: p.random(p.TWO_PI),
      });
    }
  }

  p.draw = function () {
    // 1) BLEND 薄雾：让旧光丝渐褪
    p.blendMode(p.BLEND);
    p.noStroke();
    p.fill(BASE[0], BASE[1], BASE[2], FADE);
    p.rect(0, 0, p.width, p.height);

    // 2) 节点顺力场漂移（环面 wrapping，密度恒定）
    zoff += 0.003;
    for (const q of nodes) {
      const a = p.noise(q.x * SCALE, q.y * SCALE, zoff) * p.TWO_PI * 2;
      q.x += Math.cos(a) * SPEED;
      q.y += Math.sin(a) * SPEED;
      if (q.x < 0) q.x += p.width;
      else if (q.x > p.width) q.x -= p.width;
      if (q.y < 0) q.y += p.height;
      else if (q.y > p.height) q.y -= p.height;
    }

    // 3) ADD 混色：连接线 + 发光节点（交叠处自然变亮，呈枢纽感）
    p.blendMode(p.ADD);
    p.strokeWeight(1);
    for (let i = 0; i < nodes.length; i++) {
      const A = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const B = nodes[j];
        const dx = A.x - B.x, dy = A.y - B.y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < LINK) {
          p.stroke(95, 175, 255, (1 - d / LINK) * 150);
          p.line(A.x, A.y, B.x, B.y);
        }
      }
    }
    p.noStroke();
    for (const q of nodes) {
      const tw = Math.sin(p.frameCount * 0.05 + q.ph) * 0.5 + 0.5;  // 0..1 闪烁
      const r = 2 + tw * 1.8;
      p.fill(q.col[0], q.col[1], q.col[2], 36);
      p.circle(q.x, q.y, r * 5);                                    // 柔光晕
      p.fill(q.col[0], q.col[1], q.col[2], 140 + tw * 110);
      p.circle(q.x, q.y, r * 2);                                    // 亮核
    }
  };

  p.windowResized = function () {
    p.resizeCanvas(p.windowWidth, p.windowHeight);
    p.blendMode(p.BLEND);
    p.background(BASE[0], BASE[1], BASE[2]);
    initNodes();
  };
});
