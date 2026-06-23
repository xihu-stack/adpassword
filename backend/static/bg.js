/* =============================================================================
 *  华深智药 · 密码重置  —  背景「Helix Flow / 螺旋流场」
 *
 *  算法哲学（Algorithmic Philosophy）：
 *  一张不可见的 Perlin 噪声力场铺满整个屏幕，成百上千的微粒如风中之絮，
 *  顺着力线无声漂流。每一帧用一层半透明的深蓝薄雾覆盖画布，旧轨迹缓缓
 *  褪去、新轨迹层层叠加——于是流动的光网在平衡中不断重生。粒子色取自一支
 *  冷光调色板（青/蓝/蓝绿/淡紫），亮轨迹在深蓝底色上灼灼发亮。
 *
 *  这是一段精心调校（meticulously crafted）的生成式算法：噪声尺度、漂移速度、
 *  拖尾衰减、粒子寿命均经反复打磨，力求复杂而不嘈杂、有序而不死板。种子化
 *  噪声保证每次加载构图一致——同一片流场，永恒地流动。
 *
 *  隐喻：药物分子在能量场中流转寻路（致敬华深智药 AI 制药）。
 *
 *  用法：页面加载 p5（CDN）后引入本文件，并提供一个 <div id="bg-host"></div>。
 *  画布固定铺满视口、z-index:0，置于内容之下。
 * ========================================================================== */
new p5((p) => {
  let particles = [];
  let zoff = 0;

  // 冷光调色板（RGB）—— 亮轨迹
  const PALETTE = [
    [127, 212, 255],  // 青
    [ 90, 168, 255],  // 蓝
    [155, 232, 255],  // 浅青
    [120, 250, 230],  // 蓝绿
    [191, 166, 255],  // 淡紫
  ];
  const BASE = [14, 38, 78];   // 基底深蓝（wash 色，决定整体明度，偏蓝不压抑）
  const SCALE = 0.0022;        // 噪声尺度（越小流场越宽阔）
  const SPEED = 1.15;          // 粒子漂移速度
  const FADE = 15;             // 拖尾衰减：越小拖尾越长
  const SEED = 20260623;       // 固定种子，构图一致

  p.setup = function () {
    const c = p.createCanvas(p.windowWidth, p.windowHeight);
    if (document.getElementById('bg-host')) c.parent('bg-host');
    p.pixelDensity(1);
    p.noFill();
    p.background(BASE[0], BASE[1], BASE[2]);
    p.noiseSeed(SEED);
    initParticles();
  };

  function initParticles() {
    particles = [];
    const n = Math.min(560, Math.floor((p.width * p.height) / 3600));
    for (let i = 0; i < n; i++) particles.push(spawn());
  }

  function spawn() {
    return {
      x: p.random(p.width),
      y: p.random(p.height),
      px: 0,
      py: 0,
      life: p.random(60, 200),
      col: PALETTE[Math.floor(p.random(PALETTE.length))],
    };
  }

  p.draw = function () {
    // 半透明基底 wash：制造拖尾衰减
    p.noStroke();
    p.fill(BASE[0], BASE[1], BASE[2], FADE);
    p.rect(0, 0, p.width, p.height);

    zoff += 0.0016;             // 力场缓慢演化
    p.strokeWeight(1.1);

    for (const q of particles) {
      const angle = p.noise(q.x * SCALE, q.y * SCALE, zoff) * p.TWO_PI * 3;
      q.px = q.x; q.py = q.y;
      q.x += Math.cos(angle) * SPEED;
      q.y += Math.sin(angle) * SPEED;
      q.life -= 1;

      p.stroke(q.col[0], q.col[1], q.col[2], 120);
      p.line(q.px, q.py, q.x, q.y);

      // 寿命到或飞出视口 → 重生于随机点
      if (q.life <= 0 || q.x < -5 || q.x > p.width + 5 || q.y < -5 || q.y > p.height + 5) {
        Object.assign(q, spawn());
      }
    }
  };

  p.windowResized = function () {
    p.resizeCanvas(p.windowWidth, p.windowHeight);
    p.background(BASE[0], BASE[1], BASE[2]);
    initParticles();
  };
});
